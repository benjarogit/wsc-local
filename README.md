<p align="center">
  <img src="panel/logo.png" alt="wsc-local" width="96" height="96">
</p>

<h1 align="center">wsc-local</h1>

<p align="center">
  Lokaler <strong>WoltLab Suite Core</strong>-Dev-Stack<br>
  Ein Setup · ein Login · Steuerung per Terminal oder Browser-Panel
</p>

<p align="center">
  <a href="README.en.md">English</a>
</p>

---

## Schnellstart

```bash
git clone https://github.com/benjarogit/wsc-local.git
cd wsc-local
./setup.sh
```

Danach:

```bash
./start.sh      # Stack starten
./tools.sh      # Terminal-Menü
./panel.sh      # Browser-UI (AdminLTE)
```

---

## Was du bekommst

| Dienst | URL | Login |
|--------|-----|-------|
| **WoltLab** | https://wsc.local | aus Setup |
| **phpMyAdmin** | http://localhost:8081 | dieselben Daten |
| **MailHog** | http://localhost:8025 | — |
| **Panel** | http://127.0.0.1:9099 | lokal (`./panel.sh`) |

- Automatischer Download von WoltLab Suite Core (oder eigenes ZIP)
- TLS mit **mkcert** (`https://wsc.local`)
- Snapshots: Dateien + MySQL-Dump
- **Fremdes Docker bleibt unberührt** – nur Projekt `wsc-local` / dein `NAME_PREFIX`

---

## Voraussetzungen

- Docker + Docker Compose
- [mkcert](https://github.com/FiloSottile/mkcert)
- Hosts-Eintrag: `127.0.0.1 wsc.local` (Setup kann anbieten)

---

## Befehle

| Befehl | Zweck |
|--------|--------|
| `./setup.sh` | Einmalig installieren |
| `./start.sh` | Stack starten |
| `./tools.sh` | Alles steuern (CLI-Menü) |
| `./panel.sh` | Alles steuern (Browser) |
| `./tools.sh create` | Snapshot erstellen |
| `./tools.sh restore` | Snapshot einspielen |
| `./tools.sh doctor` | Gesundheitscheck |
| `./reset.sh` | Stack weg (Snapshots bleiben) |
| `./reset.sh --purge-all` | Komplett bei Null |

### Setup-Optionen

```bash
./setup.sh
ADMIN_PASSWORD='geheim' ./setup.sh --yes
./setup.sh --zip ~/Downloads/woltlab.zip
./setup.sh --zip-url https://example.com/woltlab.zip
./setup.sh --en
```

Konflikt bei Ports/Namen? Anderen `NAME_PREFIX` wählen (Setup fragt danach).

---

## Panel

Optionale Web-Oberfläche mit [AdminLTE](https://github.com/ColorlibHQ/AdminLTE):

- Status der Container
- Start / Stop / Doctor / Rebuild
- Snapshots erstellen, restore, löschen
- Links & Login

Nur auf **127.0.0.1** – kein Netzwerk-Zugriff von außen.

---

## Sicherheit

Nur für **lokale Entwicklung**. `.env` und `var/credentials.txt` nicht committen.

---

## WoltLab

Auto-Download nutzt das öffentliche [WoltLab Suite Core](https://www.woltlab.com/de/woltlab-suite-download/)-ZIP. Kommerzielle Apps (Forum usw.) separat nachinstallieren.
