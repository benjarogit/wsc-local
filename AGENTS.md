# AGENTS.md – Arbeitsübergabe

Stand: 29.10.2026, Workbench **1.2.1**. Diese Datei ist der Einstieg für die nächste Person oder den nächsten Agenten. Sie beschreibt Zweck, Prüfungen, Architektur, Regeln und den aktuellen Stand.

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
```

Voraussetzungen für die UI-Prüfung:

```bash
npm ci
npx playwright install chromium
```

`scripts/check.py` ist die lokale Kurzprüfung. Die GitHub-CI ist maßgeblich: Sie prüft Linux, macOS und Windows mit Python 3.10/3.13, die Dashboard-Syntax, Bash/PowerShell-Einstiegspunkte und Chromium. Der Release-Workflow prüft exakt den getaggten Commit.

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
| `scripts/release.py` | reproduzierbares Release-ZIP, Dateikatalog, SHA-256, GitHub-Veröffentlichung |

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
3. Aktuelle Versionslinks in `README.md` und `README.en.md` aktualisieren.
4. `python3 scripts/check.py --ui` ausführen.
5. Commit auf `main`, dann annotierten Tag `v<Version>` setzen und beides pushen.
6. Der Tag startet `.github/workflows/release.yml`: Plattformprüfungen, Versions-/Changelog-Abgleich, ZIP, SHA-256 und Veröffentlichung.

Ein bereits veröffentlichter Tag wird nicht überschrieben. Ein Release gilt erst als fertig, wenn der Workflow erfolgreich war und das GitHub-Release mit ZIP und Prüfsumme sichtbar ist.

## Aktueller Stand und offene Punkte

- Release 1.2.0 ist veröffentlicht; 1.2.1 enthält den Lock-Fix und die Kontrastkorrektur.
- Der Update-Lock erkennt tote Prozesse, wiederverwendete PIDs und alte unvollständige Sperren. Eine laufende Sperre blockiert weiterhin.
- Die hellen Formulargrenzen und Fokusringe erfüllen WCAG 1.4.11 (3:1); Dark Mode bleibt unverändert.
- Vollständige native macOS-/Windows-Docker-Abnahmen und WSC-6.3-Dauerbetrieb sind weiterhin gesonderte Plattformtests.
- Das frühere Stil-Labor ist bewusst nicht Teil des Produkts. Nicht ohne neue Anforderung und eigenen Testplan wieder einführen.
