# Nutzertests der Workbench – Stand 28.10.2026

Die ersten Nginx-Durchläufe stammen vom 26.10.2026. Am 28.10.2026 wurden die neu geordnete Oberfläche, Nginx und Apache, Sicherungen sowie die neuen Starter geprüft. Geprüft wurde der lokale Arbeitsstand unter Linux mit Docker Compose und einem echten Chromium-Browser. Es wurden tatsächliche WoltLab-Archive installiert; Website und Administration wurden im Browser aufgerufen. Die Testprojekte und deren Daten wurden danach entfernt.

## Erfolgreich geprüft

- Frische Core-Installation von WSC 6.2.8 mit PHP 8.4, Nginx/PHP-FPM und MariaDB.
- Frische WSC-6.3-Installation mit PHP 8.5, Nginx/PHP-FPM und MariaDB, aus dem inoffiziellen Build `6.3-alpha-20261022-1f0a3ecae0`.
- Vollständiger GUI-Ablauf: Projekt vorbereiten, erzeugte Login-Daten sehen, Adminname/E-Mail/Passwort ändern, automatisch einrichten, Website und Administration öffnen.
- Eigenes ZIP über die GUI hochladen. Hierfür wurde das WSC-6.2.8-Core-Archiv verwendet. Bei älteren Profilen fordert das Formular ein eigenes Archiv an.
- Sichtbarer animierter Spinner und Statusanzeige. Ein Neuladen während der Einrichtung verbindet die Anzeige wieder mit demselben Hintergrundvorgang.
- Stylesheets, JavaScript, Bilder und lokale Links mit korrekter Domain und Port. Keine JavaScript- oder Ressourcenfehler in den geprüften Browserabläufen.
- Anmeldung in der Administration mit den gespeicherten Zugangsdaten für WSC 6.2 und WSC 6.3, ohne Rescue Mode und ohne manuelle Installer-Schritte.
- HTTPS mit mkcert. Zusätzlich wurde die WSC-6.3-Seite in einem Browserkontext ohne Ausnahme für Zertifikatsfehler erfolgreich geladen.
- Stoppen und Starten über die GUI, anschließend erneut die Website öffnen.
- Entfernen über die GUI mit Bestätigung des Projektnamens. Danach sind Projektdateien, Datenbankdateien, Container, Netzwerk und lokale Login-Daten entfernt.
- Desktop mit 1440 × 1000 und schmale Ansicht mit 390 × 844 ohne horizontalen Überlauf.
- JavaScript-/Python-Syntax und `git diff --check`.

## Nachprüfung: Apache und aktuelle Oberfläche (28.10.2026)

- WSC 6.2 mit PHP 8.4 und Apache: frische automatische Installation, Website mit HTTP 200, Stylesheets/Skripte und tatsächlicher Admin-Login ohne Browserfehler.
- WSC 6.3 mit PHP 8.5 und Apache: vollständiger Ablauf über die GUI mit eigenem Adminzugang, HTTPS ohne Zertifikatsausnahme, fertiger Website und Admin-Anmeldung.
- Der Button enthält einen expliziten SVG-Spinner. Sichtbarkeit und tatsächlich wechselnde Rotation wurden im Browser geprüft.
- Die Projektkarte wechselt direkt zu „Wird eingerichtet“, klappt die Datenprüfung zu und zeigt denselben Arbeitsschritt wie die Statusleiste. Die drei Phasen Umgebung, WoltLab und Abschlussprüfung bleiben sichtbar.
- Neuladen während der Einrichtung, Stoppen/Starten und Entfernen wurden mit dem Apache-Projekt geprüft. Eine verwaiste Fortschrittsreferenz wird nach einem bestätigten Projekt-Reset aus dem Browser entfernt.
- Eine veraltete Oberfläche ohne passende Versionskennung wird vor einer Änderung mit HTTP 409 abgewiesen. Die Assets tragen die passende Version in der URL.
- Der Launcher wurde beim Wechsel von einem laufenden alten zu einem aktuellen Server geprüft. Pfade mit Leerzeichen werden anhand der echten Prozessargumente verifiziert; laufende Änderungen blockieren einen Server-Neustart.

Drei Apache-Ursachen wurden korrigiert: [OPcache ist ab PHP 8.5 fest eingebaut](https://www.php.net/manual/en/migration85.incompatible.php#migration85.incompatible.opcache) und darf nicht nochmals als Erweiterung gebaut werden; die HTTPS-Freigaberegel muss denselben Token wie der Prüf-Endpunkt nutzen; der Apache-Prozess muss mit dem lokalen Projektbenutzer laufen. Die Benutzer-/Gruppenwerte werden nun direkt exportiert, statt ein bestimmtes Format von `/etc/apache2/envvars` vorauszusetzen. Builds nutzen höchstens vier parallele Compilerprozesse.

## Neue Navigation, Plattformlogik und Sicherungen (28.10.2026)

- Die Hauptnavigation enthält Projekte, Systemprüfung und Hilfe. Pro Projekt ist genau eine Ansicht sichtbar: Übersicht, Zugangsdaten, Dienste, Sicherungen oder Werkzeuge. Tabwechsel per Pfeiltasten, Home und End sowie die zugehörigen ARIA-Zustände wurden im Browser geprüft.
- Vollständiger Ablauf mit WSC 6.2 und Nginx in der neuen Oberfläche: Vorbereitung, direkt sichtbarer Adminzugang, geändertes Passwort, automatische Einrichtung und erfolgreiche Anmeldung. WSC 6.3 wurde mit Apache bis zur tatsächlichen Admin-Anmeldung geprüft; der HTTP-Server meldete Apache. Stoppen, Starten und Entfernen funktionierten über die neue Oberfläche.
- Der Einrichten-Spinner ist sichtbar und seine Rotation ändert sich tatsächlich. Neuladen setzt die Fortschrittsanzeige fort. Die schmale Ansicht mit 390 Pixeln erzeugt keinen horizontalen Seitenüberlauf.
- Der Mailpit-Testdienst wurde über die Dienstübersicht gestartet und gestoppt. Die Dienstansicht bietet getrennte Logs für Webserver, PHP, Datenbank und Mail, soweit im gewählten Profil vorhanden.
- Ein Snapshot wurde über die GUI erstellt, ausgewählt und in dasselbe laufende Projekt zurückgespielt. Danach funktionierten Website und Admin-Anmeldung mit den zuvor geänderten Zugangsdaten.
- Ein Server-Export wurde über die GUI erzeugt und heruntergeladen. Das Archiv enthielt Dateien, Datenbank, Prüfsummen und Importanleitung. In der exportierten `config.inc.php` stehen Platzhalter statt lokaler Datenbankzugangsdaten; lokales Datenbankpasswort, TLS-Schlüssel, `.env` und Browser-Freigabetoken waren nicht enthalten.
- Der Sicherungsablauf nutzt `mariadb-dump` statt des ungültigen Befehls `mariadbdump`. Binärwerte werden mit `--hex-blob` gesichert, damit ein SQL-Dump nicht an der Textdekodierung scheitert.
- Ein teilbares Profil wurde heruntergeladen und auf die erlaubten Stack-Felder geprüft. Ein neues Projekt aus demselben Profil erhält eigene Geheimnisse und reserviert andere Ports. Docker Compose akzeptierte Projektpfade mit Leerzeichen, `#` und `:` über die neue Bind-Mount-Schreibweise.
- `setup.sh`, `start.sh` und `panel.sh` führen jetzt in dieselbe Workbench. Die einmalige Zertifikatsfreigabe erfolgt vor dem Hintergrundstart. Der Linux-Systemcheck und die sichere Aktualisierung eines laufenden Dashboard-Servers wurden ausgeführt.
- Elf lokale Unit-Tests bestanden: Host-Erkennung, WSL2-/Windows-CA-Pfade, CA-Wechsel, Schutz laufender Vorgänge und anderer Workspaces, verständliche fehlende Voraussetzungen, teilbare Profile, Exportbereinigung und vollständige Projekt-Lebenszyklusbefehle inklusive optionaler Dienste. Python-, JavaScript- und Bash-Prüfungen sowie `git diff --check` bestanden.
- Eine Abschlusskontrolle deckte einen übrig gebliebenen gestoppten Mailcontainer auf. Projektweites Stoppen und Entfernen aktivieren nun ausdrücklich alle Compose-Profile. Ein eigener realer Mailpit-Durchlauf bestätigte: Stoppen hält auch den optionalen Dienst an; Entfernen hinterlässt weder Container noch Netzwerk. Der alte Restcontainer wurde ebenfalls entfernt.

Die neuen Windows-Starter und die gemeinsame Hostlogik sind implementiert. Eine CI-Matrix für Linux, macOS und Windows mit Python 3.10/3.13 ist angelegt, wurde hier aber nicht auf GitHub ausgeführt. macOS- und Windows-/WSL2-Docker-/Browser-Abläufe wurden auf diesem Linux-Rechner nicht real ausgeführt.

## Behobene Ursachen

Die gespeicherte WoltLab-Domain verlor den lokalen Port. Dadurch wurden CSS, Skripte, Bilder und Links an eine falsche Adresse geschickt; das ACP wechselte in den Rescue Mode. Die Domain enthält jetzt den Port, die Cookie-Domain enthält nur den Hostnamen.

Die geprüften WSC-6.2/6.3-RequestHandler vergleichen außerdem eine Domain mit Port mit einem Hostnamen ohne Port und erzeugen so eine doppelte Portangabe. Bei der neuen Installation korrigiert die Workbench nur den exakt erkannten Codeblock. Originaldatei, Pfad und Prüfsummen werden dokumentiert. Nach Updates muss diese Kompatibilität erneut geprüft werden; andere Upstream-Versionen werden nicht blind überschrieben.

Das Vorhandensein von `global.php` markiert eine Einrichtung nicht mehr automatisch als erfolgreich. Ein eigener Zustand wird erst nach Prüfung von Website, Ressourcen und tatsächlicher Admin-Anmeldung auf `ready` gesetzt. Statusabfragen löschen während der Einrichtung keine Hilfsdateien mehr.

WSC 6.2 benötigt ebenfalls HTTPS. Die automatische Einrichtung aktiviert es jetzt für die Profile 6.2 und 6.3. Die [offiziellen Systemvoraussetzungen](https://manual.woltlab.com/de/requirements/) nennen eine Domain mit gültigem TLS-Zertifikat.

Die Portvergabe berücksichtigt auch gestoppte Projekte und noch nicht gestartete Maildienste. Nach einer Portkorrektur während des ersten Starts liest der Installer die aktualisierte Projektadresse erneut ein.

## Nachprüfung: Sicherungsantworten und Farbdarstellung (28.10.2026)

Die gemeldeten Projekte `test1` (WSC 6.3, Nginx) und `test2` (WSC 6.2, Apache) besaßen bereits vollständige Sicherungsdateien. Das Serverprotokoll zeigte abgebrochene Browserverbindungen beim Zurücksenden des Ergebnisses (`BrokenPipeError`). Eine vorhandene Sicherung wurde deshalb im Browser als Netzwerkfehler wahrgenommen.

Sicherung, Wiederherstellung und Export verwenden jetzt dieselbe Hintergrundverwaltung wie die automatische Installation. Die Startanfrage liefert sofort eine Vorgangskennung; kurze Statusabfragen liefern Abschluss oder Fehler. Neuladen verbindet sich wieder mit dem gespeicherten Vorgang. Doppelte Anfragen für denselben laufenden Vorgang starten keine zweite Sicherung. Andere Datenänderungen und Server-Neustarts werden währenddessen abgewiesen. Ein Verbindungsabbruch beim Schreiben einer Antwort erzeugt keinen zweiten Fehlerantwort-Versuch.

Tatsächlich geprüft:

- Sicherung beider Projekte über die GUI: Startantwort HTTP 202 nach etwa 60–70 ms, sichtbarer Fortschritt, Neuladen während des Vorgangs, bestätigter Abschluss und auswählbare Sicherungen.
- SHA-256-Prüfungen aller vorhandenen Test-Snapshots für Dateien und Datenbank bestanden.
- Wiederherstellung von `test2` über die GUI; danach Website mit HTTP 200 und tatsächliche Admin-Anmeldung mit dem gespeicherten Zugang.
- Export von `test2` über die GUI, einschließlich geprüfter Datei-/Dump-Prüfsummen und bereinigter Datenbankzugangsdaten.
- Systemdarstellung folgt einem simulierten Wechsel der Betriebssystempräferenz. Hell und Dunkel überschreiben die Systemeinstellung und bleiben nach Neuladen gespeichert. Die schmale dunkle Ansicht mit 390 Pixeln hat keinen horizontalen Überlauf.
- Drei neue HTTP-Regressionstests prüfen unmittelbare Antwort bei noch laufendem Backup, erneutes Verbinden und Wiederverwenden derselben Vorgangskennung, Konfliktschutz und Vorprüfung einer Restore-Auswahl. Zusammen bestehen 14 lokale Unit-Tests.

Die Farbauswahl steht oben rechts. Der gespeicherte Modus wird vor dem Stylesheet angewandt; Dialoge, Eingaben, Statusfarben und Meldungen verwenden dieselben Farbtokens wie die Projektübersicht.

Ein abschließender frischer WSC-6.2-/Nginx-Durchlauf bestätigte auch die automatische Installation mit der gemeinsamen Hintergrundverwaltung einschließlich Neuladen während der Einrichtung. Die README-Screenshots wurden aus diesem Durchlauf neu aufgenommen, zusätzlich mit dunkler Darstellung. `test1`, `test2` und das abschließende Projekt `mein-forum` wurden anschließend über die GUI vollständig entfernt.

## Nachprüfung: Werkzeuge, Dialoge und verlorene Startantwort (28.10.2026)

Die weiterhin gemeldeten Werkzeuge hatten denselben langen synchronen Anfrageweg wie zuvor die Sicherungen. Alle 18 potenziell längeren Projektaktionen verwenden jetzt die Hintergrundverwaltung. Dazu gehören Recovery, Domain-/Verzeichnisanleitung, Umzugsvorbereitung, Dienststeuerung und angewandte Uploadlimits. Der Start liefert HTTP 202; Status und Fehler bleiben getrennt vom Browseraufruf erhalten.

Ein zusätzlicher Test deckte Neuladen unmittelbar vor Empfang der Startantwort auf. Der Browser kennt dann noch keine Vorgangskennung. Die Workbench kann laufende und kürzlich abgeschlossene Vorgänge nun beim Server ermitteln; bereits angezeigte Ergebnisse werden im Browser vermerkt. Dieser Fall wird durch einen simulierten Verbindungsabbruch im Browser-Test dauerhaft geprüft.

Tatsächlich mit Docker und WoltLab unter Linux geprüft:

- Domain- und Verzeichnisanleitung: vollständige Sicherung, erfolgreicher Abschluss, erklärender Dialog und Quellenlink; Domain-/App-Pfade wurden dabei wie vorgesehen nicht verändert.
- Umzugsvorbereitung: Export erstellt, Abschlussdialog mit Download und Schritten für den Zielserver; Paket über den Browser heruntergeladen.
- Recovery unter WSC 6.3: vorhandenes verwaltetes Skript erkannt, entfernt, neu aus der offiziellen Quelle eingerichtet, offizieller Authentifizierungsbildschirm mit HTTP 200 geöffnet und wieder entfernt. Danach lieferte der Browser für die Skriptadresse HTTP 404. Die Kontowiederherstellung selbst wurde nicht ausgeführt.
- Neue Werkzeug-Sicherungen hatten korrekte Datei-/Dump-Prüfsummen. Die temporäre Recovery-Datei war in den neuen Snapshots und im geprüften Umzugspaket nicht enthalten. Auch die offizielle Authentifizierungsdatei ist jetzt aus neuen Sicherungen und Exporten ausgeschlossen.
- Abschließend frische WSC-6.2-Installation mit Apache über die GUI: automatischer Ablauf mit Spinner und Neuladen, HTTP 200 und tatsächlicher Admin-Login. Anschließend vollständiges Entfernen über den neuen Dialog mit Projektnamensbestätigung.
- Lokal mitgelieferte Font-Awesome-Free-Icons an Navigation, Aktionen, Informationsschaltflächen und Farbauswahl. Der Darkmode verwendet das Mondsymbol; die Systemauswahl verwendet das Monitorsymbol.

Automatisierte Abdeckung: 23 Python-Tests einschließlich einer Matrix aller 18 Hintergrundaktionen und neun Chromium-Tests mit isolierten API-Antworten. Die Browserfälle prüfen Bestätigung und Abbrechen, verständliche Ergebnisse, Wiederaufnahme, verlorene Startantwort, Fokus nach Escape, Theme-Auswahl, Löschbestätigung und Upload-Vorschau. CLI-Tests prüfen auch fehlerhafte Recovery-Downloads, veränderte Skripte und die Erkennung/Bereinigung der offiziellen Authentifizierungsdatei. Die Browser-Suite ist im Repository und im CI-Workflow hinterlegt; der GitHub-Lauf wurde hier nicht ausgeführt.

README und Screenshots wurden aktualisiert. `test1` und das abschließende Apache-Projekt `mein-forum` wurden entfernt. Projektliste und lokale Projekt-Zugangsdaten sind leer; keine Workbench-Container oder Workbench-Netzwerke sind übrig.

## Noch nicht abgenommene Abläufe

Dieser Durchlauf bestätigt die beschriebenen lokalen Core-Installationsabläufe sowie Snapshot/Restore im selben Projekt und die Erstellung/Prüfung eines Server-Exports. macOS, Windows/WSL2, Legacy-Installationen, MySQL 8, kostenpflichtige WoltLab-Apps und andere eigene Archive wurden hier nicht durchgehend getestet. Altbestandsimport, Import auf einem anderen Projekt oder Server, Kontowiederherstellung innerhalb des offiziellen Recovery Tools sowie Erhalt eines zuvor laufenden Maildiensts über Snapshot/Restore wurden nicht abgenommen. Das ist keine Freigabe dieser weiteren Abläufe.

## Screenshots

- [Erster Start mit leerer Projektliste](panel.png)
- [Eingerichtetes Projekt](panel-project.png)
- [Einrichtung mit Spinner und tatsächlichem Arbeitsschritt](panel-installing.png)
- [Dunkle Darstellung](panel-dark.png)
- [Erklärender Umzugsdialog](panel-dialog.png)

## Abschlusskontrolle am 28.10.2026

Der letzte vollständige Apache-6.3-GUI-Durchlauf mit der neu geordneten Oberfläche endete erfolgreich. Der Browser bestätigte einen sichtbaren und animierten Spinner, Weiterführung nach Neuladen, HTTP 200, Admin-Login, Tastaturbedienung der Projektansichten, Neustart und Entfernen. Die Anzeige eines bereits abgeschlossenen Vorgangs nach Neuladen wurde zusätzlich als isolierter Frontend-Regressionsfall geprüft.

Die früheren Testprojekte sowie `mein-forum`, `apache-labor` und `cleanup-mail-check` wurden samt lokalen Zugangsdaten entfernt. Nach der gesonderten Mailcontainer-Korrektur sind keine Workbench-Container oder Workbench-Netzwerke übrig. Der laufende Dashboard-Server und die Dateien melden denselben Stand; es läuft kein Einrichtungsvorgang.

## Zustand nach dem Zurücksetzen

Die Workbench-Projektliste ist leer. Alle im Durchlauf angelegten Projekte, ihre Container/Netzwerke und ihre lokalen Zugangsdaten wurden entfernt. Zusätzlich wurden die vier gestoppten Container und das Netzwerk des alten Compose-Projekts `wsc-local` aus diesem Repository entfernt. Dessen altes Webverzeichnis `woltlab/` enthält nur noch `.gitkeep`; die frühere lokale Datenbankablage ist leer. Gemeinsame Docker-Basisimages, geprüfte Download-Caches und die lokale mkcert-CA bleiben verfügbar. Das Dashboard läuft auf `http://127.0.0.1:9099/`.

## Farbauswahl als direkte Icons (28.10.2026)

Das Dropdown und das zusätzliche Info-Symbol der Darstellung wurden durch drei direkt auswählbare Icon-Buttons ersetzt: Monitor für System, Sonne für Hell, Mond für Dunkel. Der aktive Modus ist markiert und per `aria-pressed` erkennbar. Der angepasste Browser-Test prüfte Auswahl, gespeicherte Einstellung nach Neuladen, Systemwechsel und Tastaturbedienung. Die mobile Ansicht mit 390 Pixeln blieb ohne horizontalen Überlauf. Die Screenshots der leeren hellen und dunklen Übersicht sind aktualisiert. Es wurden keine Testprojekte angelegt.

## Release 1.0.0: Sprache, Galerie und Veröffentlichung (28.10.2026)

Deutsch bleibt unabhängig von der Browsersprache der Standard. EN/DE wechselt Navigation, Projektbereiche, Formulare und Dialoge; die Auswahl bleibt gespeichert. Der Sprachwechsel stellt die zuvor geöffnete Projektansicht wieder her. Projektnamen, Benutzereingaben und Zugangsdaten werden nicht übersetzt. Ein Browser-Regressionsfall prüft ausdrücklich deutsche Begriffe und Sonderzeichen als Zugangsdaten in der englischen Oberfläche. Technische CLI-/Dienstprotokolle bleiben Originalausgaben.

Zusätzlich real unter Linux ausgeführt: frische WSC-6.2-Installation über die englische Oberfläche, vollständige automatische Einrichtung und tatsächlicher Admin-Login. Sicherung und Export wurden in der englischen Oberfläche erstellt. Das vorhandene WSC-6.3-Testprojekt und die neue 6.2-Installation dienten den aktuellen Screenshots in beiden Sprachen. Passwörter bleiben auf den Aufnahmen verborgen; E-Mail-Anzeigen sind für die Dokumentation anonymisiert.

Die Galerie enthält Startseite, Vorbereitung, erweiterte Einstellungen, Fortschritt, alle fünf Projektbereiche, Systemprüfung, Hilfe, Umzugsdialog, Dark Mode und mobile Ansichten. Die READMEs verwenden eine große Startansicht und klickbare kleinere Vorschaubilder.

Release-Abdeckung: 24 Python-Tests sowie zehn Chromium-Regressionstests. Der neue Import-Profil-Test prüft die explizite Übernahme des 6.3-Entwicklungsprofils einschließlich PHP-Version. Eine maschinenspezifische Datenbankablage des alten Compose-Stacks wurde durch ein portables Standard-Volume mit optionalem konfigurierbarem Pfad ersetzt.

Nach den Aufnahmen wurden beide Testprojekte über die englischen Bestätigungsdialoge vollständig entfernt. Projektliste, Projektdateien, Datenbank, Container, Netzwerke und lokale Projekt-Zugangsdaten sind kontrolliert leer. Gemeinsame Downloads, Basisimages und die lokale CA bleiben erhalten. Die GitHub-CI-Ergebnisse gehören zur Veröffentlichung; native vollständige macOS-/Windows-Docker-Abnahmen bleiben gesondert.

Die erste GitHub-Matrix fand einen zu strengen Testvergleich für aufgelöste Temp-Pfade (macOS `/private/var`, Windows-Langpfad) und einen Überlauf in der schmalen Navigation beim CI-Browser. Der Test erwartet nun den kanonischen Importpfad; die Navigation darf ihre Elemente passend verkleinern und umbrechen. Der Viewport-Test wartet auf das fertige responsive Layout. Die zehn Browserfälle wurden anschließend auch lokal mit genau der von Playwright installierten Chromium-Version ausgeführt.


## ACP-Direktlogin und geführte Host-Einrichtung (28.10.2026)

- Echte neue Projekte: WSC 6.2/Nginx/PHP 8.4 und WSC 6.3/Apache/PHP 8.5. „ACP öffnen“ meldete den Browser direkt an; eine geschützte ACP-Einstellungsseite war danach ohne erneute Anmeldung erreichbar. Die verbrauchte Übergabedatei liefert bei erneutem Aufruf HTTP 404.
- Einmal-Übergaben verwenden POST, einen gehashten Token, ein lokales Ziel und maximal 60 Sekunden Gültigkeit. Normale Admin-Anmeldung statt Passwortänderung oder Datenbank-Umgehung. Die echte Sicherung und der echte Server-Export enthielten keine temporären Anmeldeskripte.
- Ein weiterer automatischer WSC-6.2-Installationslauf blieb beim Sprachwechsel DE → EN mit Neuladen verbunden und wurde vollständig abgeschlossen. Screenshots entstanden aus echten Projekten; Admin-/Datenbankpasswörter blieben verborgen.
- Browser-Regressionstests prüfen zusätzlich den Sprachschalter mit Globus-Icon, die Einmal-Übergabe im neuen Tab, den verständlichen Rückfall bei abgelehnten Zugangsdaten und die bestätigungspflichtige Terminaleinrichtung. Die Voraussetzungseinrichtung wird dabei isoliert simuliert; auf dem Entwicklungsrechner werden keine installierten Systempakete entfernt oder neu installiert.
- GitHubs echtes README-Layout: Galerie und Hero hatten denselben horizontalen Mittelpunkt (564 px bei 1440 px Browserbreite); 12 verlinkte Vorschaubilder in drei Reihen.
- Automatisierte Gesamtprüfung: 35 Python-Tests und 14 Chromium-Tests. Bash-Syntax lokal; PowerShell-Syntax und portable Tests zusätzlich in der Plattform-CI.
- Weiterhin offen: native Paketinstallationen mit sudo/UAC, Neustarts, Homebrew-Ersteinrichtung und Docker-Desktop-/WSL-Integration auf echten macOS-/Windows-Geräten. Erfolgreiche Logik-/Syntaxprüfungen sind keine Bestätigung dieser Systemabläufe.
