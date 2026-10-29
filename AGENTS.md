# AGENTS.md – Arbeitsübergabe

Stand: 29.10.2026, Workbench **1.2.3**. Diese Datei ist der Einstieg für die nächste Person oder den nächsten Agenten. Sie beschreibt Zweck, Prüfungen, Architektur, Regeln und den aktuellen Stand.

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

- **Projekt- und Nutzerdaten schützen.** Keine Zugangsdaten, `.env`, `var/`, `snapshots/`, `certs/`, `woltlab/` oder Projektordner committen.
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

Die README bleibt beim Release unverändert: Badge und `releases/latest` zeigen die neue Version von selbst.

Ein bereits veröffentlichter Tag wird nicht überschrieben. Ein Release gilt erst als fertig, wenn der Workflow erfolgreich war und das GitHub-Release mit ZIP und Prüfsumme sichtbar ist.

## Aktueller Stand und offene Punkte

- Release 1.2.2 ist seit 29.10.2026 veröffentlicht; 1.2.3 bringt die automatische Versionsanzeige, den stabilen ZIP-Download, die Repository-Prüfung und die neuen Workflows.
- Jede Veröffentlichung lädt zusätzlich `wsc-local.zip` und `wsc-local-SHA256SUMS.txt` als stabile Namen hoch; die README verlinkt sie über `releases/latest`.
- Der Update-Lock erkennt tote Prozesse, wiederverwendete PIDs und alte unvollständige Sperren. Eine laufende Sperre blockiert weiterhin.
- Ein laufendes Dashboard liest die Release-Version beim Start. Weicht `VERSION` auf der Platte davon ab, nennt der Update-Bereich beide Werte und blockiert das automatische Update bis zum Neustart.
- Die hellen Formulargrenzen und Fokusringe erfüllen WCAG 1.4.11 (3:1); Dark Mode bleibt unverändert.
- Vollständige native macOS-/Windows-Docker-Abnahmen und WSC-6.3-Dauerbetrieb sind weiterhin gesonderte Plattformtests.
- Das frühere Stil-Labor ist bewusst nicht Teil des Produkts. Nicht ohne neue Anforderung und eigenen Testplan wieder einführen.
