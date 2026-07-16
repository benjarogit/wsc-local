# wsc-local

Lokaler **WoltLab Suite Core**-Dev-Stack – ein Befehl, ein Login.

```bash
git clone https://github.com/benjarogit/wsc-local.git
cd wsc-local
./setup.sh
```

English: see [README.en.md](README.en.md)

## Was du bekommst

| Dienst | URL | Login |
|--------|-----|-------|
| WoltLab | https://wsc.local | `ADMIN_USER` / Passwort aus Setup |
| phpMyAdmin | http://localhost:8081 | dieselben Zugangsdaten |
| MailHog | http://localhost:8025 | (kein Login) |
| Portainer | https://localhost:9443 | dieselben (nur wenn neu angelegt) |

Portainer startet nur, wenn noch keines läuft – bestehende Instanzen werden **nicht** überschrieben.

## Voraussetzungen

- Docker + Docker Compose
- [mkcert](https://github.com/FiloSottile/mkcert) (Pflicht)
- Hosts: `127.0.0.1 wsc.local`

## Setup-Optionen

```bash
./setup.sh                          # interaktiv
ADMIN_PASSWORD='dein-langes-pw' ./setup.sh --yes
./setup.sh --zip ~/Downloads/woltlab.zip
./setup.sh --zip-url https://example.com/woltlab.zip
./setup.sh --skip-portainer
./setup.sh --en                     # English prompts
```

Konflikt bei Ports/Namen? `NAME_PREFIX=wsc2` setzen (Setup fragt danach) und ggf. Ports in `.env` anpassen.

## Alltag

```bash
./tools.sh          # Menü: Start/Stop/Status/Snapshots/Doctor
./tools.sh start
./tools.sh doctor
./reset.sh          # Stack weg, Snapshots bleiben
./reset.sh --purge-all --yes   # komplett bei 0
```

Desktop: App-Menü → **WSC Local Übersicht** (nach Setup).

## Sicherheit

Nur für lokale Entwicklung. Ein Passwort für Admin + MySQL ist Absicht und in `.env` (nicht committen).

## Lizenz / WoltLab

Auto-Download nutzt das öffentliche [WoltLab Suite Core](https://www.woltlab.com/de/woltlab-suite-download/)-ZIP. Kommerzielle Apps (Forum etc.) separat nachinstallieren.
