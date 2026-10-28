# Screenshots der WoltLab Workbench

Stand: 28.10.2026, Produktstand **1.2.0** (Workbench-Updates und Release-Automation). Die README-Dateien verwenden einen großen Startseiten-Screenshot und eine mittig angeordnete Galerie mit 20 anklickbaren Vorschaubildern. Die Originale liegen in voller Auflösung vor; die mobile Vorschau wird über ihre Höhe begrenzt, damit sie die Galerie nicht auseinanderzieht.

Alle Aufnahmen gibt es als `*-de.png` und `*-en.png`. Deutsch und Englisch wurden in getrennten Browserkontexten gewählt. Die Projektdateien stammen aus echten lokalen WoltLab-Installationen: WSC 6.2 mit Nginx/PHP-FPM auf Deutsch und WSC 6.3 mit Apache auf Englisch. WSC 6.3 ist weiterhin ein inoffizieller Entwicklungsbuild.

## Bildinhalte

- `updates`, `update-confirm`, `update-guide`, `update-progress`: Beispielfluss von 1.2.0 auf 1.2.1. Die Versionsmetadaten stammen aus einem lokalen Testpaket; 1.2.1 wurde nicht öffentlich veröffentlicht. Dateiprüfung, Programmaustausch, Dashboard-Neustart und Browser-Wiederverbindung wurden tatsächlich in einem isolierten Programmordner ausgeführt.
- `home`: erster Start ohne Projekte mit dem geführten Einstieg, wie ihn neue Nutzer sehen (1920 × 916, Systemdarstellung bei hellem Gerätemodus). Bereits eingerichtete Projekte und „ACP öffnen“ sind in den Verwaltungsaufnahmen zu sehen.
- `create`, `advanced`: Projektassistent und optionale Einstellungen.
- `setup-language`: Zugangsdaten vor der Einrichtung und Hinweis auf die Dashboard-Sprache. Passwörter bleiben verborgen.
- `installing`: echte laufende automatische Einrichtung mit Spinner und Fortschritt, jeweils in der gewählten Sprache.
- `overview`, `credentials`, `services`, `backups`, `tools`: die fünf Verwaltungsbereiche. Sicherungen und Exportdateien wurden tatsächlich erstellt.
- `system`, `help`: Systemprüfung und Einstiegshilfe.
- `migration`: Erklärung des Serverumzugs vor einer Aktion.
- `acp`: über „ACP öffnen“ direkt angemeldete WoltLab-Administration in der Installationssprache; kein Login-Formular und keine Passwörter im Bild.
- `prerequisites`: **Beispielfall** des Voraussetzungen-Dialogs. Ausschließlich das Systemprüfungs-Ergebnis für die HTTPS-Freigabe wurde im isolierten Browser als fehlend dargestellt. Die Vorschau und ihre Texte stammen aus der tatsächlichen Oberfläche. Der Terminalbefehl ist für die Dokumentation auf den Repository-Aufruf verkürzt. Abbrechen schließt den Dialog; es werden keine Systempakete installiert und keine Zertifikate entfernt.
- `dark`, `mobile`: Dark Mode und schmale Ansicht mit 390 × 844 Pixeln.

## Aufnahme und Prüfung

1. Die Workbench mit aktuellem Server und aktuellen Assets starten. Für Browseraufnahmen werden die vorhandenen Playwright-Entwicklungswerkzeuge genutzt; sie gehören nicht zu den Laufzeitvoraussetzungen der Workbench.
2. Ausschließlich entbehrliche Dokumentationsprojekte vorbereiten. Vor der Einrichtung DE bzw. EN wählen und den Bereich mit den erzeugten Zugangsdaten und weiterhin verdeckten Passwörtern aufnehmen.
3. Automatisch einrichten und den tatsächlichen Fortschritt aufnehmen. Suite-Standard und Adminsprache müssen zur gewählten Sprache passen. Danach Website und direkte ACP-Anmeldung prüfen.
4. Verwaltungsbereiche mit echtem Projektzustand, echter Sicherung und echtem Export aufnehmen. Dialoge vor der Bestätigung fotografieren; keine Passwörter einblenden oder Browser-Adressleisten mit Tokens aufnehmen.
5. Deutsche und englische Bilddateien sowie den aktuellen Dark Mode und die mobile Ansicht kontrollieren. Galerie mit GitHubs Markdown-Renderer prüfen: gleiche Mitte wie das Hauptbild, kleine verlinkte Vorschauen und keine fehlenden Dateien.
6. Dokumentationsprojekte samt Dateien, Datenbanken, Zugangsdaten, Containern und Netzwerken entfernen. Die leere Projektliste zusätzlich kontrollieren. Gemeinsame Download-Caches und die lokale CA bleiben bestehen.

Die älteren Dateinamen `docs/panel*.png` bleiben als Links für bestehende Dokumentation erhalten und werden mit passenden aktuellen Aufnahmen abgeglichen; `docs/panel.png` zeigt den leeren Einstieg.

## English

Captured on 28 October 2026 against version 1.2.0, including Workbench updates and release automation. Each image has a German and an English version. Real disposable projects are used for setup, progress, management, backups, exports and direct ACP login. Passwords stay masked. Only the prerequisite preview uses an explicitly simulated missing HTTPS-approval result; the installer is cancelled and no host packages are changed. Demo projects are removed after capture. README thumbnails link to full-resolution images, and the mobile thumbnail height is limited to keep the centered gallery compact.

Update screenshots use a local 1.2.0 → 1.2.1 example, not a public 1.2.1 release. File replacement, recovery metadata, dashboard restart and browser reconnection are real; only release metadata and download bytes are supplied by the isolated test fixture.
