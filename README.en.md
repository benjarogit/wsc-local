<p align="center">
  <img src="panel/logo.png" alt="wsc-local" width="96" height="96">
</p>

<h1 align="center">wsc-local</h1>

<p align="center">
  Local <strong>WoltLab Suite Core</strong> development stack<br>
  One setup · one login · control via CLI or browser panel
</p>

<p align="center">
  <a href="README.md">Deutsch</a> (default)
</p>

---

## Quick start

```bash
git clone https://github.com/benjarogit/wsc-local.git
cd wsc-local
./setup.sh --en
```

Then:

```bash
./start.sh      # start stack
./tools.sh      # terminal menu
./panel.sh      # browser UI (AdminLTE)
```

---

## What you get

| Service | URL | Login |
|---------|-----|-------|
| **WoltLab** | https://wsc.local | from setup |
| **phpMyAdmin** | http://localhost:8081 | same credentials |
| **MailHog** | http://localhost:8025 | — |
| **Panel** | http://127.0.0.1:9099 | local (`./panel.sh`) |

- Auto-download of WoltLab Suite Core (or your own ZIP)
- TLS via **mkcert** (`https://wsc.local`)
- Snapshots: files + MySQL dump
- **Never touches foreign Docker** – only project `wsc-local` / your `NAME_PREFIX`

---

## Requirements

- Docker + Docker Compose
- [mkcert](https://github.com/FiloSottile/mkcert)
- Hosts: `127.0.0.1 wsc.local`

---

## Commands

| Command | Purpose |
|---------|---------|
| `./setup.sh` | One-time install |
| `./start.sh` | Start stack |
| `./tools.sh` | Full control (CLI) |
| `./panel.sh` | Full control (browser) |
| `./tools.sh create` | Create snapshot |
| `./tools.sh restore` | Restore snapshot |
| `./tools.sh doctor` | Health check |
| `./reset.sh` | Tear down (keep snapshots) |
| `./reset.sh --purge-all` | Full wipe |

```bash
ADMIN_PASSWORD='secret' ./setup.sh --yes --en
./setup.sh --zip ~/Downloads/woltlab.zip
```

---

## Panel

Optional web UI powered by [AdminLTE](https://github.com/ColorlibHQ/AdminLTE): status, start/stop, doctor, snapshots. Bound to **127.0.0.1** only.

---

## Security

Local development only. Do not commit `.env` or `var/credentials.txt`.
