# Eine WoltLab-Workbench

## Verbindlicher Produktzweck

wsc-local installiert und verwaltet WoltLab Suite lokal. Die Zielsysteme sind Linux, macOS und Windows über WSL2. Einsteiger erhalten empfohlene Werte und eine automatische Installation; Entwickler können passende Profile und Dienste wählen. Das offizielle WoltLab-Handbuch und der tatsächliche Installer bestimmen die Voraussetzungen.

## Inspirationen und Umsetzung

- **[SoftCreatRMedia/wsc-dockerized](https://github.com/SoftCreatRMedia/wsc-dockerized):** WoltLab-spezifische PHP-/Datenbankprofile, sinnvolle Erweiterungen und Dienstnamen innerhalb des Docker-Netzes. Die Workbench wählt passende Profile und verwendet den internen Datenbankhost automatisch. Versionsabhängige Funktionen werden nicht pauschal auf neuere Suites übertragen; beispielsweise beschreibt die Quelle Redis nur für Versionen unter 6.3.
- **[DDEV](https://github.com/ddev/ddev):** ein Projekt als Verwaltungseinheit, parallele Projekte, konsistente CLI-Befehle und teilbare Konfiguration. Die Workbench erzeugt neue Ports und Geheimnisse je Projekt; das im Dashboard exportierte Profil enthält nur die Stack-Auswahl.
- **[Lando](https://docs.lando.dev/plugins/):** Profile und optionale Dienste statt beliebiger Kombinationen. Die GUI bietet zum Suite-Profil passende PHP-Auswahl und integrierte Optionen. Ein frei installierbares Drittanbieter-Plugin-System ist nicht Teil des Produkts.
- **[XAMPP Control Panel](https://github.com/ApacheFriends/xampp-control-windows):** erkennbare Dienstzustände, direkte Start-/Stopp-Aktionen und erreichbare Logs. Die Workbench zeigt eine Dienstübersicht für das gewählte Projekt, ohne an eine Windows-Desktop-Technik gebunden zu sein.

Das sind eigenständig umgesetzte Konzepte. Datenbankzugänge oder veraltete Kompatibilitätsangaben der Vorbilder werden nicht ungeprüft übernommen. Kostenpflichtige Anwendungen erfordern weiterhin ein passendes eigenes Installationsarchiv bzw. die nötige WoltLab-Lizenz.

## Bedienung

- Hauptnavigation: Projekte, Systemprüfung, Hilfe.
- Projektvorbereitung in einem begrenzten Dialog. Technik und eigene Adminwerte sind optional.
- Nach dem Vorbereiten öffnet sich der Adminzugang zur Prüfung. „Einrichten“ übernimmt den vollständigen Installer-Ablauf.
- Projektkarte: Zustand, Profil, Website, Administration und Start/Stopp.
- Genau eine ausgewählte Projektansicht: Übersicht, Zugangsdaten, Dienste, Sicherungen oder Werkzeuge.
- Laufende Einrichtung: sichtbarer Spinner, konkrete Arbeitsschritte und Wiederaufnahme der Anzeige nach Neuladen.
- Fehler: Ursache und nächster Schritt; lange technische Meldungen gehören ins Protokoll. Änderungen an Uploadlimits zeigen eine Vorschau. Löschen und Wiederherstellen benötigen eine ausdrückliche Bestätigung.

## Daten und Grenzen

Passwörter liegen außerhalb der teilbaren Profile. Sicherungen halten Dateisystem und Datenbank zusammen. Ein Server-Export enthält Dateien, Dump und Anleitung; das Tool meldet keinen erfolgreichen Remote-Deploy. Legacy- und Alpha-Profile sind entsprechend markiert.

Die Plattformunterstützung umfasst Starter, Hostprüfung, Docker-Anbindung, Dateipfade und lokales HTTPS. Eine wirkliche Freigabe pro Betriebssystem braucht die dortige Docker-/Browser-Abnahme; der [Teststand](user-test.md) bleibt dafür maßgeblich.
