# AGENTS.md – Arbeitsübergabe

Die veröffentlichte Versionsnummer steht in `VERSION` und im Release-Badge der README. Diese Datei wiederholt sie nicht. Sie ist der Einstieg für die nächste Person oder den nächsten Agenten und beschreibt Zweck, Prüfungen, Architektur, Regeln und den aktuellen Stand.

## Zweck

Die Workbench richtet lokale WoltLab-Suite-Installationen in getrennten Docker-Projekten ein und verwaltet sie über ein lokales Browser-Dashboard und dieselbe CLI. Sie ist kein WoltLab-Ersatz und kein Hosting-Produkt.

- Standard ist WoltLab Suite 6.2 mit PHP 8.4, Nginx/PHP-FPM und MariaDB.
- 6.3 ist ein ausdrücklich inoffizieller Entwicklungsbuild.
- Projekte liegen außerhalb des Repos unter `~/.local/share/wsc-local/projects`.
- Persönliche Daten, Zugangsdaten, Projekte und Sicherungen gehören nie ins Repository.

## Schnellstart und Prüf-Harness

```bash
./start.sh                 # Dashboard auf http://127.0.0.1:9099/
./start.sh --no-open       # ohne Browserstart
python3 scripts/check.py   # Python, JavaScript, Bash, Whitespace
python3 scripts/check.py --ui  # zusätzlich Chromium-Tests
python3 scripts/check.py --metadata  # nur VERSION, Changelog und README-Verweise
python3 scripts/check.py --release  # Release-Metadaten und ZIP-Probe (nach dem Commit)
python3 scripts/check_repo.py  # Repository-Sauberkeit (Laufzeitdaten, Zeilenenden, Links)
```

Voraussetzungen für die UI-Prüfung:

```bash
npm ci
npx playwright install chromium
```

`scripts/check.py` ist die lokale Kurzprüfung. Die GitHub-CI ist maßgeblich: Sie prüft Linux, macOS und Windows mit Python 3.10/3.13, die Dashboard-Syntax, Bash/PowerShell-Einstiegspunkte und Chromium. Der Release-Workflow prüft exakt den getaggten Commit.

`--release` braucht einen sauberen Commit: Es gleicht `VERSION`, den Changelog-Abschnitt und die README-Verweise ab und baut das Release-ZIP samt Dateikatalog und Prüfsummen probeweise. `--metadata` führt nur den Metadatenabgleich aus. `scripts/check_repo.py` prüft die Repository-Sauberkeit: keine Laufzeit-, Projekt- oder Zugangsdateien, keine übergroßen Dateien, saubere Zeilenenden, gültiges JSON und erreichbare relative Markdown-Verweise.

Die README nennt keine feste Version mehr. Ein Release-Badge zeigt die neueste Veröffentlichung, die Links zeigen auf `releases/latest` und den stabilen Download `wsc-local.zip`. Feste Versionsverweise in der README lehnt `--metadata` ab.

Die Workflows: `workbench.yml` prüft Repository-Sauberkeit, Release-Metadaten, ruff/shellcheck, sechs Plattformkombinationen und Chromium; `release.yml` veröffentlicht getaggte Commits und verlangt den Tag auf `main`; `codeql.yml` analysiert Python und JavaScript auf `main` und wöchentlich; Dependabot aktualisiert Actions und npm wöchentlich.

## Architektur

| Pfad | Aufgabe |
|---|---|
| `workbench/cli.py` | Projekt-Lebenszyklus, Docker Compose, Installation, Sicherungen, TLS, Recovery, Kompatibilitätskorrekturen |
| `workbench/code_repo.py` | Optionaler eigener Code: lokales Git unter `projects/<name>/code`, Worktrees, GitHub nur für `wsc-<projekt>` |
| `workbench/launcher.py` | Dashboard-Start, Port-/Prozessprüfung, sauberer Serverwechsel |
| `workbench/updater.py` | Signierte Release-Prüfung, ZIP-/Git-Austausch, Wiederherstellung, `var/update.lock` |
| `workbench/profiles.json` | unterstützte WSC-/PHP-/Datenbank-Kombinationen |
| `scripts/panel_server.py` | lokale HTTP-API und statische Dashboard-Dateien; authentifiziert über Panel-Token |
| `panel/` | Dashboard ohne Build-Schritt: `app.js`, `ui_helpers.js`, `styles.css`, Sprachkatalog |
| `tests/` | Python-Unit-/HTTP-Tests und Chromium-Tests mit isolierten API-Antworten |
| `docs/` | Produktgrundsätze, Update-/Plattform-/Testdokumentation und Screenshots |
| `scripts/release.py` | reproduzierbares Release-ZIP, Dateikatalog, SHA-256, stabile Download-Namen, GitHub-Veröffentlichung |
| `scripts/check.py` | lokale Kurzprüfung; `--ui`, `--metadata`, `--release` |
| `scripts/check_repo.py` | Repository-Sauberkeit: Laufzeitdaten, Dateigröße, Zeilenenden, JSON, Markdown-Verweise |

Der Server bindet nur an Loopback. Änderungen an der Oberfläche müssen ohne Framework und ohne externen CDN funktionieren: keine Netzwerkabhängigkeiten im Browser, lokale Font-Awesome-Free-Icons, Deutsch als Standard und Englisch über den Sprachkatalog.

## Regeln für Änderungen

- **Projekt- und Nutzerdaten schützen.** Keine Zugangsdaten, `.env`, `var/`, `snapshots/`, `certs/`, `woltlab/` oder Projektordner committen. Foren-Code gehört nicht in dieses Workbench-Repository; optionaler eigener Code liegt unter `~/.local/share/wsc-local/projects/<name>/code`.
- **Optionalen eigenen Code isolieren.** `site/`, Datenbank, TLS und Geheimnisse bleiben außerhalb von `code/`. Die Anmeldung öffnet github.com; dort werden die Zugangsdaten eingegeben oder der Einmalcode bestätigt. Das Dashboard speichert kein Passwort und kein Token. Die Sitzung bleibt unter `GH_CONFIG_DIR` in `~/.config/wsc-local/gh`. Fehlt Git oder die GitHub-CLI, wird das erklärt und nicht still installiert. Nur das von der Workbench angelegte private Repository `wsc-<projekt>` verwalten; fremde Remotes und Force-Push sind aus.
- **WoltLab nicht stillschweigend patchen.** Kompatibilitätskorrekturen nur für exakt erkannte Codeblöcke, mit Original, Prüfsumme und Dokumentation.
- **Destruktive Aktionen bestätigen.** Projekt entfernen, Wiederherstellen und Update nur nach sichtbarer Bestätigung.
- **Keine neuen Suite-Versionen freigeben, ohne sie zu testen.** 6.3 bleibt inoffiziell; andere Stacks nicht als getestet darstellen.
- **Oberfläche und API zusammen ändern.** Neue Aktionen brauchen Authentifizierung, Versionsprüfung, Hintergrundstatus und Tests.
- **Fehler ehrlich melden.** Lieber abbrechen und die Sicherung nennen, als einen Erfolg vorzutäuschen.
- **Deutsch bleibt die Quelle der UI-Texte.** Neue sichtbare Texte zusätzlich in `panel/locale-en.js` aufnehmen.

## Release

1. `VERSION` erhöhen.
2. `CHANGELOG.md` mit einem Abschnitt `## <Version> – <Datum>` ergänzen; daraus entstehen die Release-Notes.
3. `python3 scripts/check.py --ui` ausführen.
4. Commit auf `main`, dann `python3 scripts/check.py --release` ausführen.
5. Annotierten Tag `v<Version>` setzen und Commit und Tag pushen.
6. Der Tag startet `.github/workflows/release.yml`: Plattformprüfungen, Versions-/Changelog-Abgleich, ZIP, SHA-256 und Veröffentlichung.

Die README bleibt beim Release unverändert: Badge und `releases/latest` zeigen die neue Version von selbst. `AGENTS.md` und `docs/screenshots/README.md` nennen keine Release-Nummer.

Ein bereits veröffentlichter Tag wird nicht überschrieben. Ein Release gilt erst als fertig, wenn der Workflow erfolgreich war und das GitHub-Release mit ZIP und Prüfsumme sichtbar ist.

## Aktueller Stand und offene Punkte

- Die Update-Seite trennt laufenden Prozess, Programmdateien und veröffentlichte Version. Sie nennt die Workbench nur aktuell, wenn Prozess und Dateien übereinstimmen, und bietet sonst den Dashboard-Neustart an. Optionaler eigener Code und die GitHub-Anmeldung ohne Passwort im Dashboard gehören zum Produkt; fehlt Git oder die GitHub-CLI, erklärt die Oberfläche den Befehl.
- GitHub-Sicherheit für das öffentliche Repository: `SECURITY.md`, private Schwachstellenmeldung, Dependabot-Alarme und Sicherheitsupdates, Secret Scanning mit Push-Schutz. Code-Scanning und Security Advisories bleiben an. Die kostenlosen Workflows bleiben `workbench.yml`, `codeql.yml`, `release.yml` und das wöchentliche Dependabot für Actions und npm. Keine zusätzlichen kostenpflichtigen Runner.
- Jede Veröffentlichung lädt zusätzlich `wsc-local.zip` und `wsc-local-SHA256SUMS.txt` als stabile Namen hoch; die README verlinkt sie über `releases/latest`.
- Der Update-Lock erkennt tote Prozesse, wiederverwendete PIDs und alte unvollständige Sperren. Eine laufende Sperre blockiert weiterhin.
- Ein laufendes Dashboard liest die Release-Version beim Start. Weicht sie von den Dateien ab, nennt der Update-Bereich beide Werte, bietet den Neustart an und blockiert das automatische Update, bis Prozess und Dateien übereinstimmen.
- Die hellen Formulargrenzen und Fokusringe erfüllen WCAG 1.4.11 (3:1); Dark Mode bleibt unverändert.
- Vollständige native macOS-/Windows-Docker-Abnahmen und WSC-6.3-Dauerbetrieb sind weiterhin gesonderte Plattformtests.
- Das frühere Stil-Labor ist bewusst nicht Teil des Produkts. Nicht ohne neue Anforderung und eigenen Testplan wieder einführen.
- Optionaler eigener Code und GitHub-Anbindung sind unter Werkzeuge verfügbar; die Suite bleibt ohne diese Stufen voll nutzbar.
