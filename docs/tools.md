# Werkzeuge verständlich erklärt

Alle Projektwerkzeuge liegen unter **Verwalten → Werkzeuge**. Bestätigungen und Eingaben öffnen einen Dialog mit Wirkung, nächsten Schritten und gegebenenfalls einer Änderungsvorschau. Das Informationssymbol erklärt Begriffe, ohne einen Vorgang zu starten. Escape oder Abbrechen schließen einen Dialog; bereits gestartete Hintergrundvorgänge laufen weiter und verbinden sich nach Neuladen wieder mit der Oberfläche.

## Installierte Pakete und Styles

Direkt an der Projektkarte steht, welcher Stil Standard ist und welche Stile aktiv sind. **Pakete und Styles** öffnet die vollständige Liste in einem Dialog. Die Workbench liest sie aus der laufenden Datenbank: Name, Kennung, Version, Autor, bei Paketen die Art (Anwendung oder Paket) und bei Styles, ob der Stil Standard, aktiv oder deaktiviert ist. Die Liste ändert nichts. Ein gestopptes Projekt wird dafür nicht gestartet.

Dieselbe Liste gibt die Kommandozeile aus:

```bash
./wsc installed mein-forum
./wsc installed mein-forum --json
```

Eigene Dateien unter **Werkzeuge → Eigener Code** sind davon getrennt. Sie erscheinen in der Liste erst, wenn sie in WoltLab installiert sind.

## Recovery

**Recovery einrichten** lädt das offizielle WoltLab-Hilfsskript, prüft die Antwort, erstellt eine Sicherung und legt die Datei vorübergehend im installierten Projekt ab. Nach Abschluss öffnet sich ein Dialog mit dem Recovery-Link und der offiziellen Anleitung. Solange die Datei vorhanden ist, zeigt die Workbench „Recovery ist aktiv“ und bietet das Entfernen an. Ein zweites Einrichten wird verhindert.

Die Wiederherstellung des Kontozugangs erfolgt im offiziellen Werkzeug. Dieses bietet eine zusätzliche Datei `wsc-recovery-auth.php` zum Download an. Speichere sie unverändert im Projektordner, den der Abschlussdialog nennt, und bestätige anschließend die Authentifizierung im Werkzeug.

**Recovery entfernen** löscht die verwaltete Skriptdatei, deren Prüfsumme noch dem Installationsnachweis entspricht, und eine vorhandene Authentifizierungsdatei im exakt erkannten offiziellen Format. Veränderte oder unbekannte Dateien werden zur Prüfung erhalten. Beide temporären Dateien werden weder in neue Snapshots noch in Exporte aufgenommen.

Quelle: [WoltLab Recovery Tool](https://manual.woltlab.com/de/recovery-tool/).

## Domain und Verzeichnisse

**Domain: Anleitung** und **Verzeichnisse: Anleitung** erstellen eine Sicherung und zeigen die passenden nächsten Schritte. Diese Schaltflächen ändern noch keine Domain und verschieben keine App-Dateien. Das steht bereits im Bestätigungsdialog.

Für eine neue Domain müssen Zieladresse und HTTPS erreichbar sein. Danach erfolgt die Übernahme über die WoltLab-Administration. Bei Verzeichnisänderungen hängen Dateien, App-Pfade und Konfiguration zusammen; die genaue Reihenfolge richtet sich nach der installierten App-Struktur.

Quelle: [WoltLab: Domain und Verzeichnisstruktur ändern](https://manual.woltlab.com/de/customize-directory-structure/).

## Sicherung, Export und Serverumzug

- **Sicherung erstellen** hält einen lokalen Stand aus Dateien und Datenbank für die Wiederherstellung desselben Projekts fest.
- **Server-Export erstellen** erzeugt ein herunterladbares Paket aus Dateien, Datenbank-Dump, Prüfsummen, Projektkonfiguration und `IMPORT.md`. Lokale Datenbankzugangsdaten in `config.inc.php` werden durch Platzhalter ersetzt.
- **Serverumzug vorbereiten** erklärt den vollständigen Umzugsablauf und erstellt dasselbe Exportpaket. Es ist der geführte Zugang zum Export, kein zweites Dateiformat. Im Abschlussdialog ist der Download direkt erreichbar; zusätzlich bleibt er unter Sicherungen verfügbar.

Auf dem Zielserver werden Dateien und Datenbank eingespielt und neue Datenbankzugangsdaten, Domain, HTTPS und Dateirechte eingerichtet. Die Workbench führt keinen SSH-Transfer durch und behauptet keinen abgeschlossenen Serverumzug. Das Paket enthält die Anleitung für diese Schritte.

Quellen: [Datensicherung](https://manual.woltlab.com/de/backup/), [Serverumzug](https://manual.woltlab.com/de/server-migration/).

## Eigener Code und GitHub

**Eigener Code** ist ein optionales Git nur für eigene Pakete und Styles. Die laufende Installation, `site/`, die Datenbank, TLS und Zugangsdaten bleiben außerhalb. GitHub ist erst der optionale dritte Schritt und für das lokale Repository nicht nötig.

**Git installieren**, wenn Git fehlt. Git merkt sich Änderungen an den Dateien. Der Dialog nennt den Befehl für das erkannte System (Linux, macOS oder Windows) und verlinkt [git-scm.com/downloads](https://git-scm.com/downloads). Die Workbench installiert Git nicht selbst. Danach die Workbench neu starten.

**GitHub-CLI einrichten**, wenn `gh` fehlt. Die GitHub-CLI öffnet die Anmeldung im Browser. Der Dialog nennt den Befehl für Fedora, Arch und CachyOS. Unter Ubuntu und Debian liegt `gh` nicht im Standard-Archiv; dort gilt die Anleitung auf [cli.github.com](https://cli.github.com/). Die Workbench installiert `gh` nicht selbst. Danach die Workbench neu starten.

**Bei GitHub registrieren** öffnet [github.com/signup](https://github.com/signup). Konto und Passwort legt man dort an.

**Bei GitHub anmelden** öffnet ein Systemterminal. Der Browser zeigt die GitHub-Seite. Dort werden die GitHub-Zugangsdaten eingegeben oder der Einmalcode bestätigt. Das Dashboard speichert kein Passwort und kein Token. Danach ist die Workbench mit diesem Konto verknüpft. Die Sitzung liegt unter `GH_CONFIG_DIR` in `~/.config/wsc-local/gh` und ersetzt eine andere `gh`-Anmeldung nicht.

**Privates Repository erstellen** legt `wsc-<projekt>` an und setzt nur `origin`. **Push** sendet die Commits erst nach einer weiteren Bestätigung. **Letzte Aktivität** zeigt Commits und Pull Requests nur dieses Repositorys.

## Uploadlimits

Der erste Dialog nimmt eine Größe wie `256M` oder `1G` entgegen. Danach zeigt die Workbench die geplanten PHP- und Webserverwerte. Erst „Änderungen anwenden“ schreibt die Konfiguration und startet betroffene Dienste neu. Abbrechen verwirft die Vorschau.

## Icons und Tests

Die Oberfläche nutzt eine lokal mitgelieferte Auswahl aus **Font Awesome Free 7.3.1**. Es wird kein Icon-CDN angesprochen. Originalquelle, Prüfsummen und Lizenz liegen unter `panel/vendor/fontawesome/`; die Icons stehen unter CC BY 4.0. Die Attribution ist auch unter Hilfe erreichbar.

Automatisierte HTTP-Tests decken alle Hintergrundaktionen und Konflikte ab. CLI-Tests prüfen Vorbedingungen und Recovery-Integrität. Browser-Tests prüfen Dialoge, Abbrechen, Wiederaufnahme, verständliche Ergebnisse, Löschschutz und Upload-Vorschau mit isolierten API-Antworten. Diese UI-Tests benötigen keine WoltLab-Lizenz oder laufende Docker-Instanz und verändern keine echten Projekte:

```bash
npm ci
npx playwright install chromium
npm run test:ui
```

Python-Tests:

```bash
python3 -m unittest discover -s tests -v
```

Die tatsächlich mit Docker und WoltLab ausgeführten Tests stehen im [Testprotokoll](user-test.md). Native macOS-/Windows-Abnahmen und ein echter Remote-Umzug bleiben gesonderte Prüfungen.


## Direkt in die Administration

**ACP öffnen** verwendet den lokal gespeicherten Adminzugang für eine normale WoltLab-Anmeldung. Es werden keine Passwörter zurückgesetzt und keine Zwei-Faktor-Prüfungen umgangen. Die Workbench übergibt die so erhaltenen Sitzungscookies per POST mit einem zufälligen Einmal-Token an die lokale Projektadresse. Das Hilfsskript löscht sich vor der Weiterleitung; die Übergabe ist maximal 60 Sekunden gültig. Passwort und Cookies werden nicht im Aufgabenprotokoll ausgegeben. Temporäre Anmeldeskripte sind von Sicherungen und Exporten ausgeschlossen.

Ein neues Browserfenster muss erlaubt sein. Bei verändertem Adminpasswort, Zwei-Faktor-Anmeldung oder fehlgeschlagener Anmeldung erklärt der Dialog den Fehler und bietet **ACP manuell öffnen** an. Nach einem Neuladen der Workbench klickst du erneut auf **ACP öffnen**, um eine neue Einmal-Übergabe zu erhalten.
