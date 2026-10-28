# Betrieb auf Linux, macOS und Windows

Alle Plattformen verwenden denselben Python-Projektmanager, dieselben WoltLab-Profile und dasselbe lokale Browser-Dashboard. Windows läuft wie vereinbart über WSL2; die nativen Windows-Starter übernehmen den Einstieg.

## Geführte Installation fehlender Voraussetzungen

Linux/macOS: `bash ./setup.sh --install-deps`. Windows: **`Install-wsc-local.cmd` doppelklicken**; alternativ `Start-wsc-local.ps1 -InstallDependencies`. Vorab ohne Änderungen ansehen: `bash ./setup.sh --install-deps --dry-run` bzw. `Install-wsc-local.ps1 -DryRun`.

Im laufenden Dashboard öffnet **Systemprüfung → Fehlendes einrichten** eine Vorschau und danach ein Systemterminal. Dort laufen Paketinstallation und HTTPS-Freigabe. Die Workbench wartet auf das Skriptende und prüft anschließend erneut. Ein geöffnetes Terminal allein bedeutet noch keinen Erfolg. Bei fehlendem grafischem Terminal erscheint der direkt ausführbare Befehl. Das Dashboard benötigt selbst Python 3.10+; ohne Python verwendest du den nativen Einstieg oben.

- **Linux:** apt/dnf/pacman für Python, mkcert und NSS. Fehlendes Docker wird für diese lokale Entwicklungsumgebung über das [offizielle Docker-Installationsskript](https://github.com/docker/docker-install) eingerichtet; auf Arch über native Pakete. Das Docker-Skript verändert Paketquellen und benötigt sudo. Eine Docker-Gruppenmitgliedschaft gewährt administrativen Zugriff; danach neu anmelden und die Workbench neu starten. Bestehendes Docker wird nicht ersetzt. Kann dessen Compose-Plugin aus den vorhandenen Quellen nicht installiert werden, bleiben die Meldungen im Terminal und die offizielle Anleitung verfügbar.
- **macOS:** bei Bedarf [Homebrew](https://docs.brew.sh/Installation), fehlende Pakete und Docker Desktop. Homebrew/Systemabfragen und die erste Docker-Desktop-Freigabe bleiben sichtbar.
- **Windows/WSL2:** winget-Pakete `Docker.DockerDesktop` und `FiloSottile.mkcert`, fehlendes WSL mit Ubuntu über `wsl --install`. Windows-Neustart und das erstmalige Anlegen des Ubuntu-Benutzers bleiben gegebenenfalls erforderlich. Danach das Skript erneut starten. Die Docker-Desktop-WSL-Integration muss für die gewählte Distribution freigegeben sein. Nach neu installierten Windows-Programmen WSL neu öffnen, damit der Suchpfad aktualisiert ist.

Systempasswörter werden niemals im Dashboard abgefragt. Nicht unterstützte Linux-Paketverwaltungen erhalten die manuelle Anleitung. Ein nativer macOS-/Windows-Paketinstallationslauf ist vorerst **nicht als getestet ausgewiesen**; CI prüft dort portable Logik und Skriptsyntax, keine Administratorinstallationen.

## Linux

Benötigt werden Python 3.10+, Docker Engine oder Docker Desktop mit Compose sowie mkcert. Bei Firefox/Chromium gehört NSS zur lokalen Zertifikatsfreigabe. Unter Debian/Ubuntu zum Beispiel:

```bash
sudo apt install python3 mkcert libnss3-tools
```

Docker nach der [offiziellen Anleitung](https://docs.docker.com/engine/install/) inklusive [Compose-Plugin](https://docs.docker.com/compose/install/) installieren und starten. Der Benutzer muss Docker ohne interaktive sudo-Abfrage ansprechen können.

Im Repository `./setup.sh` ausführen. Die einmalige Zertifikatsfreigabe läuft im Terminal, bevor der Dashboard-Server im Hintergrund startet.

## macOS

Python und mkcert mit NSS lassen sich über Homebrew installieren:

```bash
brew install python mkcert nss
```

Docker Desktop oder einen kompatiblen Docker-Anbieter starten. Anschließend `./setup.sh` im Repository ausführen. Systemabfragen zur lokalen Zertifizierungsstelle bestätigen. Bash und Python übernehmen den Start; es werden keine Linux-Paketbefehle unter macOS ausgeführt.

## Windows mit WSL2

1. WSL2 mit einer Linux-Distribution einrichten: [Microsoft-Anleitung](https://learn.microsoft.com/windows/wsl/install).
2. Docker Desktop starten. Unter den Docker-Einstellungen die WSL-Integration für diese Distribution aktivieren und Linux-Container verwenden.
3. In WSL Python, mkcert und NSS installieren; für Ubuntu gelten die Linux-Befehle oben.
4. mkcert zusätzlich unter Windows nach der [offiziellen Windows-Anleitung](https://github.com/FiloSottile/mkcert#windows) installieren, beispielsweise über Chocolatey oder Scoop. WSL danach neu öffnen, damit `mkcert.exe` im Suchpfad gefunden wird.
5. `Start-wsc-local.cmd` doppelklicken oder im WSL-Terminal `./setup.sh` starten.

Der Windows-Starter unterstützt Repository-Pfade mit Leerzeichen, Windows-Laufwerke und `\\wsl.localhost\DISTRIBUTION\...` bzw. `\\wsl$\DISTRIBUTION\...`. Bei mehreren Distributionen:

```powershell
.\Start-wsc-local.ps1 -Distribution Ubuntu
.\Start-wsc-local.ps1 -Distribution Ubuntu -Check
```

Für große Projekte ist die Ablage im WSL-Dateisystem sinnvoll; Docker muss die Projektdateien aus der gewählten Distribution lesen können.

### HTTPS im Windows-Browser

Ein Zertifikat, dem nur Linux vertraut, reicht für den Windows-Browser nicht. Die Workbench richtet die lokale CA über `mkcert.exe` in Windows ein und verwendet deren `CAROOT` auch für mkcert in WSL. Der private CA-Schlüssel wird weder in Projektprofile noch in Exporte aufgenommen.

Fehlt Windows-mkcert oder ist die gemeinsame CA nicht erreichbar, nennt die Systemprüfung die Ursache. Die Einrichtung gibt dann keinen Erfolg für ein unvollständiges HTTPS-Setup aus. Browser nach einer erstmaligen CA-Installation bei Bedarf neu starten.

## Diagnose auf allen Plattformen

- Dashboard: **Systemprüfung** öffnen und „Erneut prüfen“ wählen.
- CLI: `./wsc check` oder `./wsc check --json`.
- Start ohne Browser: `./start.sh --no-open`.
- Alternativer Port: `./start.sh --port 9199`.

Ein Update startet nur den eindeutig zu diesem Repository gehörenden Server neu und wartet mit dem Neustart, solange eine Einrichtung läuft. Die neue Oberfläche und der Server müssen dieselbe Versionskennung verwenden.

## Teststand

Linux-Installationen und Browserabläufe wurden lokal mit echten Containern geprüft. Automatische Tests prüfen Betriebssystem-Erkennung, Windows-/WSL-Pfade, CA-Wechsel, sichere Server-Aktualisierung und teilbare Profile. Die CI-Matrix umfasst Linux, macOS und Windows; sie ersetzt keine vollständige Docker-Desktop-/WSL2-Abnahme auf einem echten macOS- oder Windows-Gerät. Nicht ausgeführte Plattformtests werden nicht als bestanden ausgewiesen.
