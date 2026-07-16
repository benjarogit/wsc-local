<p align="center">
  <img src="panel/logo.png" alt="wsc-local" width="96" height="96">
</p>

<h1 align="center">wsc-local</h1>

<p align="center">
  WoltLab Suite Core <strong>lokal</strong> zum Ausprobieren und Entwickeln<br>
  Einmal einrichten · ein Login · alles im Browser steuern
</p>

<p align="center">
  <a href="README.en.md">English</a>
</p>

<p align="center">
  <img src="docs/panel.png" alt="wsc-local Steuerung" width="720">
</p>

---

## So geht’s

### Einmalig

Du brauchst [Docker](https://docs.docker.com/get-docker/) und [mkcert](https://github.com/FiloSottile/mkcert).

```bash
git clone https://github.com/benjarogit/wsc-local.git
cd wsc-local
./setup.sh
```

Das Setup lädt WoltLab, richtet `https://wsc.local` ein und fragt dich nach Benutzer & Passwort.

### Danach

| | |
|--|--|
| **Einfachster Weg** | Im Anwendungsmenü **„wsc-local“** öffnen |
| **Oder im Terminal** | `./start.sh` – startet alles und öffnet die Steuerung |

Fertig. Das Terminal kannst du schließen – weiter geht’s im **Browser**.

---

## Deine Adressen

| | |
|--|--|
| **WoltLab** | https://wsc.local |
| **Steuerung** | http://127.0.0.1:9099 |
| **Datenbank** | http://localhost:8081 |
| **Test-E-Mails** | http://localhost:8025 |

Login siehst du nach dem Setup und jederzeit in der Steuerung (kopieren per Klick).

---

## Was die Steuerung kann

- Status auf einen Blick (läuft / Hinweis / Problem)
- Starten, stoppen, Website öffnen
- Sicherungen anlegen und wiederherstellen
- Deutsch / Englisch umschalten

Andere Programme und Docker-Projekte auf dem Rechner bleiben unberührt.

---

## Neu von vorne

```bash
./reset.sh              # Umgebung entfernen (Sicherungen behalten)
./reset.sh --purge-all  # wirklich alles weg
./setup.sh              # erneut einrichten
```
