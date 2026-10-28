# Änderungen / Changelog

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
