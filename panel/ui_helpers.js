// Shared dialogs and local Font Awesome Free icons. SVG attribution: /icons-license.txt.
(() => {
  const {t, html:H} = window.WorkbenchLocale;
  const icon = (name) => H`<svg class="fa-icon" aria-hidden="true" focusable="false"><use href="/icons.svg#${name}"></use></svg>`;
  const dialog = document.getElementById('action-dialog');
  const form = document.getElementById('action-form');
  let pending = null;
  let returnFocus = null;
  function finish(value) {
    const resolve = pending; pending = null;
    dialog.close();
    if (returnFocus?.isConnected) returnFocus.focus({preventScroll:true});
    resolve?.(value);
  }
  function ask({title, description='', body='', confirm=t('Weiter'), cancel=t('Abbrechen'), input=null, danger=false}) {
    if (pending) return Promise.resolve(null);
    returnFocus = document.activeElement;
    document.getElementById('action-heading').textContent = title;
    document.getElementById('action-description').textContent = description;
    document.getElementById('action-content').innerHTML = body;
    const field = document.getElementById('action-input');
    document.getElementById('action-input-wrap').hidden = !input;
    document.getElementById('action-input-label').textContent = input?.label || '';
    field.value = input?.value || ''; field.required = !!input; field.type = input?.type || 'text';
    field.placeholder = ''; field.autocomplete = 'off';
    const error = document.getElementById('action-input-error');error.hidden = true;
    const accept = document.getElementById('action-accept');accept.textContent = confirm;
    accept.className = H`button ${danger ? 'danger' : 'primary'}`;
    const back = document.getElementById('action-cancel');back.textContent = cancel;back.hidden = !cancel;
    form.onsubmit = (event) => {
      event.preventDefault();
      if(input?.expected && field.value !== input.expected){error.textContent=t('Bitte den Projektnamen genau wie angegeben eingeben.');error.hidden=false;field.setAttribute('aria-invalid','true');field.focus();return;}
      if(input?.pattern && !input.pattern.test(field.value.trim())){error.textContent=input.error || t('Bitte die Eingabe prüfen.');error.hidden=false;field.setAttribute('aria-invalid','true');field.focus();return;}
      finish({value: field.value.trim()});
    };
    field.removeAttribute('aria-invalid');
    dialog.showModal();
    (input ? field : danger ? back : accept).focus();
    return new Promise((resolve) => {pending = resolve;});
  }
  dialog.addEventListener('cancel', (event) => {event.preventDefault();finish(null);});
  dialog.querySelectorAll('[data-action-dialog-close]').forEach(button=>button.addEventListener('click',()=>finish(null)));
  document.getElementById('action-cancel').addEventListener('click',()=>finish(null));
  const topics = {
    credentials: {title:t('Deine Zugangsdaten'),description:t('Der Adminzugang meldet dich in WoltLab an. Die Datenbankdaten verbinden WoltLab mit seiner Datenbank und sind kein Website-Login.'),body:H('<p>Vor der Einrichtung kannst du Adminname, E-Mail und Passwort ändern. Danach änderst du den Zugang direkt in WoltLab. Geheimnisse bleiben auf deinem Gerät; teilbare Projektprofile enthalten keine Passwörter.</p>')},
    backups: {title:t('Sicherung oder Server-Export?'),description:t('Eine Sicherung stellt denselben lokalen Projektstand wieder her. Ein Server-Export ist das Paket für einen Umzug auf einen anderen Server.'),body:H('<p>Beide enthalten zusammengehörige Dateien und einen Datenbank-Dump. Das Projekt pausiert kurz. Im Export ersetzt die Workbench lokale Datenbankzugänge durch Platzhalter. Am Zielserver trägst du neue Datenbankdaten ein.</p><p>Beim Wiederherstellen wird vorher der aktuelle Stand gesichert. Einen Export mit Anleitung findest du anschließend zum Herunterladen in diesem Bereich.</p>')},
    profile: {title:t('Teilbares Projektprofil'),description:t('Das Profil beschreibt Suite-Version, PHP, Webserver und Datenbank.'),body:H('<p>Es enthält weder Website-Dateien noch Datenbankinhalte oder Passwörter. Ein neues Projekt aus diesem Profil erhält eigene Ports und Geheimnisse. Für vollständige Daten verwendest du Sicherung oder Export.</p>')},
    services: {title:t('Dienste deines Projekts'),description:t('Webserver und PHP liefern die Website aus; die Datenbank speichert Benutzer und Inhalte.'),body:H('<p>Start und Stopp oben steuern das Projekt. Mailpit ist ein optionales lokales Testpostfach. Für Test-E-Mails in WoltLab: SMTP-Server <code>mail</code>, Port <code>1025</code>, ohne Anmeldung. Dienstprotokolle findest du unter „Logs“.</p>')},
    versions: {title:t('WoltLab-Version und Installationsquelle'),description:t('Das Standardprofil lädt den freien WoltLab Core. Für andere Anwendungen oder ältere Versionen brauchst du ein passendes eigenes Installations-ZIP.'),body:H('<p>PHP und Datenbank müssen zur Suite passen. Alpha- und Legacy-Profile benötigen eine bewusste Bestätigung. Lizenzpflichtige WoltLab-Anwendungen setzt du mit deinem eigenen Archiv und einer passenden Lizenz ein.</p>')},
    recovery: {title:t('Recovery: verlorenen Adminzugang wiederherstellen'),description:t('Die Workbench sichert das Projekt und legt das offizielle WoltLab-Hilfsskript vorübergehend ab.'),body:H('<p>Öffne danach den angezeigten Recovery-Link und folge dem offiziellen Werkzeug. Das offizielle Werkzeug verlangt eine zusätzliche Authentifizierungsdatei im Projektordner. Entferne anschließend beide Dateien mit „Recovery entfernen“. Die Workbench führt keine eigene Passwortänderung aus.</p><p><a href="https://manual.woltlab.com/de/recovery-tool/" target="_blank" rel="noopener">Offizielle Recovery-Anleitung ↗</a></p>')}
  };
  const guides = {
    guide_domain: {title:t('Domainänderung vorbereiten'),description:t('Die Workbench erstellt eine Sicherung und zeigt die Anleitung. Die Domain wird dabei noch nicht geändert.'),steps:[t('Die neue Domain muss auf die Zielumgebung zeigen und ein gültiges TLS-Zertifikat besitzen.'),t('Öffne WoltLab über die neue Domain und melde dich in der Administration an.'),t('Übernimm dort die erkannte Domainänderung und prüfe Links sowie Anmeldung.')],source:'https://manual.woltlab.com/de/customize-directory-structure/'},
    guide_directory: {title:t('Verzeichnisänderung vorbereiten'),description:t('Die Workbench sichert den aktuellen Stand. Dateien und Datenbankpfade änderst du anschließend nach der Anleitung passend zu deinen installierten Apps.'),steps:[t('Lege alte und neue App-Verzeichnisse fest.'),t('Passe Dateien, App-Pfade und Konfiguration in der offiziellen Reihenfolge an.'),t('Leere den WoltLab-Cache und prüfe Website und Administration.')],source:'https://manual.woltlab.com/de/customize-directory-structure/'},
    guide_migration: {title:t('Serverumzug vorbereiten'),description:t('Der Server-Export ist das Umzugspaket. Dieser Assistent erstellt dasselbe Paket und erklärt dir das Einspielen auf dem Zielserver.'),steps:[t('Aktiviere in WoltLab den Wartungsmodus und erstelle hier das Exportpaket.'),t('Lade das Paket herunter. Prüfe PHP, Datenbank und Erweiterungen auf dem Zielserver.'),t('Spiele Dateien und Datenbank ein. Trage neue Datenbankdaten in config.inc.php ein.'),t('Richte Domain und HTTPS ein. Prüfe Anmeldung, Uploads, E-Mails und Hintergrundaufgaben, bevor du den Wartungsmodus beendest.')],source:'https://manual.woltlab.com/de/server-migration/'}
  };
  function guideBody(action) {
    const guide = guides[action];
    return H`<ol class="dialog-steps">${guide.steps.map(step=>H`<li>${step}</li>`).join('')}</ol><p><a href="${guide.source}" target="_blank" rel="noopener">Offizielle WoltLab-Anleitung ↗</a></p>`;
  }
  function info(key) {const topic=topics[key];if(topic)return ask({...topic,confirm:t('Verstanden'),cancel:''});}
  const infoButton = (key,label=t('Weitere Informationen')) => H`<button type="button" class="info-button" data-info="${key}" aria-label="${label}">${icon('circle-info')}</button>`;
  document.body.addEventListener('click',event=>{const button=event.target.closest('[data-info]');if(button)info(button.dataset.info);});
  window.WorkbenchUI={icon,ask,info,infoButton,guides,guideBody};
})();
