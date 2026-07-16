# wsc-local

Local **WoltLab Suite Core** dev stack – one command, one login.

```bash
git clone https://github.com/benjarogit/wsc-local.git
cd wsc-local
./setup.sh --en
```

German (default): see [README.md](README.md)

## What you get

| Service | URL | Login |
|---------|-----|-------|
| WoltLab | https://wsc.local | `ADMIN_USER` / password from setup |
| phpMyAdmin | http://localhost:8081 | same credentials |
| MailHog | http://localhost:8025 | (no login) |
| Portainer | https://localhost:9443 | same (only if newly created) |

Portainer starts only if none is running – existing instances are **not** overwritten.

## Requirements

- Docker + Docker Compose
- [mkcert](https://github.com/FiloSottile/mkcert) (required)
- Hosts: `127.0.0.1 wsc.local`

## Setup options

```bash
./setup.sh --en
ADMIN_PASSWORD='your-long-password' ./setup.sh --yes --en
./setup.sh --zip ~/Downloads/woltlab.zip
./setup.sh --zip-url https://example.com/woltlab.zip
./setup.sh --skip-portainer
```

Port/name conflict? Set `NAME_PREFIX=wsc2` and adjust ports in `.env`.

## Daily use

```bash
./tools.sh
./reset.sh
./reset.sh --purge-all --yes
```

## Security

Local development only. One shared password for admin + MySQL is intentional; keep `.env` out of git.
