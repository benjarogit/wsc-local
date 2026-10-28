# wsc-local · WoltLab Workbench

**[Deutsch](README.md) · [English](README.en.md)**

WoltLab Suite lokal vorbereiten, automatisch installieren und verwalten – über ein übersichtliches Browser-Dashboard und dieselbe CLI. Mehrere Projekte laufen getrennt nebeneinander, mit eigenen Dateien, Datenbanken, Ports und Zugangsdaten.

**Linux · macOS · Windows über WSL2** · **Deutsch als Standard, Englisch im Dashboard umschaltbar**

<a href="docs/screenshots/home-de.png"><img src="docs/screenshots/home-de.png" alt="wsc-local: Startseite mit lokalen WoltLab-Projekten" width="1100"></a>

## Schnellstart

### Voraussetzungen einmalig installieren

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
2. **Login-Daten prüfen:** Den sicher erzeugten Adminzugang ansehen und bei Bedarf Name, E-Mail und Passwort ändern.
3. **Einrichten:** Die Workbench startet die Umgebung, richtet HTTPS ein und installiert WoltLab vollständig. Website, Ressourcen und tatsächliche Admin-Anmeldung werden geprüft. Danach öffnest du Website oder Administration direkt über die Projektkarte.

Es gibt keine manuelle WoltLab-Installer-Klickstrecke. Spinner und Arbeitsschritte zeigen den Fortschritt. Nach Neuladen verbindet sich die Oberfläche wieder mit laufenden Vorgängen – auch wenn die erste Startantwort verloren gegangen ist.

## Oberfläche und Funktionen

- **Projekte:** Zustand, Website, Administration und Start/Stopp direkt an der Karte. **Verwalten** öffnet die Bereiche Übersicht, Zugangsdaten, Dienste, Sicherungen und Werkzeuge.
- **Zugangsdaten:** Anzeigen und Kopieren von Admin- und getrennten Datenbankdaten. Passwörter bleiben zunächst verborgen. Nach der Installation änderst du den Adminzugang in WoltLab.
- **Dienste:** Status und Logs von Webserver, PHP und Datenbank. Den optionalen Mailpit-Testdienst schaltest du separat ein. Für Test-E-Mails in WoltLab: SMTP `mail:1025`, ohne Anmeldung.
- **Sicherungen:** Dateisystem und Datenbank gemeinsam sichern, Prüfsummen kontrollieren und einen Stand wiederherstellen. Vor dem Restore wird der aktuelle Stand gesichert.
- **Export und Serverumzug:** Ein Paket mit Dateien, SQL-Dump, Projektkonfiguration, Prüfsummen und Importanleitung erstellen und herunterladen. **Serverumzug vorbereiten** ergänzt die Erklärung für den Zielserver und verwendet dasselbe Exportformat. Das Einspielen auf dem Server ist geführt; SSH-Deployments sind nicht enthalten.
- **WoltLab-Werkzeuge:** Diagnose, Uploadlimits mit Änderungsvorschau, offizielles Recovery Tool und dessen Entfernung. Domain- und Verzeichniswerkzeuge erstellen eine Sicherung und öffnen die Anleitung; sie ändern App-Pfade oder Datenbankwerte nicht automatisch.
- **Entfernen:** Projektdateien, Datenbank, Container, Netzwerke und lokale Zugangsdaten nach Bestätigung des Projektnamens entfernen. Gemeinsame Basisimages, Download-Caches und die lokale CA bleiben erhalten.

Informationssymbole öffnen Erklärungen. Bestätigungen, Eingaben und Vorschauen erscheinen in Dialogen mit Abbrechen und Tastaturbedienung. [Werkzeuge und Umzugsablauf im Detail](docs/tools.md)

### Sprache und Darstellung

**Deutsch ist der Standard**, unabhängig von der Browsersprache. Über **EN / DE** oben wechselst du die Dashboard-Sprache; die Auswahl bleibt in diesem Browser gespeichert. Die aktuellen Projektbereiche werden beim Wechsel wieder geöffnet. CLI-Ausgaben und technische Dienstprotokolle bleiben in ihrer Originalsprache.

Monitor, Sonne und Mond wählen **System, Hell oder Dunkel** direkt aus. Der aktive Modus ist markiert; System folgt der Geräteeinstellung. Die Darstellung ändert die Workbench, nicht das Design deiner WoltLab-Website.

### Screenshots

Ein Klick auf eine Vorschau öffnet das Bild in voller Größe. Die Aufnahmen zeigen die tatsächliche Oberfläche; Zugangsdaten sind verborgen beziehungsweise für die Dokumentation anonymisiert.

<p>
  <a href="docs/screenshots/create-de.png" title="Projekt vorbereiten"><img src="docs/screenshots/create-de.png" alt="Projekt vorbereiten" width="280"></a>
  <a href="docs/screenshots/advanced-de.png" title="Erweiterte Einstellungen"><img src="docs/screenshots/advanced-de.png" alt="Erweiterte Einstellungen" width="280"></a>
  <a href="docs/screenshots/installing-de.png" title="Automatische Einrichtung"><img src="docs/screenshots/installing-de.png" alt="Automatische Einrichtung" width="280"></a>
</p>
<p>
  <a href="docs/screenshots/overview-de.png" title="Projektübersicht"><img src="docs/screenshots/overview-de.png" alt="Projektübersicht" width="280"></a>
  <a href="docs/screenshots/credentials-de.png" title="Zugangsdaten – verborgen"><img src="docs/screenshots/credentials-de.png" alt="Zugangsdaten – verborgen" width="280"></a>
  <a href="docs/screenshots/services-de.png" title="Dienste und Logs"><img src="docs/screenshots/services-de.png" alt="Dienste und Logs" width="280"></a>
</p>
<p>
  <a href="docs/screenshots/backups-de.png" title="Sicherungen und Export"><img src="docs/screenshots/backups-de.png" alt="Sicherungen und Export" width="280"></a>
  <a href="docs/screenshots/tools-de.png" title="WoltLab-Werkzeuge"><img src="docs/screenshots/tools-de.png" alt="WoltLab-Werkzeuge" width="280"></a>
  <a href="docs/screenshots/system-de.png" title="Systemprüfung"><img src="docs/screenshots/system-de.png" alt="Systemprüfung" width="280"></a>
</p>
<p>
  <a href="docs/screenshots/help-de.png" title="Hilfe und Einstieg"><img src="docs/screenshots/help-de.png" alt="Hilfe und Einstieg" width="280"></a>
  <a href="docs/screenshots/migration-de.png" title="Umzugsdialog"><img src="docs/screenshots/migration-de.png" alt="Umzugsdialog" width="280"></a>
  <a href="docs/screenshots/dark-de.png" title="Dark Mode"><img src="docs/screenshots/dark-de.png" alt="Dark Mode" width="280"></a>
</p>

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

```bash
git pull --ff-only
./panel.sh
```

Der Starter aktualisiert ausschließlich den zu diesem Repository gehörenden Dashboard-Server und schützt laufende Vorgänge. Versionskennungen verhindern Änderungen mit einer veralteten Oberfläche. Projektdateien liegen außerhalb des Repositories.

Der frühere Einzel-Stack ist ausdrücklich über `./setup.sh --legacy` und `./start.sh --legacy` verfügbar. `tools.sh` und `reset.sh` gehören zu diesem alten Stack; für Workbench-Projekte verwende das Dashboard beziehungsweise `./wsc`.

## Tests, Herkunft und Release

```bash
python3 -m unittest discover -s tests -v
npm ci
npx playwright install chromium
npm run test:ui
```

Die CI prüft portable Logik auf Linux, macOS und Windows sowie Browserabläufe mit isolierten API-Antworten. Echte WoltLab-/Docker-Installationen wurden lokal unter Linux geprüft. Vollständige Docker-/Browser-Abnahmen auf macOS und Windows/WSL2 sind gesonderte Plattformtests. [Ausführliches Testprotokoll](docs/user-test.md)

[wsc-dockerized](https://github.com/SoftCreatRMedia/wsc-dockerized) liefert WoltLab-spezifische Anregungen; [DDEV](https://github.com/ddev/ddev) projektbezogene Konfiguration; [Lando](https://docs.lando.dev/plugins/) Profile und optionale Dienste; [XAMPP](https://github.com/ApacheFriends/xampp-control-windows) direkte Dienststeuerung. Die Workbench bleibt ausschließlich auf WoltLab ausgerichtet. Font Awesome Free ist lokal samt [Lizenz und Quellen](panel/vendor/fontawesome/) eingebunden.

[Produktgrundsätze](docs/product.md) · [Änderungen und Release-Hinweise](CHANGELOG.md) · [GitHub-Releases](https://github.com/benjarogit/wsc-local/releases)
