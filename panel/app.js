(() => {
  const {t, html:H} = window.WorkbenchLocale;
  const {icon, ask, infoButton, guides, guideBody} = window.WorkbenchUI;
  const VERSION = document.querySelector('meta[name=panel-version]')?.content || '';
  const TOKEN = document.querySelector('meta[name="panel-token"]')?.content || '';
  const list = document.getElementById('instances');
  const output = document.getElementById('output');
  const count = document.getElementById('project-count');
  const toastArea = document.getElementById('toast-area');
  const operationStatus = document.getElementById('operation-status');
  const operationMessage = document.getElementById('operation-message');
  const resultMessage = document.getElementById('operation-result');
  let lastProjects = '';
  let knownProjects = null;
  let projectDetails = [];
  let operationInProgress = false;
  const spinnerMarkup = '<span class="button-spinner" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="3" opacity=".3"/><path d="M12 3a9 9 0 0 1 9 9" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></svg></span>';

  function beginOperation(button, message, buttonLabel) {
    operationInProgress = true;
    document.getElementById('install-phases').hidden = true;
    resultMessage.hidden = true;
    document.querySelector('#create-form button[type=submit]').disabled = true;
    operationMessage.textContent = message;
    document.getElementById('operation-hint').textContent = /WoltLab.*eingerichtet|Umgebung und HTTPS|Einrichtungsstatus/.test(message) ? t('Du musst nichts weiter anklicken. Website und Admin-Zugang werden zum Schluss geprüft.') : t('Der Vorgang läuft auf deinem Gerät weiter. Nach Neuladen verbindet sich die Anzeige wieder mit ihm.');
    operationStatus.hidden = false;
    document.querySelectorAll('[data-action]').forEach((item) => { item.disabled = true; });
    if (button) {
      button.dataset.idleLabel = button.innerHTML;
      button.classList.add('is-busy');
      button.setAttribute('aria-busy', 'true');
      button.innerHTML = spinnerMarkup;
      button.append(document.createTextNode(buttonLabel));
    }
    output.textContent = message;
    if(!document.getElementById('create-dialog').open) operationStatus.scrollIntoView({ block: 'nearest', behavior: 'instant' });
  }

  function endOperation() {
    operationInProgress = false;
    lastProjects = '';
    operationStatus.hidden = true;
    document.querySelector('#create-form button[type=submit]').disabled = false;
    document.querySelectorAll('[data-action]').forEach((button) => {
      button.disabled = false;
      button.classList.remove('is-busy');
      button.removeAttribute('aria-busy');
      if (button.dataset.idleLabel) button.innerHTML = button.dataset.idleLabel;
    });
  }

  const esc = (value) => String(value).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const hostnameOf = (value) => { try { return new URL(value).hostname; } catch (_) { return String(value || t('unbekannt')); } };
  const localUrl = (value) => {
    try {
      const url = new URL(value, window.location.href);
      if (!['http:', 'https:'].includes(url.protocol)) return '#';
      if (url.hostname === '127.0.0.1' || url.hostname === 'localhost' || url.hostname.endsWith('.localhost')) return url.href;
    } catch (_) { /* Invalid URLs are shown as unavailable. */ }
    return '#';
  };

  function finishedJobs() {
    try { return JSON.parse(localStorage.getItem('wsc-finished-jobs')) || []; } catch (_) { return []; }
  }
  function finishJob(id) {
    try { localStorage.setItem('wsc-finished-jobs',JSON.stringify([...new Set([...finishedJobs(),id])].slice(-100)));localStorage.removeItem('wsc-pending-install'); } catch (_) { /* Server discovery also works without storage. */ }
  }
  function rememberJob(data) {
    try { localStorage.setItem('wsc-pending-install',JSON.stringify({id:data.job_id,name:data.name,action:data.action})); } catch (_) { /* The server keeps the job independently. */ }
  }

  async function api(path, options = {}) {
    let response;
    try { response = await fetch(path, {
      cache: 'no-store', ...options,
      headers: { 'Content-Type': 'application/json', 'X-Panel-Token': TOKEN, 'X-Workbench-Version': VERSION, ...(options.headers || {}) },
    }); } catch (error) {
      throw new Error(t('Die Verbindung zur Workbench wurde unterbrochen. Lade die Seite neu, um den Projekt- und Vorgangsstatus zu prüfen.'));
    }
    const data = window.WorkbenchLocale.localizeResponse(await response.json().catch(() => ({})));
    if (data.version_mismatch) {
      const url = new URL(window.location.href); url.searchParams.set('ui', data.version); window.location.replace(url.href);
      throw new Error(t('Die aktualisierte Oberfläche wird geladen. Bitte danach erneut einrichten.'));
    }
    if (!response.ok) throw new Error(data.error || response.statusText || t('Anfrage fehlgeschlagen.'));
    if (response.status === 202 && data.job_id) {
      rememberJob(data);
      return trackJob(data.job_id, data.name, data.action);
    }
    return data;
  }

  function showInstallationState(name, stage) {
    const card = list.querySelector(H`[data-project="${CSS.escape(name || '')}"]`);
    if (!card) return;
    if (card.dataset.installing !== 'true') {
      card.dataset.installing = 'true';
      card.querySelector('.main-actions').innerHTML=H`<button class="button primary is-busy" disabled>${spinnerMarkup}Einrichtung läuft …</button>`;
      const badge = card.querySelector('.project-head .badge');
      badge.textContent = t('Wird eingerichtet'); badge.className = 'badge running';
      card.querySelector('.next-step').innerHTML = H('<strong>Die automatische Einrichtung läuft.</strong><span data-current-stage></span>');
      const credentials = card.querySelector('[data-credentials]');
      credentials.open = false;
      credentials.dataset.editable = 'false';
      credentials.querySelector('summary').textContent = t('Login-Daten ansehen');
      const intro=card.querySelector('[data-panel=credentials]>p');if(intro)intro.textContent=t('Die Einrichtung läuft mit deinem gespeicherten Adminzugang.');
      const edit = credentials.querySelector('.credentials-edit');
      if (edit) edit.hidden = true;
    }
    const label = card.querySelector('[data-current-stage]');
    if (label.textContent !== stage) label.textContent = stage;
  }

  async function trackJob(id, name, action = 'install') {
    let failures = 0;
    while (true) {
      await new Promise((resolve) => window.setTimeout(resolve, 1000));
      let response;
      let job;
      try {
        response = await fetch(H`/api/jobs/${encodeURIComponent(id)}`, { headers: { 'X-Panel-Token': TOKEN }, cache: 'no-store', signal: AbortSignal.timeout(10000) });
        job = await response.json();
        failures = 0;
      } catch (error) {
        failures += 1;
        operationMessage.textContent = t('Verbindung wird wiederhergestellt. Der Vorgang läuft auf dem Gerät weiter …');
        if (failures < 10) continue;
        throw new Error(t('Der Status ist vorübergehend nicht erreichbar. Der Vorgang läuft weiter. Lade die Seite neu, um ihn wieder anzuzeigen.'));
      }
      if (!response.ok || job.state === 'failed') {
        finishJob(id);
        throw new Error(t(job.error) || t('Der Vorgangsstatus ist nicht verfügbar. Lade die Projektübersicht neu.'));
      }
      const label = H`${name || job.name}: ${t(job.stage) || t('Vorgang läuft …')}`;
      if (operationMessage.textContent !== label) operationMessage.textContent = label;
      if (action === 'install' && job.state === 'running') showInstallationState(name || job.name, t(job.stage) || t('Umgebung wird vorbereitet …'));
      const phases = document.getElementById('install-phases'); phases.hidden = action !== 'install';
      const phase = /Startseite|Stylesheets|Admin-Zugang|Dateien und Admin/.test(job.stage || '') ? 2 : /Installer|ACP|Core|Ersteinrichtung|Installationsschritt/.test(job.stage || '') ? 1 : 0;
      phases.querySelectorAll('[data-phase]').forEach((item, index) => {
        item.classList.toggle('complete', index < phase);
        if (index === phase) item.setAttribute('aria-current', 'step'); else item.removeAttribute('aria-current');
      });
      if (job.state === 'done') {
        finishJob(id);
        const messages = { install: t('WoltLab ist eingerichtet. Website und Administration können jetzt geöffnet werden.'), snapshot: t('Sicherung erstellt und geprüft.'), export: t('Server-Export erstellt.'), restore: t('Sicherung wiederhergestellt.') };
        return { ok: true, output: job.output, result: job.result, message: messages[action] || t('Vorgang abgeschlossen.') };
      }
    }
  }

  async function openACP(button) {
    const tab = window.open('about:blank', '_blank');
    if(!tab){showResult(t('Bitte erlaube ein neues Browserfenster und versuche es erneut.'),true);return;}
    tab.opener=null;
    tab.document.title=t('ACP-Anmeldung');
    tab.document.body.textContent=t('ACP-Anmeldung wird vorbereitet …');
    beginOperation(button,t('ACP-Anmeldung wird vorbereitet …'),t('Anmelden …'));
    try {
      const data=await api(`/api/instances/${encodeURIComponent(button.dataset.name)}/acp-login`,{method:'POST',body:'{}'});
      if(tab.closed)throw new Error(t('Das Anmeldefenster wurde geschlossen. Bitte erneut öffnen.'));
      const form=tab.document.createElement('form');form.method='POST';form.action=localUrl(data.result.url);
      const token=tab.document.createElement('input');token.type='hidden';token.name='token';token.value=data.result.token;form.append(token);tab.document.body.append(form);form.submit();
      showResult(t('Die Administration wird mit deinem gespeicherten Adminzugang geöffnet.'));
    } catch(error) {
      if(!tab.closed)tab.close();showResult(error.message,true);
      const project=projectDetails.find(item=>item.name===button.dataset.name);
      await ask({title:t('ACP-Anmeldung nicht abgeschlossen'),description:error.message,body:project?H`<p><a class="button" href="${esc(localUrl(project.url+'/acp/'))}" target="_blank" rel="noopener">ACP manuell öffnen ↗</a></p>`:'',confirm:t('Schließen'),cancel:''});
    } finally {endOperation();await refresh();}
  }

  let hostInstallation=null;
  async function installHost(button) {
    if(!hostInstallation)return;
    const accepted=await ask({title:t('Voraussetzungen einrichten'),description:t('Die Einrichtung läuft in deinem Systemterminal. Bestätige dort bei Bedarf Systemabfragen.'),body:H`<ul>${hostInstallation.steps.map(step=>H`<li>${esc(t(step))}</li>`).join('')}</ul><p>${esc(t('Bereits installierte Programme werden nicht ersetzt. Ein Neustart, erneutes Anmelden oder die erste Docker-Desktop-Freigabe kann erforderlich sein.'))}</p><p><code>${esc(hostInstallation.command)}</code></p>`,confirm:t('Systemterminal öffnen')});
    if(!accepted)return;
    beginOperation(button,t('Bitte schließe die Einrichtung im Systemterminal ab …'),t('Einrichtung läuft …'));
    try{const data=await api('/api/system/install',{method:'POST',body:'{}'});output.textContent=data.output||'';await loadSystem();showResult(systemReady?t('Dein Gerät ist bereit.'):t('Einrichtung beendet. Die Systemprüfung zeigt die noch nötigen Schritte.'));}
    catch(error){showResult(error.message,true);output.textContent=error.message;}
    finally{endOperation();await loadSystem();}
  }

  function showResult(message, isError = false) {
    resultMessage.textContent = message.length > 360 ? message.slice(0, 360) + t(' … Weitere Details stehen im Protokoll.') : message;
    resultMessage.classList.toggle('error', isError);
    resultMessage.hidden = false;
    if (isError) document.getElementById('operation-details').open = true;
  }

  function toast(message, isError = false) {
    const item = document.createElement('div');
    item.className = H`toast${isError ? ' error' : ''}`;
    item.textContent = message;
    toastArea.append(item);
    window.setTimeout(() => item.remove(), 4500);
  }

  const actionIcons = {install:'gear',start:'play',stop:'stop',doctor:'heart-pulse',logs:'server',snapshot:'box-archive',restore:'arrow-rotate-left',export:'truck-arrow-right',remove:'trash-can',recovery_install:'life-ring',recovery_remove:'xmark',uploads:'upload',tls_enable:'shield-halved',tls_disable:'shield-halved',mail_start:'play',mail_stop:'stop',guide_domain:'globe',guide_directory:'folder-tree',guide_migration:'truck-arrow-right'};
  const projectViews = new Map();
  function projectCard(project) {
    const phase = project.installation?.state || (project.site_ready ? 'ready' : 'prepared');
    const ready = project.site_ready && phase === 'ready';
    const busy = phase === 'running';
    const canInstall = !project.files_available && project.core_available && !busy;
    const needsArchive = !project.files_available && !project.core_available && !busy;
    const state = project.status_error ? t('Prüfung nötig') : busy ? t('Wird eingerichtet') : phase === 'failed' ? t('Einrichtung unterbrochen') : ready ? (project.running ? t('Einsatzbereit') : t('Gestoppt')) : phase === 'unverified' ? t('Noch nicht geprüft') : t('Vorbereitet');
    const name = esc(project.name);
    const action = (id, label, type = '', extra = '') => H`<button class="button ${type}" data-action="${id}" data-name="${name}" ${extra}>${icon(actionIcons[id] || 'gear')}${label}</button>`;
    const drawer = (label, tab = 'overview', type = '') => H`<button class="button ${type}" data-project-open="${name}" data-project-tab="${tab}">${icon('gear')}${label}</button>`;
    const main = busy ? H`<button class="button primary is-busy" disabled>${spinnerMarkup}Einrichtung läuft …</button>`
      : project.status_error ? action(project.port_mismatch ? 'repair-ports' : 'doctor', project.port_mismatch ? t('Ports korrigieren') : t('Problem prüfen'), 'primary')
      : canInstall ? drawer(t('Login-Daten prüfen & einrichten'), 'credentials', 'primary')
      : needsArchive ? drawer(t('Installationsarchiv hinzufügen'), 'overview', 'primary')
      : ready && project.running ? H`<a class="button primary" href="${esc(localUrl(project.url))}" target="_blank" rel="noopener">${icon('arrow-up-right-from-square')}Website öffnen</a>${action('acp_login',t('ACP öffnen'))}${action('stop',t('Stoppen'))}`
      : ready ? action('start',t('Projekt starten'),'primary') : action('doctor',t('Installation prüfen'),'primary');
    const setup = project.status_error ? project.status_error : busy ? project.installation?.stage || t('Umgebung wird vorbereitet …') : canInstall ? t('Nächster Schritt: Adminzugang prüfen und WoltLab automatisch einrichten.') : needsArchive ? t('Für dieses Projekt fehlt noch ein passendes WoltLab-Installationsarchiv.') : phase === 'failed' ? t('Die Einrichtung wurde unterbrochen. Unter „Werkzeuge“ findest du Diagnose und Protokoll.') : '';
    const badge = phase === 'failed' || project.status_error ? 'failed' : ready && project.running ? 'ready' : busy ? 'running' : '';
    const mailRunning = (project.services || []).some(s => s.name === 'mail' && s.state === 'running');
    const services = [ ['web', project.webserver === 'apache' ? 'Apache + PHP' : 'Nginx'], ...(project.webserver === 'apache' ? [] : [['php','PHP-FPM']]), ['database',project.database === 'mysql8' ? 'MySQL 8' : 'MariaDB'], ['mail',t('Mail-Test (Mailpit)')] ];
    const serviceRows = services.map(([key,label]) => {
      const status = (project.services || []).find(s=>s.name===key);
      const running = status?.state === 'running';
      return H`<tr><th scope="row">${label}</th><td><span class="badge ${running?'ready':''}">${running?t('Läuft'):t('Gestoppt')}</span></td><td>${key==='mail'?action(mailRunning?'mail_stop':'mail_start',mailRunning?t('Stoppen'):t('Starten'))+(mailRunning?H` <a href="${esc(localUrl(project.mail_url))}" class="button" target="_blank" rel="noopener">Postfach ↗</a>`:''):''} ${action('logs','Logs','',H`data-service="${key}"`)}</td></tr>`;
    }).join('');
    const tabs=[['overview',t('Übersicht')],['credentials',t('Zugangsdaten')],['services',t('Dienste')],['backups',t('Sicherungen')],['tools',t('Werkzeuge')]];
    return H`<article class="project" data-project="${name}" data-url="${esc(localUrl(project.url))}">
      <div class="project-head"><div><h3 class="project-title">${name}</h3><p class="project-subtitle">WoltLab ${esc(project.suite)} · ${project.webserver==='apache'?'Apache':'Nginx'} · PHP ${esc(project.php)}${project.experimental?' · Alpha':project.legacy?' · Legacy':''}</p></div><span class="badge ${badge}">${esc(state)}</span></div>
      <p class="next-step" ${setup?'':'hidden'}>${esc(setup)}</p>
      <div class="project-actions"><div class="actions main-actions">${main}</div>${drawer(t('Verwalten'))}</div>
      <div class="project-drawer" hidden><div class="project-tabs" role="tablist" aria-label="${name} verwalten">${tabs.map(([key,label])=>H`<button id="tab-${name}-${key}" class="project-tab" role="tab" aria-selected="${key==='overview'}" aria-controls="panel-${name}-${key}" tabindex="${key==='overview'?0:-1}" data-tab="${key}">${label}</button>`).join('')}</div>
      <section class="tab-panel" role="tabpanel" id="panel-${name}-overview" aria-labelledby="tab-${name}-overview" data-panel="overview">
        ${project.status_error?H`<p class="result error">${esc(project.status_error)}</p>`:''}
        ${needsArchive?H`<form class="archive-upload" data-archive-for="${name}"><label>WoltLab-Installations-ZIP<input type="file" accept=".zip,application/zip" required></label><p class="hint">Maximal 256 MiB, mit install.php.</p><button class="button primary" type="submit">Archiv einspielen</button></form>`:''}
        <dl class="meta"><dt>Projektadresse</dt><dd>${esc(project.url)}</dd><dt>Suite-Profil</dt><dd>WoltLab ${esc(project.suite)}${project.experimental?t(' · inoffizieller Entwicklungsbuild'):''}</dd><dt>Webserver</dt><dd>${project.webserver==='apache'?t('Apache mit PHP'):t('Nginx mit PHP-FPM')}</dd><dt>Datenbank</dt><dd>${project.database==='mysql8'?'MySQL 8':'MariaDB 10.11'}</dd><dt>HTTPS</dt><dd>${project.tls_enabled?t('Lokales Zertifikat eingerichtet'):t('Wird bei Bedarf automatisch eingerichtet')}</dd></dl>
        <a class="button" href="/api/instances/${name}/profile" download="${name}.wsc-local.json">${icon('upload')}Projektprofil herunterladen</a>${infoButton('profile',t('Teilbares Projektprofil erklären'))}<p class="hint">Teilbar ohne Login-Daten. Neue Projekte erhalten eigene Passwörter und freie Ports.</p>
      </section>
      <section class="tab-panel" role="tabpanel" id="panel-${name}-credentials" aria-labelledby="tab-${name}-credentials" data-panel="credentials" hidden>
        <p>${canInstall?t('Prüfe den erzeugten Adminzugang. Du kannst Name, E-Mail und Passwort vor der Einrichtung ändern.'):t('Hier findest du den Adminzugang für dieses Projekt. Änderungen nach der Installation erfolgen in WoltLab.')}</p>
        <details class="credentials" data-credentials="${name}" data-editable="${canInstall}"><summary>Adminzugang anzeigen ${infoButton('credentials',t('Admin- und Datenbankzugang erklären'))}</summary><div class="credential-content"><p class="hint">Login-Daten werden lokal geladen …</p></div></details>
        ${canInstall?H`<div class="setup-footer">${action('install',phase==='failed'?t('Erneut einrichten'):t('Einrichten'),'primary')}<p class="hint">WoltLab wird vollständig in der Dashboard-Sprache installiert. Du musst keinen Installer bedienen.</p></div>`:''}
      </section>
      <section class="tab-panel" role="tabpanel" id="panel-${name}-services" aria-labelledby="tab-${name}-services" data-panel="services" hidden><div class="heading-with-info"><h4>Projekt-Dienste</h4>${infoButton('services',t('Dienste und Mail-Test erklären'))}</div><p>Start und Stopp des gesamten Projekts findest du oben. Den Mail-Test kannst du unabhängig einschalten.</p>${mailRunning?H('<p class="hint">Für den Mail-Test in WoltLab SMTP-Server mail, Port 1025 und keine Anmeldung verwenden.</p>'):''}<div class="table-scroll"><table class="service-table"><thead><tr><th>Dienst</th><th>Status</th><th>Aktionen</th></tr></thead><tbody>${serviceRows}</tbody></table></div></section>
      <section class="tab-panel" role="tabpanel" id="panel-${name}-backups" aria-labelledby="tab-${name}-backups" data-panel="backups" hidden><div class="heading-with-info"><h4>Dateien und Datenbank zusammen sichern</h4>${infoButton('backups',t('Sicherung und Export erklären'))}</div><p>Eine Sicherung hält beide Teile auf demselben Stand. Das Projekt wird dafür kurz pausiert.</p><div class="actions">${action('snapshot',t('Sicherung erstellen'),'',project.files_available?'':'disabled')}${action('export',t('Server-Export erstellen'),'',project.files_available?'':'disabled')}</div><div class="restore-controls"><label for="snapshot-${name}">Vorhandene Sicherung</label><select id="snapshot-${name}" data-snapshot-select><option value="">Sicherungen werden geladen …</option></select>${action('restore',t('Wiederherstellen'))}</div><p class="hint">Ein Export ist ein Paket mit Anleitung für den Serverumzug. Ein direkter SSH-Upload ist nicht enthalten.</p><ul class="export-list" aria-label="Erstellte Exporte"></ul></section>
      <section class="tab-panel" role="tabpanel" id="panel-${name}-tools" aria-labelledby="tab-${name}-tools" data-panel="tools" hidden><div class="tool-group"><h4>Diagnose und Einstellungen</h4><div class="actions">${action('doctor',t('Projekt prüfen'))}${action('logs',t('Webserver-Logs'))}${action('uploads',t('Uploadlimits'))}${action(project.tls_enabled?'tls_disable':'tls_enable',project.tls_enabled?t('HTTPS deaktivieren'):t('HTTPS einrichten'))}</div></div><div class="tool-group"><h4>WoltLab-Hilfen</h4><p class="hint">Domain und Verzeichnisse: Sicherung plus geführte Anleitung. Serverumzug: Exportpaket plus Schritte für den Zielserver.</p>${project.recovery_enabled?H`<div class="recovery-notice"><strong>${icon('life-ring')}Recovery ist aktiv</strong><p>Nach Gebrauch wieder entfernen.</p><a href="${esc(localUrl(project.url+'/wsc-recovery.php'))}" target="_blank" rel="noopener">Offizielles Recovery Tool öffnen ↗</a></div>`:''}<div class="actions">${action('recovery_install',t('Recovery einrichten'),'',(!project.files_available || project.recovery_enabled)?'disabled':'')}${action('recovery_remove',t('Recovery entfernen'),'',project.recovery_enabled?'':'disabled')}${infoButton('recovery',t('Recovery erklären'))}${action('guide_domain',t('Domain: Anleitung'),'',project.files_available?'':'disabled')}${action('guide_directory',t('Verzeichnisse: Anleitung'),'',project.files_available?'':'disabled')}${action('guide_migration',t('Serverumzug vorbereiten'),'',project.files_available?'':'disabled')}</div></div><div class="danger-zone"><h4>Projekt entfernen</h4><p>Entfernt die Dateien, Datenbank, Container und lokalen Login-Daten dieses Projekts. Bei Bedarf vorher sichern.</p>${action('remove',t('Projekt vollständig entfernen'),'danger')}</div></section>
      </div></article>`;
  }

  async function activateProject(name, tab='overview', open=true) {
    const card=list.querySelector(H`[data-project="${CSS.escape(name)}"]`); if(!card) return;
    projectViews.set(name,{open,tab}); card.querySelector('.project-drawer').hidden=!open;
    const toggle=card.querySelector('.project-actions>[data-project-open]');if(toggle){toggle.innerHTML=icon(open?'xmark':'gear')+(open?t('Schließen'):t('Verwalten'));toggle.setAttribute('aria-expanded',String(open));}
    card.querySelectorAll('[data-tab]').forEach(button=>{const selected=button.dataset.tab===tab;button.setAttribute('aria-selected',String(selected));button.tabIndex=selected?0:-1;});
    card.querySelectorAll('[data-panel]').forEach(panel=>panel.hidden=panel.dataset.panel!==tab);
    if(!open)return;
    if(tab==='credentials'){const details=card.querySelector('[data-credentials]');details.open=true;await loadCredentials(details);}
    if(tab==='backups'){
      const select=card.querySelector('[data-snapshot-select]');
      try {
        const [data,exports]=await Promise.all([api(H`/api/instances/${encodeURIComponent(name)}/snapshots`),api(H`/api/instances/${encodeURIComponent(name)}/exports`)]);
        select.innerHTML=(data.items||[]).map(s=>H`<option value="${esc(s.name)}">${esc(s.name)}</option>`).join('')||H('<option value="">Noch keine Sicherung vorhanden</option>');
        card.querySelector('[data-action=restore]').disabled=!(data.items||[]).length;
        card.querySelector('.export-list').innerHTML=(exports.items||[]).map(item=>H`<li><span>${esc(item.name)} <small>${(item.size/1024/1024).toFixed(1)} MiB</small></span><a class="button" href="/api/instances/${encodeURIComponent(name)}/exports/${encodeURIComponent(item.name)}" download>Export herunterladen</a></li>`).join('');
      }
      catch(error){select.innerHTML=H('<option value="">Sicherungen nicht verfügbar</option>');showResult(error.message,true);}
    }
  }

  async function refresh() {
    if (operationInProgress) return;
    list.setAttribute('aria-busy', 'true');
    try {
      const data = await api('/api/instances');
      const projects = data.items || [];
      projectDetails = projects;
      knownProjects = new Set(projects.map((project) => project.name));
      document.querySelector('#view-projects .page-heading [data-create-open]').hidden=projects.length===0;

      const signature = JSON.stringify(projects.map((project) => ({...project, services: (project.services || []).map(({name, state}) => ({name, state}))})));
      if (signature === lastProjects || (list.contains(document.activeElement) && document.activeElement.matches('input,select,textarea'))) return;
      lastProjects = signature;
      count.textContent = H`${projects.length} ${projects.length === 1 ? t('Projekt') : t('Projekte')}`;
      list.innerHTML = projects.length
        ? projects.map(projectCard).join('')
        : H('<div class="empty"><h3>Dein erstes WoltLab-Projekt</h3><p>Wähle eine Suite-Version und erhalte eine fertig eingerichtete lokale Installation.</p><ol class="empty-steps"><li>Projekt vorbereiten</li><li>Login-Daten prüfen</li><li>Automatisch einrichten</li></ol><button class="button primary" data-create-open>Projekt vorbereiten</button></div>');
      for(const [name,view] of projectViews) if(knownProjects.has(name)) activateProject(name,view.tab,view.open);
    } catch (error) {
      count.textContent = t('Status nicht verfügbar');
      list.innerHTML = H`<div class="empty">${esc(error.message)}<br>Starte das Dashboard erneut mit <code>./panel.sh</code>.</div>`;
    } finally {
      list.setAttribute('aria-busy', 'false');
    }
  }

  async function presentToolResult(action, name, result) {
    if (guides[action]) {
      await activateProject(name, action==='guide_migration'?'backups':'tools');
      let download='';
      if(action==='guide_migration') {
        await activateProject(name,'backups');
        const data=await api(H`/api/instances/${encodeURIComponent(name)}/exports`);
        if(data.items?.length)download=H`<p><a class="button primary" download href="/api/instances/${encodeURIComponent(name)}/exports/${encodeURIComponent(data.items[0].name)}">${icon('upload')}Umzugspaket herunterladen</a></p>`;
      }
      await ask({title:action==='guide_migration'?t('Umzugspaket ist bereit'):t('Sicherung erstellt – nächste Schritte'),description:guides[action].description,body:download+guideBody(action)+H`<details class="dialog-log"><summary>Sicherung und technische Details</summary><pre>${esc(result.output || '')}</pre></details>`,confirm:t('Verstanden'),cancel:''});
    } else if(action==='recovery_install') {
      const card=list.querySelector(H`[data-project="${CSS.escape(name)}"]`);
      const recovery=await api(H`/api/instances/${encodeURIComponent(name)}/recovery`);
      const address=localUrl(recovery.url || (card?.dataset.url || '').replace(/\/$/,'')+'/wsc-recovery.php');
      await activateProject(name,'tools');
      await ask({title:t('Recovery Tool ist bereit'),description:t('Eine Sicherung wurde erstellt. Öffne das offizielle Werkzeug, stelle deinen Zugang wieder her und entferne die Datei danach wieder unter Werkzeuge.'),body:H`<p><a class="button primary" href="${esc(address)}" target="_blank" rel="noopener">${icon('life-ring')}Recovery Tool öffnen</a></p><p>Das offizielle Werkzeug bietet eine zusätzliche Datei <code>wsc-recovery-auth.php</code> zum Download an. Speichere sie unverändert in diesem Projektordner und bestätige anschließend die Authentifizierung im Werkzeug:</p><p><code>${esc(recovery.directory || '')}</code></p><p>„Recovery entfernen“ bereinigt danach beide erkannten Dateien.</p><p><a href="https://manual.woltlab.com/de/recovery-tool/" target="_blank" rel="noopener">WoltLab-Anleitung ↗</a></p>`,confirm:t('Verstanden'),cancel:''});
    } else if(action==='recovery_remove') {
      showResult(t('Das Recovery Tool wurde entfernt. Der Link ist nicht mehr verfügbar.'));
    }
  }

  async function run(action, name, button) {
    if (action === 'repair-ports') action = 'start';
    let snapshot = '';
    const prompts = {
      stop: H`Projekt „${name}“ anhalten? Dateien und Datenbank bleiben erhalten.`,
      mail_stop: H`Den Mail-Testdienst für „${name}“ anhalten?`,
      snapshot: H`Vollständige Sicherung für „${name}“ erstellen? Die Website wird kurz pausiert.`,
      export: H`Server-Export für „${name}“ erstellen? Das Paket enthält Dateien und Datenbank, aber keine Passwörter.`,
      guide_domain: H`WoltLab-Hilfe zur Domainänderung für „${name}“ öffnen? Vorher wird eine Sicherung erstellt; Änderungen an der Datenbank erfolgen nicht automatisch.`,
      guide_directory: H`WoltLab-Hilfe zur Verzeichnisstruktur für „${name}“ öffnen? Vorher wird eine Sicherung erstellt; Änderungen an Dateien oder Datenbank erfolgen nicht automatisch.`,
      guide_migration: H`Umzugshinweise und einen anbieterneutralen Export für „${name}“ erstellen? Das Paket enthält keine lokalen Geheimnisse.`,
      restore: H`Eine Sicherung für „${name}“ wiederherstellen? Dateien und Datenbank werden ersetzt. Vorher wird automatisch eine Sicherung des aktuellen Standes erstellt.`,
      recovery_install: H`Das offizielle WoltLab Recovery Tool wird öffentlich erreichbar abgelegt. Vor Gebrauch eine Sicherung erstellen und die Datei anschließend sofort entfernen. Einrichten?`,
      recovery_remove: H`Das von wsc-local abgelegte Recovery Tool entfernen?`,
      tls_enable: H`mkcert richtet ein lokales CA-Zertifikat im Benutzerprofil und HTTPS für „${name}.localhost“ ein. Fortfahren?`,
      tls_disable: H`Lokales HTTPS für „${name}“ abschalten und auf HTTP zurückstellen?`,
      'start-experimental': H`WSC 6.3 benötigt HTTPS. Ich richte ein lokales Zertifikat für „${name}.localhost“ ein und starte danach die Website. Beim ersten Mal kann eine Systemabfrage zur Vertrauensstellung des Zertifikats erscheinen. Fortfahren?`,
    };
    if (action === 'remove') {
      const confirmation = await ask({title:H`Projekt „${name}“ endgültig entfernen?`,description:t('Dateien, Datenbank, Container und lokale Zugangsdaten werden gelöscht. Erstelle bei Bedarf vorher eine Sicherung oder einen Export.'),body:H('<p>Gemeinsame Downloads und Docker-Basisimages bleiben verfügbar.</p>'),confirm:t('Projekt endgültig entfernen'),danger:true,input:{label:H`Zum Bestätigen ${name} eingeben`,expected:name}});
      if (!confirmation) {
        toast(t('Abgebrochen. Es wurde nichts gelöscht.'));
        return;
      }
    }
    if (action === 'uploads') {
      const choice = await ask({title:t('Uploadlimits anpassen'),description:t('Die Workbench zeigt zuerst die betroffenen PHP- und Webserver-Einstellungen. Erst danach bestätigst du die Änderung.'),confirm:t('Änderungen prüfen'),input:{label:t('Maximale Uploadgröße'),value:'256M',pattern:/^[1-9][0-9]{0,5}[MG]$/,error:t('Bitte eine Größe wie 256M oder 1G eingeben.')}});
      if (!choice) return;
      const size = choice.value;
      beginOperation(button, H`Uploadlimits für ${name} werden geprüft …`, t('Wird geprüft …'));
      try {
        const preview = await api('/api/workbench', { method: 'POST', body: JSON.stringify({ action: 'uploads_preview', name, size: size.trim() }) });
        if (!await ask({title:t('Uploadlimit: Änderungsvorschau'),description:t('Nach dem Anwenden werden die betroffenen Dienste neu gestartet.'),body:H`<pre class="change-preview">${esc(preview.output)}</pre>`,confirm:t('Änderungen anwenden')})) return;
        const applied = await api('/api/workbench', { method: 'POST', body: JSON.stringify({ action: 'uploads_apply', name, size: size.trim() }) });
        output.textContent = applied.output || t('Uploadlimits angewandt.');
        toast(t('Uploadlimits wurden angewandt.'));
        await refresh();
      } catch (error) {
        output.textContent = error.message;
        toast(error.message, true);
      } finally {
        endOperation();
        await refresh();
      }
      return;
    }
    if (action === 'restore') {
      snapshot=button.closest('.project').querySelector('[data-snapshot-select]').value;
      if(!snapshot){toast(t('Bitte zuerst eine vorhandene Sicherung auswählen.'),true);return;}
      prompts.restore += H`\nAusgewählt: ${snapshot}`;
    }
    if (guides[action]) {
      if (!await ask({title:guides[action].title,description:guides[action].description,body:guideBody(action),confirm:action==='guide_migration'?t('Exportpaket erstellen'):t('Sicherung erstellen & Anleitung öffnen')})) return;
    } else if (prompts[action] && !await ask({title:({snapshot:t('Sicherung erstellen'),restore:t('Sicherung wiederherstellen'),export:t('Server-Export erstellen'),recovery_install:t('Offizielles Recovery Tool einrichten'),recovery_remove:t('Recovery Tool entfernen'),stop:t('Projekt stoppen'),tls_disable:t('HTTPS abschalten')})[action] || t('Aktion bestätigen'),description:prompts[action],confirm:t('Bestätigen'),danger:action==='restore' || action==='tls_disable'})) return;
    const busyLabels = { install: t('WoltLab wird automatisch eingerichtet …'), start: t('Container werden gestartet …'), 'start-experimental': t('HTTPS wird eingerichtet …'), stop: t('Container werden gestoppt …'), snapshot: t('Sicherung wird erstellt …'), export: t('Server-Export wird erstellt …'), restore: t('Sicherung wird wiederhergestellt …'), doctor: t('Projekt wird geprüft …'), tls_enable: t('HTTPS wird eingerichtet …'), remove: t('Projekt wird entfernt …') };
    beginOperation(button, H`${name}: ${busyLabels[action] || t('Vorgang läuft …')}`, busyLabels[action] || t('Wird ausgeführt …'));
    if (action === 'install') { document.getElementById('create-dialog').close(); showInstallationState(name, t('Umgebung und HTTPS vorbereiten …')); }
    let completedResult = null;
    try {
      let result;
      if (action === 'start-experimental') {
        const tls = await api('/api/workbench', { method: 'POST', body: JSON.stringify({ action: 'tls_enable', name }) });
        output.textContent = H`${tls.output || t('Lokales HTTPS ist eingerichtet.')}\nWebsite wird gestartet …`;
        result = await api('/api/workbench', { method: 'POST', body: JSON.stringify({ action: 'start', name }) });
        const status = await api('/api/instances');
        const project = (status.items || []).find((item) => item.name === name);
        output.textContent = H`${tls.output || t('Lokales HTTPS ist eingerichtet.')}\n${result.output || t('Website gestartet.')}`;
        toast(t('Website gestartet.'));
      } else {
        result = await api('/api/workbench', { method: 'POST', body: JSON.stringify({ action, name, snapshot, service:button?.dataset.service || 'web', ...(action==='install'?{language:window.WorkbenchLocale.language}:{}) }) });
        if (action === 'start') {
          const status = await api('/api/instances');
          const project = (status.items || []).find((item) => item.name === name);
          output.textContent = result.output || t('Website gestartet.');
        } else {
          output.textContent = result.output || t('Fertig.');
        }

      }
      completedResult = result;
      const completed = {start: H`Projekt „${name}“ ist gestartet.`, stop: H`Projekt „${name}“ ist gestoppt.`, remove: H`Projekt „${name}“ wurde vollständig entfernt.`, doctor: t('Prüfung abgeschlossen. Das Ergebnis steht im Protokoll.'), logs: t('Logs geladen. Du findest sie im Protokoll.'), snapshot: t('Sicherung erstellt und geprüft.'), restore: t('Sicherung wiederhergestellt. Das Projekt ist wieder verfügbar.'), export: t('Server-Export erstellt.'), tls_enable: t('Lokales HTTPS ist eingerichtet.'), tls_disable: t('Lokales HTTPS ist deaktiviert.')};
      showResult(action === 'install' ? result.message : completed[action] || t('Vorgang abgeschlossen. Das Ergebnis steht im Protokoll.'));
      if (action === 'logs' || action === 'doctor') document.getElementById('operation-details').open = true;
      await refresh();
    } catch (error) {
      output.textContent = error.message;
      showResult(error.message, true);
    } finally {
      endOperation();
      await refresh();
    }
    if (completedResult) { try { await presentToolResult(action, name, completedResult); } catch(error) { showResult(t('Der Vorgang wurde abgeschlossen, aber die Anleitung konnte nicht angezeigt werden. ')+error.message,true); } }
  }

  document.getElementById('create-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    if (operationInProgress) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const project = String(form.get('project') || '').trim();
    const suite = String(form.get('suite') || '6.2');
    const webserver = String(form.get('webserver') || 'nginx-php-fpm');
    const source = String(form.get('source') || 'download');
    const php = String(form.get('php') || '');
    const database = String(form.get('database') || 'mariadb');
    const archive = document.getElementById('source-archive').files[0];
    if (source === 'zip' && (!archive || archive.size > 256 * 1024 * 1024)) { showResult(t('Bitte ein Installations-ZIP mit maximal 256 MiB auswählen.'), true); return; }
    const submit = event.currentTarget.querySelector('button[type="submit"]');
    document.getElementById('create-error').hidden=true;
    let projectCreated=false;
    operationInProgress = true;
    document.querySelector('[data-create-close]').disabled=true;
    submit.disabled = true;
    submit.classList.add('is-busy');
    submit.setAttribute('aria-busy', 'true');
    operationMessage.textContent = H`Projekt ${project} wird vorbereitet …`;
    operationStatus.hidden = false;
    submit.innerHTML=spinnerMarkup;submit.append(document.createTextNode(t('Projekt wird vorbereitet …')));
    output.textContent = H`Projekt ${project} wird vorbereitet …`;
    try {
      const result = await api('/api/workbench', { method: 'POST', body: JSON.stringify({ action: 'create', project, suite, webserver, source, php, database, experimental_ack:document.getElementById('version-ack').checked, admin_username: form.get('admin_username'), admin_email: form.get('admin_email'), admin_password: form.get('admin_password') }) });
      projectCreated=true;
      if (source === 'zip') await uploadArchive(project, archive);
      output.textContent = H`Projekt „${project}“ ist vorbereitet. Sieh dir in der Projektkarte die Zugangsdaten an oder passe sie vorab an. Danach klickst du einmal auf „Einrichten“; wsc-local übernimmt die WoltLab-Installation vollständig.`;
      document.getElementById('create-dialog').close();
      projectViews.set(project,{open:true,tab:'credentials'});
      showResult(H`Projekt „${project}“ ist vorbereitet. Prüfe jetzt die Login-Daten in der Projektkarte und klicke auf „Einrichten“.`);
      formElement.reset();
      suiteSelect.dispatchEvent(new Event('change'));

      await refresh();
    } catch (error) {
      output.textContent = error.message;
      if(projectCreated){document.getElementById('create-dialog').close();projectViews.set(project,{open:true,tab:'overview'});showResult(error.message,true);}
      else{const errorBox=document.getElementById('create-error');errorBox.textContent=error.message;errorBox.hidden=false;errorBox.scrollIntoView({block:'nearest'});}
    } finally {
      endOperation();
      submit.disabled = false;
      submit.classList.remove('is-busy');
      submit.removeAttribute('aria-busy');
      operationStatus.hidden = true;
      submit.textContent = t('Projekt vorbereiten');
      document.querySelector('[data-create-close]').disabled=false;
      await refresh();
    }
  });

  let catalog = {};
  const suiteSelect = document.getElementById('suite-version');
  const suiteHint = document.getElementById('suite-hint');
  const sourceMode = document.getElementById('source-mode');
  function updateSource() {
    const canDownload = ['6.2', '6.3'].includes(suiteSelect.value);
    sourceMode.querySelector('[value=download]').disabled = !canDownload;
    if (!canDownload) sourceMode.value = 'zip';
    document.getElementById('archive-input').hidden = sourceMode.value !== 'zip';
    document.getElementById('source-archive').required = sourceMode.value === 'zip';
  }
  sourceMode.addEventListener('change', updateSource);
  suiteSelect.addEventListener('change', () => {
    suiteHint.textContent = suiteSelect.value === '6.3'
      ? t('Inoffizielle frühe Alpha: braucht PHP 8.4.23+ und HTTPS; nicht für produktive Daten.')
      : ['5.5', '6.0'].includes(suiteSelect.value) ? t('Legacy-Profil: eigenes ZIP erforderlich, kein regulärer Support.') : suiteSelect.value === '6.1' ? t('Eigenes Installations-ZIP erforderlich. Die passende PHP-Version wird automatisch gewählt.') : t('Passende PHP-Version, Datenbank und lokales HTTPS werden automatisch eingerichtet.');
    updateSource();
    const choices=catalog[suiteSelect.value]?.php_choices || ({'5.5':['8.1'],'6.0':['8.3','8.2'],'6.1':['8.3','8.2'],'6.2':['8.4','8.3','8.2'],'6.3':['8.5']})[suiteSelect.value];
    document.getElementById('php-version').innerHTML=choices.map((php,index)=>H`<option value="${php}">PHP ${php}${index===0?' · empfohlen':''}</option>`).join('');
    const needsConsent=['5.5','6.0','6.3'].includes(suiteSelect.value);
    document.getElementById('version-consent').hidden=!needsConsent;document.getElementById('version-ack').required=needsConsent;document.getElementById('version-ack').checked=false;
    document.getElementById('version-consent-label').textContent=suiteSelect.value==='6.3'?t('Ich nutze den inoffiziellen Alpha-Build ausschließlich für lokale Tests.'):t('Ich nutze diese Legacy-Version bewusst für Kompatibilitätstests.');
  });
  suiteSelect.dispatchEvent(new Event('change'));

  let systemReady = null;
  let systemCheck = null;
  function showView(name) {
    document.querySelectorAll('.app-view').forEach(view=>view.hidden=view.id!==H`view-${name}`);
    document.querySelectorAll('.app-nav [data-view]').forEach(button=>{const active=button.dataset.view===name;button.classList.toggle('active',active);if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');});
    if(name==='system'&&systemReady===null) loadSystem();
    document.dispatchEvent(new CustomEvent('workbench-view',{detail:name}));
    const heading=document.querySelector(H`#view-${name} h1`);heading.tabIndex=-1;heading.focus({preventScroll:true});
  }
  async function loadSystem() {
    if(systemCheck)return systemCheck;
    systemCheck=(async()=>{
      const button=document.getElementById('system-refresh');button.disabled=true;button.classList.add('is-busy');button.innerHTML=spinnerMarkup+t('Wird geprüft …');
      try {
        const data=await api('/api/system');systemReady=data.ready;hostInstallation=data.installation;
        document.getElementById('host-summary').textContent=H`${data.host.label} · ${data.ready?t('Bereit für WoltLab'):t('Vorbereitung erforderlich')}`;
        document.getElementById('system-dot').classList.toggle('ready',data.ready);document.getElementById('system-dot').classList.toggle('missing',!data.ready);
        document.getElementById('system-report').innerHTML=H`<div class="system-summary ${data.ready?'ready':'missing'}"><strong>${data.ready?t('Dein Gerät ist bereit.'):t('Diese Voraussetzungen fehlen noch.')}</strong><p>${esc(data.host.label)} · ${esc(data.host.architecture)}</p>${!data.ready&&data.installation?.supported?H`<button class="button primary" data-action="host_install">${icon('gear')}Fehlendes einrichten</button>`:''}</div><div class="system-checks">${data.checks.map(check=>H`<article class="system-check"><span class="check-symbol ${check.status}" aria-hidden="true">${check.status==='ready'?'✓':'!'}</span><div><h2>${esc(check.label)}</h2><p>${esc(check.detail)}</p>${check.help?H`<p class="check-help">${esc(check.help)}</p>`:''}${check.status!=='ready'&&check.url?H`<a href="${esc(check.url)}" target="_blank" rel="noopener">Installationsanleitung ↗</a>`:''}</div><span class="badge ${check.status==='ready'?'ready':'failed'}">${check.status==='ready'?t('Bereit'):t('Erforderlich')}</span></article>`).join('')}</div>`;
      } catch(error) {systemReady=false;document.getElementById('host-summary').textContent=t('Systemprüfung nicht erreichbar');document.getElementById('system-report').textContent=error.message;}
      finally {button.disabled=false;button.classList.remove('is-busy');button.textContent=t('Erneut prüfen');systemCheck=null;}
    })();return systemCheck;
  }
  async function loadCatalog() {
    try {const data=await api('/api/catalog');catalog=Object.fromEntries(data.profiles.map(profile=>[profile.suite,profile]));suiteSelect.dispatchEvent(new Event('change'));}
    catch(error){showResult(t('Versionskatalog konnte nicht geladen werden. Die Standardprofile bleiben verfügbar.'),true);}
  }
  async function openCreate(button) {
    if(operationInProgress)return;
    button.disabled=true;
    try {await loadSystem();if(!systemReady){showView('system');return;}document.getElementById('create-error').hidden=true;document.getElementById('create-dialog').showModal();}
    finally{button.disabled=false;}
  }
  document.getElementById('system-refresh').addEventListener('click',loadSystem);
  document.getElementById('create-dialog').addEventListener('cancel',event=>{if(operationInProgress)event.preventDefault();});
  document.body.addEventListener('keydown',event=>{
    const tab=event.target.closest('[role=tab]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
    event.preventDefault();const tabs=[...tab.parentElement.querySelectorAll('[role=tab]')];const index=event.key==='Home'?0:event.key==='End'?tabs.length-1:(tabs.indexOf(tab)+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
    activateProject(tab.closest('.project').dataset.project,tabs[index].dataset.tab);tabs[index].focus();
  });

  document.body.addEventListener('click', (event) => {
    const navigation=event.target.closest('[data-view]');if(navigation)showView(navigation.dataset.view);
    const create=event.target.closest('[data-create-open]');if(create)openCreate(create);
    if(event.target.closest('[data-create-close]')&&!operationInProgress)document.getElementById('create-dialog').close();
    const open=event.target.closest('[data-project-open]');if(open){const view=projectViews.get(open.dataset.projectOpen);activateProject(open.dataset.projectOpen,open.dataset.projectTab,!(view?.open&&open.textContent.trim()===t('Schließen')));}
    const tab=event.target.closest('[data-tab]');if(tab)activateProject(tab.closest('.project').dataset.project,tab.dataset.tab);
    const button = event.target.closest('[data-action]');
    if (button && !operationInProgress && !document.getElementById('action-dialog').open) {
      if(button.dataset.action==='acp_login') openACP(button);
      else if(button.dataset.action==='host_install') installHost(button);
      else run(button.dataset.action, button.dataset.name, button);
    }
    const reveal = event.target.closest('[data-reveal]');
    if (reveal) {
      const input = reveal.closest('.credential-value').querySelector('input');
      const visible = input.type === 'password';
      input.type = visible ? 'text' : 'password';
      reveal.textContent = visible ? t('Verbergen') : t('Anzeigen');
      reveal.setAttribute('aria-pressed', String(visible));
    }
    const copy = event.target.closest('[data-copy-value]');
    if (copy) {
      navigator.clipboard.writeText(copy.dataset.copyValue || '').then(() => toast(t('In die Zwischenablage kopiert.'))).catch(() => toast(t('Kopieren nicht möglich. Bitte den Wert markieren.'), true));
    }
  });

  async function loadCredentials(details) {
    if (!details?.dataset.credentials || details.dataset.loaded || details.dataset.loading) return;
    details.dataset.loading = 'true';
    const content = details.querySelector('.credential-content');
    try {
      const data = await api(H`/api/instances/${encodeURIComponent(details.dataset.credentials)}/credentials`);
      const row = (label, value, secret = false) => H`<dt>${esc(label)}</dt><dd><div class="credential-value">${secret ? H`<input type="password" readonly value="${esc(value)}" aria-label="${esc(label)}"><button class="button" type="button" data-reveal aria-pressed="false">Anzeigen</button>` : H`<span>${esc(value)}</span>`}<button class="button" type="button" data-copy-value="${esc(value)}" aria-label="${esc(label)} kopieren">Kopieren</button></div></dd>`;
      content.innerHTML = H`<dl class="credential-grid">${row(t('Adminname'), data.admin.username)}${row(t('Admin-E-Mail'), data.admin.email)}${row(t('Adminpasswort'), data.admin.password, true)}</dl>
        ${details.dataset.editable === 'true' ? H`<details class="credentials-edit"><summary>Login-Daten ändern</summary><form data-credentials-edit="${esc(details.dataset.credentials)}"><div class="advanced-grid"><div><label>Adminname<input name="username" required maxlength="40" value="${esc(data.admin.username)}" autocomplete="username"></label></div><div><label>Admin-E-Mail<input name="email" type="email" required value="${esc(data.admin.email)}" autocomplete="email"></label></div><div><label>Neues Adminpasswort<input name="password" type="password" minlength="12" autocomplete="new-password"></label><p class="hint">Leer lassen, um das erzeugte Passwort beizubehalten.</p></div></div><button class="button" type="submit">Login-Daten speichern</button></form></details>` : H('<p class="hint">Nach der Installation änderst du deine Login-Daten direkt in WoltLab.</p>')}
        <details class="credentials"><summary>Datenbank-Zugangsdaten</summary><dl class="credential-grid">${row(t('Datenbankhost'), data.database.host)}${row(t('Datenbank'), data.database.name)}${row(t('Datenbanknutzer'), data.database.username)}${row(t('Datenbankpasswort'), data.database.password, true)}</dl></details>`;
      details.dataset.loaded = 'true';
    } catch (error) { content.textContent = error.message; }
    finally { delete details.dataset.loading; }
  }

  document.body.addEventListener('toggle', (event) => {
    const details = event.target;
    if (details instanceof HTMLDetailsElement && details.open) loadCredentials(details);
  }, true);

  async function uploadArchive(name, archive) {
    if (!archive || archive.size > 256 * 1024 * 1024) throw new Error(t('Bitte ein Installations-ZIP mit maximal 256 MiB auswählen.'));
    return api(H`/api/instances/${encodeURIComponent(name)}/archive`, { method: 'POST', headers: { 'Content-Type': 'application/zip' }, body: archive });
  }

  document.body.addEventListener('submit', async (event) => {
    const form = event.target;
    if (form.dataset.archiveFor) {
      event.preventDefault();
      if (operationInProgress) return;
      const submit = form.querySelector('button[type=submit]');
      beginOperation(submit, t('Installationsarchiv wird eingespielt …'), t('Wird eingespielt …'));
      try { await uploadArchive(form.dataset.archiveFor, form.querySelector('input[type=file]').files[0]); showResult(t('Archiv eingespielt. Prüfe die Login-Daten und klicke auf „Einrichten“.')); }
      catch (error) { output.textContent = error.message; showResult(error.message, true); }
      finally { endOperation(); await refresh(); }
      return;
    }
    if (!form.dataset.credentialsEdit) return;
    event.preventDefault();
    if (operationInProgress) return;
    const values = new FormData(form);
    const submit = form.querySelector('button[type=submit]');
    beginOperation(submit, t('Login-Daten werden gespeichert …'), t('Wird gespeichert …'));
    try {
      await api('/api/workbench', { method: 'POST', body: JSON.stringify({action:'save_credentials', name:form.dataset.credentialsEdit, username:values.get('username'), email:values.get('email'), password:values.get('password')}) });
      const details = form.closest('[data-credentials]');
      delete details.dataset.loaded;
      await loadCredentials(details);
      showResult(t('Login-Daten gespeichert. Klicke auf „Einrichten“, um WoltLab mit diesen Daten zu installieren.'));
    } catch (error) { showResult(error.message, true); output.textContent = error.message; }
    finally { endOperation(); }
  });

  async function initialize() {
    await Promise.allSettled([refresh(),loadSystem(),loadCatalog()]);
    try{const saved=JSON.parse(sessionStorage.getItem('wsc-language-view'));sessionStorage.removeItem('wsc-language-view');if(saved){showView(saved.view);if(saved.name&&knownProjects?.has(saved.name))await activateProject(saved.name,saved.tab||'overview');}}catch(_){}
    let serverJobs;try{serverJobs=await api('/api/jobs');if(serverJobs.updating)return;}catch(_){}
    let pending;
    try { pending = JSON.parse(localStorage.getItem('wsc-pending-install')); } catch (_) { try { localStorage.removeItem('wsc-pending-install'); } catch (_) {} }
    if (!pending?.id) {
      try {const data=serverJobs||await api('/api/jobs');const completed=finishedJobs();const job=data.items?.find(item=>!completed.includes(item.job_id)&&!(item.action==='acp_login'&&item.state!=='running')&&(item.action==='host_install'||knownProjects?.has(item.name)));if(job){pending={id:job.job_id,name:job.name,action:job.action};rememberJob(job);}} catch (_) { /* A previous server may not offer discovery. */ }
    }
    if (!pending?.id) return;
    if (pending.action!=='host_install' && pending.name && knownProjects && !knownProjects.has(pending.name)) { try {localStorage.removeItem('wsc-pending-install');} catch (_) {} return; }
    beginOperation(null, H`${pending.name}: ${pending.action==='install'?t('Einrichtungsstatus'):t('Vorgangsstatus')} wird geladen …`, '');
    let recoveredResult = null;
    try {
      const result = await trackJob(pending.id, pending.name, pending.action || 'install');
      recoveredResult = result;
      output.textContent = result.output || t('Vorgang abgeschlossen.');
      showResult(result.message);
    } catch (error) { output.textContent = error.message; showResult(error.message, true); }
    finally { endOperation(); await refresh(); }
    if(recoveredResult && pending.action==='acp_login')showResult(t('Bitte klicke erneut auf „ACP öffnen“, um ein neues Anmeldefenster zu öffnen.'));
    if(recoveredResult && pending.action==='host_install')await loadSystem();
    if(recoveredResult) { try { await presentToolResult(pending.action, pending.name, recoveredResult); } catch(error) { showResult(t('Der Vorgang wurde abgeschlossen, aber die Anleitung konnte nicht angezeigt werden. ')+error.message,true); } }
  }

  window.WorkbenchOperations={begin:beginOperation,end:endOperation,result:showResult,refresh,busy:()=>operationInProgress};
  initialize();
  window.setInterval(refresh, 12000);
})();
