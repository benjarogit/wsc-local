# wsc-local

Lokaler WoltLab-Suite-Dev-Stack mit Apache, MySQL, phpMyAdmin, MailHog, HTTPS (`wsc.local`) und Snapshots.

Ziel: schnell und reproduzierbar entwickeln – inkl. Plugin-Tests – ohne Production-Anspruch.

## Voraussetzungen

- Docker + Docker Compose
- [mkcert](https://github.com/FiloSottile/mkcert) (für lokale HTTPS-Zerts)
- Hosts-Eintrag: `127.0.0.1 wsc.local`

## Schnellstart

```bash
git clone https://github.com/benjarogit/wsc-local.git
cd wsc-local
cp .env.example .env
./scripts/generate-certs.sh

# WoltLab-Dateien nach ./woltlab legen
# (Download/Installer von WoltLab, oder bestehendes Projekt)

./tools.sh start
# oder interaktiv: ./tools.sh
```

Dann:

| Dienst | URL |
|--------|-----|
| WoltLab | https://wsc.local |
| HTTP-Fallback | http://localhost:8080 |
| phpMyAdmin | http://localhost:8081 |
| MailHog UI | http://localhost:8025 |

**Datenbank beim Installer**

| Feld | Wert |
|------|------|
| Host | `database` (nicht `localhost`) |
| DB | `woltlab` (siehe `.env`) |
| User / Pass | aus `.env` |

SMTP in der Suite: Host `mailhog`, Port `1025`.

## tools.sh

```text
./tools.sh          # Menü
./tools.sh start
./tools.sh stop
./tools.sh status
./tools.sh rebuild  # nach Dockerfile-Änderungen
./tools.sh doctor   # PHP-Extensions, Erreichbarkeit, …
./tools.sh create   # Snapshot (Dateien + DB)
./tools.sh restore
./tools.sh list
```

Nach der ersten erfolgreichen Installation: Snapshot erstellen. Bei Problemen wiederherstellen statt neu zu installieren.

## PHP-Erweiterungen

Entspricht den [WoltLab-Anforderungen](https://www.woltlab.com/):

`ctype`, `dom`, `exif`, `fileinfo`, `gmp`, `intl`, `libxml`, `mbstring`, `openssl`, `pdo`, `pdo_mysql`, `zlib`, plus **gd und imagick** (beide mit WebP).

Check: `./tools.sh doctor`

## MySQL vs. MariaDB

Für WoltLab lokal egal. Dieses Setup nutzt **MySQL 8** – stabil und ausreichend. Ein Wechsel zu MariaDB bringt keinen spürbaren Vorteil und riskiert Volume-Migration.

Redis/Dragonfly sind für lokale Dev-Instanzen meist überflüssig und nicht enthalten.

## Struktur

```text
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── tools.sh
├── config/          # php.ini, Apache HTTPS vHost
├── certs/           # lokal generiert (nicht im Repo)
├── scripts/
├── snapshots/       # lokal (nicht im Repo)
└── woltlab/         # Suite-Dateien (nicht im Repo)
```

## Hinweise

- Aufruf idealerweise über **https://wsc.local** (Port 443) – Hostname/Cookies stimmen sonst oft nicht.
- `woltlab/`, `snapshots/` und Zertifikate sind absichtlich **nicht** im Git-Repo.
- Nur für lokale Entwicklung gedacht.
