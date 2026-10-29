# wsc-local · WoltLab Workbench

**[Deutsch](README.md) · [English](README.en.md)**

**Aktuelle Version: [v1.2.2](https://github.com/benjarogit/wsc-local/releases/tag/v1.2.2)** · [ZIP herunterladen](https://github.com/benjarogit/wsc-local/releases/download/v1.2.2/wsc-local-1.2.2.zip) · [Änderungen](CHANGELOG.md)

WoltLab Suite lokal vorbereiten, automatisch installieren und verwalten – über ein übersichtliches Browser-Dashboard und dieselbe CLI. Mehrere Projekte laufen getrennt nebeneinander, mit eigenen Dateien, Datenbanken, Ports und Zugangsdaten.

**Linux · macOS · Windows über WSL2** · **Deutsch als Standard, Englisch im Dashboard umschaltbar**

<a href="docs/screenshots/home-de.png"><img src="docs/screenshots/home-de.png" alt="wsc-local: erster Start ohne Projekte mit geführtem Einstieg" width="1100"></a>

<p align="center">Vorschau anklicken, um den Screenshot groß zu öffnen.</p>

<table align="center">
  <tr>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/create-de.png" title="Projekt vorbereiten"><img src="docs/screenshots/create-de.png" alt="Projekt vorbereiten" width="160"><br><sub>Projekt vorbereiten</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/advanced-de.png" title="Erweiterte Einstellungen"><img src="docs/screenshots/advanced-de.png" alt="Erweiterte Einstellungen" width="160"><br><sub>Erweiterte Einstellungen</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/installing-de.png" title="Automatische Einrichtung"><img src="docs/screenshots/installing-de.png" alt="Automatische Einrichtung" width="160"><br><sub>Automatische Einrichtung</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/overview-de.png" title="Projektübersicht"><img src="docs/screenshots/overview-de.png" alt="Projektübersicht" width="160"><br><sub>Projektübersicht</sub></a></td>
  </tr>
  <tr>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/credentials-de.png" title="Zugangsdaten – verborgen"><img src="docs/screenshots/credentials-de.png" alt="Zugangsdaten – verborgen" width="160"><br><sub>Zugangsdaten – verborgen</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/services-de.png" title="Dienste und Logs"><img src="docs/screenshots/services-de.png" alt="Dienste und Logs" width="160"><br><sub>Dienste und Logs</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/backups-de.png" title="Sicherungen und Export"><img src="docs/screenshots/backups-de.png" alt="Sicherungen und Export" width="160"><br><sub>Sicherungen und Export</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/tools-de.png" title="WoltLab-Werkzeuge"><img src="docs/screenshots/tools-de.png" alt="WoltLab-Werkzeuge" width="160"><br><sub>WoltLab-Werkzeuge</sub></a></td>
  </tr>
  <tr>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/system-de.png" title="Systemprüfung"><img src="docs/screenshots/system-de.png" alt="Systemprüfung" width="160"><br><sub>Systemprüfung</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/help-de.png" title="Hilfe und Einstieg"><img src="docs/screenshots/help-de.png" alt="Hilfe und Einstieg" width="160"><br><sub>Hilfe und Einstieg</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/migration-de.png" title="Umzugsdialog"><img src="docs/screenshots/migration-de.png" alt="Umzugsdialog" width="160"><br><sub>Umzugsdialog</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/dark-de.png" title="Dark Mode"><img src="docs/screenshots/dark-de.png" alt="Dark Mode" width="160"><br><sub>Dark Mode</sub></a></td>
  </tr>
  <tr>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/setup-language-de.png" title="Installationssprache"><img src="docs/screenshots/setup-language-de.png" alt="Installationssprache" width="160"><br><sub>Installationssprache</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/acp-de.png" title="Direkt im ACP"><img src="docs/screenshots/acp-de.png" alt="Direkt im ACP" width="160"><br><sub>Direkt im ACP</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/prerequisites-de.png" title="Voraussetzungen (Beispiel)"><img src="docs/screenshots/prerequisites-de.png" alt="Voraussetzungen (Beispiel)" width="160"><br><sub>Voraussetzungen (Beispiel)</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/mobile-de.png" title="Mobile Ansicht"><img src="docs/screenshots/mobile-de.png" alt="Mobile Ansicht" height="110"><br><sub>Mobile Ansicht</sub></a></td>
  </tr>
  <tr>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/updates-de.png" title="Update-Übersicht (Beispiel)"><img src="docs/screenshots/updates-de.png" alt="Update-Übersicht (Beispiel)" width="160"><br><sub>Update-Übersicht (Beispiel)</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/update-confirm-de.png" title="Update bestätigen"><img src="docs/screenshots/update-confirm-de.png" alt="Update bestätigen" width="160"><br><sub>Update bestätigen</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/update-guide-de.png" title="Update-Anleitung"><img src="docs/screenshots/update-guide-de.png" alt="Update-Anleitung" width="160"><br><sub>Update-Anleitung</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/update-progress-de.png" title="Update-Fortschritt"><img src="docs/screenshots/update-progress-de.png" alt="Update-Fortschritt" width="160"><br><sub>Update-Fortschritt</sub></a></td>
  </tr>
</table>

Die Aufnahmen zeigen den aktuellen Stand mit echten WoltLab-Testprojekten; Passwörter bleiben verborgen. Voraussetzungen- und Update-Dialoge zeigen gekennzeichnete Beispielfälle: eine fehlende HTTPS-Freigabe und ein lokales Test-Update von 1.2.0 auf 1.2.1. Die Update-Aufnahmen stammen aus einem echten Programmaustausch mit Dashboard-Neustart in einem isolierten Testordner; die gezeigte Version 1.2.1 ist seit dem 29.10.2026 öffentlich verfügbar. [Aufnahmen und Ablauf](docs/screenshots/README.md)

## Schnellstart

Lade zuerst das Repository herunter ([ZIP](https://github.com/benjarogit/wsc-local/releases/download/v1.2.2/wsc-local-1.2.2.zip) oder Git) und entpacke es. Die folgenden Befehle werden im Projektordner ausgeführt; dort liegen auch die Windows-Starter.

### Voraussetzungen einmalig installieren

**Geführte Einrichtung:** Linux/macOS: `bash ./setup.sh --install-deps`. Windows: **`Install-wsc-local.cmd` doppelklicken** (oder `Start-wsc-local.ps1 -InstallDependencies`). Danach den normalen Starter öffnen. Wenn das Dashboard bereits läuft, bietet **Systemprüfung → Fehlendes einrichten** denselben Ablauf mit Vorschau an.

Die Einrichtung installiert fehlende Pakete und richtet lokales HTTPS im Systemterminal ein. Linux verwendet apt/dnf/pacman, macOS Homebrew, Windows winget und WSL2. Systempasswörter werden ausschließlich im Terminal bzw. im Betriebssystemdialog eingegeben. WSL-Ersteinrichtung, Docker-Desktop-Freigabe, Neustarts oder erneutes Anmelden können erforderlich bleiben. Vorhandene Docker-Installationen werden nicht ersetzt; bei Konflikten nennt die Systemprüfung die nächsten Schritte. [Plattformen und Grenzen](docs/platforms.md)

Alternativ kannst du die Voraussetzungen selbst installieren:

- **Python 3.10 oder neuer.**
- **Docker mit Docker Compose**, gestartet und vom aktuellen Benutzer erreichbar. Die Workbench benötigt Linux-Container.
- **mkcert** für vertrauenswürdiges lokales HTTPS; unter Linux gegebenenfalls NSS für deinen Browser.
- Internet für Container-Images und den Core-Download. Ein eigenes Installations-ZIP ist ebenfalls möglich.

Die [Plattform-Anleitung](docs/platforms.md) beschreibt Linux, macOS und Windows/WSL2 einschließlich der Zertifikatsfreigabe. Node.js wird nur für die Entwicklungstests benötigt.

### Linux und macOS

```bash
git clone https://github.com/benjarogit/wsc-local.git
cd wsc-local
./setup.sh
```

`setup.sh` prüft die Voraussetzungen, begleitet die einmalige HTTPS-Vertrauensstellung im Terminal und öffnet das Dashboard. Fehlende Voraussetzungen und passende Hilfen findest du unter **Systemprüfung**.

Später reicht `./start.sh` oder `./panel.sh`. Ohne Browserstart: `./start.sh --no-open`. Anderer Dashboard-Port: `./start.sh --port 9199`. Die Standardadresse ist `http://127.0.0.1:9099/`.

### Windows

1. [WSL2](https://learn.microsoft.com/windows/wsl/install) mit einer Linux-Distribution einrichten.
2. Docker Desktop starten, **Linux-Container** verwenden und die WSL-Integration für diese Distribution aktivieren.
3. Python und mkcert in WSL installieren; mkcert zusätzlich unter Windows installieren, damit der Windows-Browser derselben lokalen Zertifizierungsstelle vertraut.
4. Repository klonen und **`Start-wsc-local.cmd` doppelklicken**, oder im WSL-Terminal `./setup.sh` ausführen.

Bei mehreren Distributionen: `Start-wsc-local.ps1 -Distribution Ubuntu`. [Details und Befehle](docs/platforms.md#windows-mit-wsl2)

## In drei Schritten zur fertigen Suite

1. **Projekt vorbereiten:** Name, Suite-Version und Quelle wählen. Nginx/PHP-FPM mit MariaDB ist der Standard. Apache, passende PHP-Profile, MySQL 8 und eigene Adminwerte stehen unter den optionalen Einstellungen.
2. **Sprache und Login-Daten prüfen:** Oben DE oder EN wählen; diese Sprache übernimmt die Suite bei der Einrichtung. Den sicher erzeugten Adminzugang ansehen und bei Bedarf Name, E-Mail und Passwort ändern.
3. **Einrichten:** Die Workbench startet die Umgebung, richtet HTTPS ein und installiert WoltLab vollständig. Website, Ressourcen und tatsächliche Admin-Anmeldung werden geprüft. Danach öffnest du die Website oder meldest dich über **ACP öffnen** direkt in der Administration an.

Es gibt keine manuelle WoltLab-Installer-Klickstrecke. Spinner und Arbeitsschritte zeigen den Fortschritt. Nach Neuladen verbindet sich die Oberfläche wieder mit laufenden Vorgängen – auch wenn die erste Startantwort verloren gegangen ist.

## Oberfläche und Funktionen

- **Projekte:** Zustand, Website, Administration und Start/Stopp direkt an der Karte. **Verwalten** öffnet die Bereiche Übersicht, Zugangsdaten, Dienste, Sicherungen und Werkzeuge.
- **ACP öffnen:** Meldet dich mit dem gespeicherten Adminzugang direkt in der Administration an. Die Sitzung wird über eine kurz gültige Einmal-Übergabe übertragen; Passwörter stehen nicht in URLs. Bei geändertem Passwort oder Zwei-Faktor-Anmeldung bietet der Dialog die normale ACP-Anmeldung an.
- **Zugangsdaten:** Anzeigen und Kopieren von Admin- und getrennten Datenbankdaten. Passwörter bleiben zunächst verborgen. Nach der Installation änderst du den Adminzugang in WoltLab.
- **Dienste:** Status und Logs von Webserver, PHP und Datenbank. Den optionalen Mailpit-Testdienst schaltest du separat ein. Für Test-E-Mails in WoltLab: SMTP `mail:1025`, ohne Anmeldung.
- **Sicherungen:** Dateisystem und Datenbank gemeinsam sichern, Prüfsummen kontrollieren und einen Stand wiederherstellen. Vor dem Restore wird der aktuelle Stand gesichert.
- **Export und Serverumzug:** Ein Paket mit Dateien, SQL-Dump, Projektkonfiguration, Prüfsummen und Importanleitung erstellen und herunterladen. **Serverumzug vorbereiten** ergänzt die Erklärung für den Zielserver und verwendet dasselbe Exportformat. Das Einspielen auf dem Server ist geführt; SSH-Deployments sind nicht enthalten.
- **WoltLab-Werkzeuge:** Diagnose, Uploadlimits mit Änderungsvorschau, offizielles Recovery Tool und dessen Entfernung. Domain- und Verzeichniswerkzeuge erstellen eine Sicherung und öffnen die Anleitung; sie ändern App-Pfade oder Datenbankwerte nicht automatisch.
- **Entfernen:** Projektdateien, Datenbank, Container, Netzwerke und lokale Zugangsdaten nach Bestätigung des Projektnamens entfernen. Gemeinsame Basisimages, Download-Caches und die lokale CA bleiben erhalten.

Informationssymbole öffnen Erklärungen. Bestätigungen, Eingaben und Vorschauen erscheinen in Dialogen mit Abbrechen und Tastaturbedienung. [Werkzeuge und Umzugsablauf im Detail](docs/tools.md)

### Sprache und Darstellung

**Deutsch ist der Standard**, unabhängig von der Browsersprache. Über den **DE/EN-Schalter mit Globus-Icon** oben wechselst du die Dashboard-Sprache; die Auswahl bleibt in diesem Browser gespeichert. Die aktuellen Projektbereiche werden beim Wechsel wieder geöffnet. CLI-Ausgaben und technische Dienstprotokolle bleiben in ihrer Originalsprache.

Bei **Einrichten** übernimmt eine neue WoltLab-Installation die aktuelle Dashboard-Sprache für die Suite-Standardsprache und den ersten Adminbenutzer. Ein Sprachwechsel während der laufenden Einrichtung ändert diese Auswahl nicht mehr. Bereits installierte Websites bleiben unverändert. Die CLI verwendet die Systemsprache (`LC_ALL`, `LC_MESSAGES`, `LANG`; Englisch → EN, sonst Deutsch) oder eine explizite Wahl: `./wsc install mein-forum --language en`. Bei einer Wiederaufnahme bleibt die gespeicherte Auswahl erhalten.

Monitor, Sonne und Mond wählen **System, Hell oder Dunkel** direkt aus. Der aktive Modus ist markiert; System folgt der Geräteeinstellung. Die Darstellung ändert die Workbench, nicht das Design deiner WoltLab-Website.


## Suite-Versionen und Installationsarchive

Die Profile orientieren sich am [offiziellen WoltLab-Handbuch](https://manual.woltlab.com/de/php-compatibility/). Alpha und Legacy erfordern eine bewusste Bestätigung.

- **WSC 6.2:** automatischer Download von Core 6.2.8 mit SHA-256-Prüfung oder eigenes ZIP. Das Standardprofil verwendet PHP 8.4 und lokales HTTPS.
- **WSC 6.3:** inoffizieller Entwicklungsbuild aus [YoureCom/wsc-63-testbuilds](https://github.com/YoureCom/wsc-63-testbuilds), gebaut aus WoltLab/WCF. Profil mit PHP 8.5 und HTTPS; für lokale Tests.
- **WSC 5.5, 6.0 und 6.1:** eigenes passendes Installations-ZIP erforderlich. Legacy-Profile sind entsprechend gekennzeichnet.

Eigene ZIPs wählst du direkt im Dashboard aus, maximal 256 MiB und mit `install.php`. Lizenzpflichtige Anwendungen benötigen dein eigenes geeignetes Archiv und eine passende WoltLab-Lizenz. Der freie Core benötigt beim lokalen Setup keine Lizenzzugangsdaten.

Die geprüften WSC-6.2/6.3-Dateien benötigen eine gezielte Korrektur für lokale Ports. Die Workbench ersetzt ausschließlich den exakt erkannten Codeblock und dokumentiert Originaldatei sowie Prüfsummen unter `config/compatibility/`. Nach WoltLab-Updates muss diese Kompatibilität erneut geprüft werden.

## CLI und teilbare Projektprofile

```bash
./wsc --version
./wsc check
./wsc create mein-forum --download-core
./wsc install mein-forum
./wsc list
./wsc start mein-forum
./wsc stop mein-forum
./wsc status mein-forum
./wsc logs mein-forum --service database
./wsc doctor mein-forum
./wsc snapshot mein-forum
./wsc snapshots mein-forum
./wsc restore mein-forum PFAD_ZUR_SICHERUNG
./wsc export mein-forum
./wsc remove mein-forum
```

Ein unter **Übersicht** heruntergeladenes Projektprofil enthält nur Suite-, PHP-, Webserver- und Datenbankauswahl, ohne Passwörter und lokale Ports:

```bash
./wsc create zweites-projekt --profile mein-forum.wsc-local.json --download-core
```

Das neue Projekt bekommt eigene Zugangsdaten und Ports. Das Profil enthält keine Website-Dateien oder Datenbankinhalte; dafür dienen Sicherung und Export.

## Daten, HTTPS und Umzug

Projekte liegen standardmäßig unter `~/.local/share/wsc-local/projects/`, Geheimnisse getrennt unter `~/.config/wsc-local/secrets/`. `WSC_LOCAL_HOME` und `XDG_CONFIG_HOME` ändern diese Pfade. Unter Windows gelten die Pfade innerhalb von WSL.

Das Dashboard und veröffentlichte Containerports binden an Loopback. Lokales HTTPS nutzt mkcert. Let's Encrypt ist für öffentliche Domains am Zielserver vorgesehen, nicht für `localhost`.

Exporte entfernen Workbench-eigene lokale Datenbankzugangsdaten aus `config.inc.php` und enthalten keine lokale `.env` oder TLS-Schlüssel. WoltLab-Inhalte und dessen Datenbank bleiben Bestandteil des Pakets; behandle es wie eine vollständige Datensicherung. Temporäre Recovery- und Authentifizierungsdateien sind ausgeschlossen.

`./wsc import QUELLE projektname` erkennt ältere wsc-local-Dateien, alte Snapshots und Workbench-Exportpakete. Alte rohe Datenbankordner werden nicht zwischen Datenbankprofilen kopiert; ein vollständiger Stand benötigt einen passenden Dump bzw. Export. [Teststand und Grenzen](docs/user-test.md)

## Aktualisieren und alte Installation

Ab **1.2.0** meldet die Workbench neue stabile Releases direkt im Dashboard. Unter **Updates** kannst du nach Vorschau automatisch aktualisieren oder die manuelle Anleitung öffnen. Git- und ZIP-Installationen werden erkannt. Prüfsummen, Schutz lokaler Änderungen, Wiederherstellungsstand und automatischer Dashboard-Neustart gehören zum Ablauf; WoltLab-Projekte und Zugangsdaten bleiben erhalten.

```bash
./wsc update --check   # Neue Version suchen
./wsc update           # Mit Vorschau und Bestätigung installieren
./wsc update --guide   # Wahlweise selbst aktualisieren
```

**Von 1.1.0 oder älter:** einmal `git pull --ff-only` und `./start.sh` ausführen. Bei einer ZIP-Installation die Programmdateien nach Anleitung in den bestehenden Ordner übernehmen und persönliche Daten erhalten. Danach steht die Updatefunktion für kommende Releases bereit. [Update, Konflikte und Wiederherstellung im Detail](docs/updating.md)

**Releases entstehen automatisch:** Ein neuer Versions-Tag startet die GitHub-Prüfungen; nach deren Erfolg veröffentlicht der Workflow ZIP und SHA-256-Prüfsumme. Die Version steht oben in dieser README und im Dashboard-Fußbereich.

Der frühere Einzel-Stack ist ausdrücklich über `./setup.sh --legacy` und `./start.sh --legacy` verfügbar. `tools.sh` und `reset.sh` gehören zu diesem alten Stack; für Workbench-Projekte verwende das Dashboard beziehungsweise `./wsc`.

## Tests, Herkunft und Release

```bash
python3 -m unittest discover -s tests -v
npm ci
npx playwright install chromium
npm run test:ui
```

Für die lokale Kurzprüfung gibt es `python3 scripts/check.py`; mit `--ui` laufen zusätzlich die Chromium-Tests, mit `--release` werden Release-Metadaten und das ZIP probeweise geprüft. Die CI bleibt maßgeblich und prüft portable Logik auf Linux, macOS und Windows sowie Browserabläufe mit isolierten API-Antworten. Echte WoltLab-/Docker-Installationen wurden lokal unter Linux geprüft. Vollständige Docker-/Browser-Abnahmen auf macOS und Windows/WSL2 sind gesonderte Plattformtests. [Ausführliches Testprotokoll](docs/user-test.md)

[wsc-dockerized](https://github.com/SoftCreatRMedia/wsc-dockerized) liefert WoltLab-spezifische Anregungen; [DDEV](https://github.com/ddev/ddev) projektbezogene Konfiguration; [Lando](https://docs.lando.dev/plugins/) Profile und optionale Dienste; [XAMPP](https://github.com/ApacheFriends/xampp-control-windows) direkte Dienststeuerung. Die Workbench bleibt ausschließlich auf WoltLab ausgerichtet. Font Awesome Free ist lokal samt [Lizenz und Quellen](panel/vendor/fontawesome/) eingebunden.

[Produktgrundsätze](docs/product.md) · [Änderungen und Release-Hinweise](CHANGELOG.md) · [GitHub-Releases](https://github.com/benjarogit/wsc-local/releases)
