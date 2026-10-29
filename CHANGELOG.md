# Änderungen / Changelog

## 1.2.2 – 2026-10-29

### Deutsch

- Dokumentation korrigiert: 1.2.1 ist seit dem 29.10.2026 veröffentlicht. README, Screenshot-Dokumentation und Testprotokoll behaupten das nicht mehr fälschlich.
- `python3 scripts/check.py --release` prüft `VERSION`, den Changelog-Abschnitt und die Versionslinks beider README-Dateien, verlangt einen sauberen Commit und baut das Release-ZIP samt Dateikatalog und Prüfsummen probeweise.
- Das Dashboard erkennt, wenn die Programmdateien von der beim Start geladenen Version abweichen, nennt beide Werte und blockiert das automatische Update bis zum Neustart.
- Neue Regressionstests für die Release-Metadaten und die Laufzeitwarnung.

### English

- Corrected the documentation: 1.2.1 has been public since 29 October 2026. The README, screenshot documentation, and test notes no longer claim otherwise.
- `python3 scripts/check.py --release` validates `VERSION`, the changelog section, and the version links in both README files, requires a clean commit, and builds the release ZIP including manifest and checksums as a trial run.
- The dashboard detects when the program files differ from the version loaded at startup, names both values, and blocks automatic updates until it restarts.
- Added regression tests for the release metadata and the runtime warning.

**Geltungsbereich / Scope:** Die Workbench aktualisiert sich selbst, nicht die WoltLab-Suite. WSC 6.3 bleibt ein inoffizieller Entwicklungsbuild; native macOS-/Windows-Docker-Abnahmen bleiben gesonderte Plattformtests.

## 1.2.1 – 2026-10-29

### Deutsch

- Die Update-Sperre `var/update.lock` erkennt jetzt verwaiste Sperren nach einem Absturz oder Neustart, wiederverwendete Prozess-IDs und alte unvollständige Sperren. Eine tatsächlich laufende Sperre blockiert weiterhin.
- Formulargrenzen und Fokusring im hellen Modus erfüllen jetzt WCAG 1.4.11 (3:1). Der Dark Mode bleibt unverändert.
- Neue Arbeitsübergabe `AGENTS.md` und lokale Prüf-Harness `python3 scripts/check.py`; mit `--ui` laufen zusätzlich die Chromium-Tests.
- Zusätzliche Regressionstests für tote, laufende und alte Update-Sperren.

### English

- `var/update.lock` now recovers locks left by crashed or restarted updates, reused process IDs, and old incomplete locks. A genuinely running update still blocks.
- Light-mode form borders and focus rings now meet WCAG 1.4.11 (3:1); dark mode is unchanged.
- Added the `AGENTS.md` handoff and the local `python3 scripts/check.py` harness, with `--ui` to include Chromium tests.
- Added regression tests for dead, live, and old update locks.

**Geltungsbereich / Scope:** Die Workbench aktualisiert sich selbst, nicht die WoltLab-Suite. WSC 6.3 bleibt ein inoffizieller Entwicklungsbuild; native macOS-/Windows-Docker-Abnahmen bleiben gesonderte Plattformtests.

## 1.2.0 – 2026-10-28

### Deutsch

- Neue Update-Meldung und eigener Bereich **Updates** in deutscher und englischer Oberfläche; aktuelle Version im Dashboard-Fußbereich. Hintergrundprüfung mit Cache, manuelles erneutes Prüfen und Release-Hinweise.
- Automatische Workbench-Updates über Dashboard und `./wsc update`, wahlweise manuelle Anleitung. Git wird per Fast-forward aktualisiert; ZIP-Dateien werden anhand ihres Dateikatalogs ausgetauscht. Die erste Aktualisierung von 1.1.0 oder älter erfolgt noch manuell.
- Feste offizielle Release-Quelle, SHA-256- und Dateiprüfung, Schutz persönlicher Daten, lokaler Änderungen und kollidierender Dateien. Laufende Aufträge und gleichzeitig eintreffende Änderungen blockieren den Programmaustausch.
- Wiederherstellungsstand vor jedem Update, persistenter Fortschritt über den Dashboard-Neustart und Rückkehr zum alten Programm bei Schreib- oder Startfehlern. Zwischenzeitlich geänderte Dateien werden bei der Wiederherstellung geschützt.
- Neue GitHub-Release-Automation: stabiler Versions-Tag, Prüfungen des exakten Commits, Abgleich von VERSION und Changelog, ZIP mit Dateikatalog und Prüfsummen, Veröffentlichung erst nach erfolgreichen Tests.
- Zusätzliche Tests für ZIP und Git, Fehlerfälle, echte Dashboard-Neustarts, Wiederherstellung, Browser-Wiederverbindung und Paketbau. Erweiterte Anleitungen und aktuelle Screenshots.

### English

- Update notifications, a dedicated Updates page, release notes and a visible application version in both dashboard languages.
- Guided automatic application updates for Git and ZIP installations, with preview, confirmation and offline manual instructions. Users on 1.1.0 or earlier perform the first upgrade manually.
- Official stable release downloads, SHA-256 and managed-file verification, local-change and collision guards, and preserved project data and credentials.
- Recovery points, persistent progress across a real dashboard restart and automatic recovery after file or startup failures. Tests include a live browser update and a failed replacement followed by a verified restart of the old version.
- Tag-driven GitHub release automation tests the pinned commit and verifies the version before building and publishing archives, file manifests and checksums.

**Geltungsbereich / Scope:** Aktualisiert wird die Workbench, nicht die WoltLab-Suite. Das 6.3-Profil bleibt ein inoffizieller Entwicklungsbuild. Native Paketinstallationen und vollständige Docker-Abnahmen auf macOS/Windows bleiben gesonderte Zielsystemtests; die CI prüft portable Logik auf allen drei Systemen.

## 1.1.0 – 2026-10-28

- Neue WoltLab-Installationen übernehmen die gewählte Dashboard-Sprache für Suite-Standard und Adminbenutzer. CLI: Systemsprache bzw. `--language de|en`; gespeicherte Auswahl bei Wiederaufnahme. Sprachprüfung vor Freigabe. / New installations inherit the dashboard language, with CLI locale fallback, explicit override, and final language verification.
- ACP-Direktlogin über normale WoltLab-Anmeldung und kurz gültige Einmal-Übergabe; verständlicher Rückfall auf die manuelle Anmeldung bei geändertem Zugang oder Zwei-Faktor-Prüfung.
- Geführte Einrichtung fehlender Voraussetzungen im Systemterminal, per Dashboard oder nativem Linux-/macOS-/Windows-Einstieg; abschließende Systemprüfung statt pauschaler Erfolgsmeldung.
- DE/EN-Schalter mit Globus-Icon und gespeichertem Zustand. Zentrierte README-Galerien und erneuerte Screenshots in beiden Sprachen.
- Zusätzliche Tests für Anmeldesicherheit, Hintergrundendpunkte, Terminalübergabe, Sprachschalter und Installationsvorschau.

English: direct ACP login using a normal WoltLab session and a one-use handoff; guided prerequisite setup in the system terminal; globe language switch; centered screenshot galleries and additional regression coverage. Native macOS/Windows package installations still require device testing.

## 1.0.0 – 2026-10-28

Erste versionierte Veröffentlichung der neu konzipierten WoltLab Workbench.

### Deutsch

- Mehrere voneinander getrennte WoltLab-Projekte mit gemeinsamer CLI und lokalem Dashboard.
- Geführte Vorbereitung, prüfbare Adminzugänge und vollständige automatische WoltLab-Installation mit abschließender Website-/Admin-Prüfung.
- Profile ab WSC 5.5, Standard WSC 6.2 und optionaler inoffizieller WSC-6.3-Entwicklungsbuild; Nginx/PHP-FPM, Apache und optionale Dienste.
- Projektbezogene Portvergabe, lokale Geheimnisse, mkcert-HTTPS und Systemprüfung für Linux, macOS und Windows/WSL2.
- Zusammengehörige Datei-/Datenbanksicherungen, Wiederherstellung, Exportpakete, Recovery-Hilfe sowie geführte Domain-, Verzeichnis- und Umzugshinweise.
- Hintergrundvorgänge mit Wiederaufnahme nach Verbindungsabbruch oder Neuladen; Dialoge, lokale Font-Awesome-Free-Icons und direkte Theme-Auswahl.
- Deutsch als Standardsprache, gespeicherter Englisch-Umschalter, deutsch-/englischsprachige Dokumentation und aktuelle Screenshot-Galerien.
- Automatisierte Plattform-, HTTP-, CLI- und Browser-Regressionstests samt CI.

**Umstieg:** Der normale Einstieg führt jetzt in die Workbench. Bestehende Workbench-Daten liegen außerhalb des Repos. Der alte Einzel-Stack bleibt unter `--legacy` verfügbar; dessen rohe Datenbankablage wird nicht automatisch migriert.

**Geltungsbereich:** WSC 6.3 bleibt ein inoffizieller Entwicklungsbuild. Server-Exporte enthalten eine Anleitung statt eines SSH-Deployments. Domain-/Verzeichnisaktionen sichern und leiten an. Vollständige native macOS-/Windows-Docker-Abnahmen und weitere nicht ausgeführte Fälle stehen im [Testprotokoll](docs/user-test.md).

### English

- First versioned WoltLab Workbench release: isolated projects, shared CLI/dashboard, automatic installation, and actual website/admin verification.
- Curated WSC/PHP profiles, Nginx/PHP-FPM and Apache, local HTTPS, independent ports and secrets, and platform checks.
- Consistent backups/restores, export packages, official Recovery Tool integration, and guided migration/domain/directory workflows.
- Reconnectable background tasks, accessible dialogs, bundled Font Awesome Free icons, and System/Light/Dark icon controls.
- German default with a saved English dashboard option, matching READMEs, screenshot galleries, and automated regression checks.

**Migration:** Default entry points now launch the Workbench. The old single-instance stack is explicit under `--legacy`; raw database directories are not automatically migrated.

**Scope:** WSC 6.3 is an unofficial development build. Remote restore remains guided. See the [test notes](docs/user-test.md) for executed checks and platform limitations.
