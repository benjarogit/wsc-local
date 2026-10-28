# Workbench aktualisieren

Ab **1.2.0** prüft die Workbench veröffentlichte stabile GitHub-Releases und kann sie selbst installieren. Das ist ein Update des Tools; vorhandene WoltLab-Installationen und deren Suite-Version werden dabei nicht aktualisiert.

## Im Dashboard

1. Bei einem neuen Release erscheint ein Hinweis. **Updates** in der Navigation zeigt installierte und veröffentlichte Version, Installationsart und Release-Hinweise. Die automatische Prüfung verwendet einen Cache von sechs Stunden; **Erneut prüfen** fragt GitHub direkt ab.
2. **Update installieren** öffnet die Vorschau. Nach Bestätigung lädt die Workbench das offizielle Release-ZIP, prüft SHA-256 und den enthaltenen Dateikatalog und legt einen Wiederherstellungsstand an.
3. Die Programmdateien werden aktualisiert. Der eigene Dashboard-Prozess startet neu; die Anzeige verbindet sich wieder und bestätigt die tatsächlich laufende Version. Auch nach Neuladen bleibt der Vorgangsstatus erhalten.
4. **Manuelle Anleitung** bleibt als Alternative verfügbar, auch wenn GitHub gerade nicht erreichbar ist. Fehlende Host-Voraussetzungen werden weiterhin über die Systemprüfung eingerichtet.

WoltLab-Websites können weiterlaufen. Falls mehrere Dashboards desselben Programmordners geöffnet wurden, zusätzliche Server zuerst mit `./start.sh --stop --port PORT` beenden; ein Update benötigt genau einen eigenen Dashboard-Prozess oder keinen laufenden Server. Laufende Workbench-Aufträge, etwa Einrichtung, Sicherung oder Änderungen an Zugangsdaten, blockieren ein Update. Während des Updates starten keine neuen Änderungen. Der erste Browser-Aufruf prüft im Hintergrund; ein fehlgeschlagener Versionsabruf blockiert die Projektverwaltung nicht.

## In der CLI

```bash
./wsc update --check       # Nur prüfen, GitHub direkt abfragen
./wsc update               # Vorschau und Rückfrage, danach installieren
./wsc update --yes         # Geprüftes Update ohne Rückfrage installieren
./wsc update --guide       # Lokale manuelle Anleitung, ohne Netzwerkabruf
./wsc update --json        # Update-Plan maschinenlesbar ausgeben
```

Die CLI erkennt den eigenen laufenden Dashboard-Prozess und dessen Port. Sie beendet ihn erst, wenn keine Workbench-Aufträge laufen, und startet ihn anschließend neu. Bei unbekanntem oder fremdem Prozess wird kein Prozess beendet.

## Git und ZIP

**Git-Installation:** Nur ein unveränderter Programmstand kann automatisch aktualisiert werden. Der offizielle Release-Tag wird geholt und der Branch ausschließlich per Fast-forward weitergesetzt. Abweichende eigene Commits, lokale Codeänderungen oder kollidierende Dateien führen zur Anleitung. Es gibt keinen erzwungenen Reset und kein `git clean`.

**ZIP-Installation:** Der Dateikatalog beschreibt die verwalteten Programmdateien. Für ZIPs ab 1.2.0 liegt er als `.wsc-local-release.json` im Download. Ein älterer 1.1.0-Dateistand kann gegen dessen offiziellen Git-Dateikatalog geprüft werden. Geänderte oder fehlende Programmdateien und Kollisionen verhindern das automatische Ersetzen. Unbekannte persönliche Dateien bleiben erhalten.

Lokale `.env`, `var`, `certs`, `snapshots`, `woltlab` sowie separat gespeicherte Projekte und Zugangsdaten werden nicht durch das Release ersetzt. Ein Updatepaket mit Pfadmanipulationen, Verknüpfungen, doppelten Dateinamen, zu großer Entpackgröße oder abweichenden Prüfsummen wird abgewiesen. Der Download stammt fest aus dem offiziellen Repository; eine beliebige Update-URL kann nicht eingegeben werden.

## Fehler und Wiederherstellung

Vor dem Austausch speichert `var/update-state.json` den Wiederherstellungsstand. Bei einem Git-Update bleibt der vorherige Commit erreichbar; bei einem ZIP-Update werden die bisherigen Programmdateien unter `var/update-backups/` gesichert. Scheitert der Dateiaustausch, wird zurückgesetzt. Scheitert der Start der neuen Version, wird der bisherige Programmstand wiederhergestellt und dessen Dashboard erneut gestartet. Erfolg wird erst gemeldet, wenn die erwartete Version antwortet.

Der Wiederherstellungshelfer liegt außerhalb der auszutauschenden Programmdateien. Falls das Programm nach einem abgebrochenen Prozess oder Stromausfall nicht startet, im bisherigen Programmordner ausführen:

```bash
python3 var/update-recovery.py --rollback .
./start.sh
```

Unter Windows diese Befehle in WSL2 ausführen. Der Helfer verweigert eine Wiederherstellung, wenn der Update-Prozess noch läuft. Zwischenzeitlich geänderte Programmdateien werden nicht blind durch eine Sicherung ersetzt. Details stehen in `var/update-restart.log`; bei einem Konflikt den bisherigen Ordner und die Sicherung behalten und die Änderungen manuell abgleichen. Wiederherstellungsstände werden nicht automatisch gelöscht.

## Erster Umstieg von 1.1.0 oder älter

Die alten Versionen haben die Update-Oberfläche noch nicht. Diesen ersten Umstieg einmal manuell durchführen:

- Git: laufende Aufträge abschließen, `git pull --ff-only`, dann `./start.sh`.
- ZIP: bisherigen Programmordner als Sicherung kopieren. Das neue Release-ZIP separat entpacken und nur dessen Programmdateien in den bisherigen Ordner übernehmen. Persönliche `.env`-, `var`-, `certs`-, `snapshots`- und `woltlab`-Daten erhalten; Verzeichnisse zusammenführen statt ersetzen. Danach `./start.sh` bzw. `Start-wsc-local.cmd` verwenden.

Die automatische Updatefunktion ist anschließend für kommende Releases verfügbar. Die nummerierte ZIP-Datei ist der empfohlene Download; die von GitHub zusätzlich erzeugten „Source code“-Archive enthalten keinen generierten Installations-Dateikatalog und benötigen bei einer Erstinstallation gegebenenfalls dessen Prüfung über GitHub.

## Automatische GitHub-Releases

Ein neuer stabiler Tag wie `v1.2.0` startet `.github/workflows/release.yml`. Der Workflow löst den Tag zuerst auf einen festen Commit auf und führt die Plattform- und Browserprüfungen für genau diesen Commit aus. Erst nach erfolgreicher Prüfung werden Versionsnummer und Changelog abgeglichen, ZIP, Dateikatalog und SHA-256-Datei gebaut, als Entwurf hochgeladen und veröffentlicht. Bereits veröffentlichte Releases werden bei einem erneuten Lauf nicht überschrieben. Ein älterer nachträglicher Tag verdrängt keine neuere Version als „Latest“.

Für Maintainer nach Versionsänderung und Commit:

```bash
git push origin main
git tag -a v1.2.0 -m "wsc-local 1.2.0"
git push origin v1.2.0
```

Der Tag muss zur Datei `VERSION` und einem Abschnitt im `CHANGELOG.md` passen. Nach einem fehlgeschlagenen Workflow kann die Veröffentlichung über den manuellen Workflow-Start mit demselben Tag wiederholt werden. Ein neuer Versions-Tag bleibt eine bewusste Versionsentscheidung; Paketbau und Veröffentlichung übernimmt GitHub.

## English

From **1.2.0**, **Updates** checks stable GitHub releases, offers an installation preview and installs the verified release after confirmation. The application creates a recovery point, restarts its own dashboard and verifies the running version. Running WoltLab sites and their data are preserved. This updates the Workbench application, not the WoltLab Suite itself.

CLI: `./wsc update --check`, `./wsc update`, `./wsc update --yes`, `./wsc update --guide`, or `./wsc update --json`. Manual instructions remain available offline. Checks are cached for six hours; the refresh button and `--check` bypass the cache.

Git updates require clean tracked files and a fast-forward to the official stable tag. ZIP updates verify managed files against the installation manifest or the official previous release tree. Changed files, collisions and ongoing Workbench operations block installation. Private `.env`, runtime directories, projects and credentials are preserved. If replacement or dashboard startup fails, the previous program is restored; the UI waits for the restored dashboard to respond before confirming recovery.

For an interrupted process, run `python3 var/update-recovery.py --rollback .` and then `./start.sh` in the original application directory (inside WSL2 on Windows). Keep backups and inspect `var/update-restart.log` if manual reconciliation is required. The recovery helper refuses to overwrite intervening source edits or interrupt a still-running updater.

Users on 1.1.0 or earlier perform the first upgrade manually through Git, or by merging new application files from the release ZIP into the existing directory while preserving personal data. Thereafter, the new update interface is available for future releases.

Stable `vMAJOR.MINOR.PATCH` tags trigger GitHub release automation. The exact tagged commit is tested first; matching VERSION and changelog, a source ZIP with a file manifest, and SHA-256 checksums are required before publication. Published releases are never silently overwritten.
