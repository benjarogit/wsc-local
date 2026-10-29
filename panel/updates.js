// Release updates are separate from project jobs: the dashboard itself restarts.
(()=>{
  const {t,html:H}=window.WorkbenchLocale,{ask,icon}=window.WorkbenchUI,operations=window.WorkbenchOperations;
  const token=document.querySelector('meta[name=panel-token]').content,build=document.querySelector('meta[name=panel-version]').content;
  const status=document.getElementById('updates-status'),install=document.getElementById('updates-install'),check=document.getElementById('updates-check');
  let latest=null,watching=false;
  const escape=value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const stored=key=>{try{return localStorage.getItem(key)}catch{return null}};
  const save=(key,value)=>{try{value===null?localStorage.removeItem(key):localStorage.setItem(key,value)}catch{}};
  async function request(path,options={}){
    const response=await fetch(path,{cache:'no-store',...options,headers:{'Content-Type':'application/json','X-Panel-Token':token,'X-Workbench-Version':build}});
    const data=window.WorkbenchLocale.localizeResponse(await response.json());
    if(data.version_mismatch){const url=new URL(location.href);url.searchParams.set('ui',data.version);location.replace(url.href);const error=new Error(data.error);error.data=data;throw error;}
    if(!response.ok){const error=new Error(data.error||t('Update-Prüfung fehlgeschlagen.'));error.data=data;throw error;}
    return data;
  }
  function controls(busy){check.disabled=busy;install.disabled=busy||!latest?.can_apply;}
  function render(data){
    latest=data;
    const title=data.available?H`Version ${data.latest} ist verfügbar`:t('Deine Workbench ist aktuell.');
    status.innerHTML=H`<div class="system-summary ${data.available?'missing':'ready'}"><strong>${escape(title)}</strong><p>${t('Installiert')}: ${escape(data.current)} · ${t('Veröffentlicht')}: ${escape(data.latest)} · ${data.mode==='git'?t('Git-Installation'):t('ZIP-Installation')}</p>${data.available&&data.problems?.length?H`<ul>${data.problems.map(problem=>H`<li>${escape(t(problem))}</li>`).join('')}</ul>`:''}<p><a href="${escape(data.release_url)}" target="_blank" rel="noopener">Release auf GitHub öffnen ↗</a></p></div>`;
    if(data.runtime_mismatch)status.insertAdjacentHTML('beforeend',H`<div class="system-summary missing"><strong>${t('Dashboard-Neustart erforderlich')}</strong><p>${H(t('Die Programmdateien sind {0}, der laufende Prozess ist {1}. Starte das Dashboard neu, damit Anzeige und Update-Status übereinstimmen.'),escape(data.runtime_mismatch.files),escape(data.runtime_mismatch.running))}</p></div>`);
    if(['failed','rolled_back'].includes(data.state?.phase))status.insertAdjacentHTML('beforeend',H`<div class="result error"><strong>Letztes Update nicht abgeschlossen</strong><p>${escape(t(data.state.error||'Das Update wurde zurückgenommen. Die bisherige Version bleibt erhalten.'))}</p></div>`);
    document.getElementById('updates-notes').textContent=data.notes||t('Keine Release-Hinweise vorhanden.');
    document.getElementById('update-dot').hidden=!data.available;
    const notice=document.getElementById('update-notice');notice.hidden=!data.available||stored('wsc-update-dismissed')===data.latest||!document.getElementById('view-updates').hidden;
    document.getElementById('update-notice-title').textContent=title;
    controls(watching);
  }
  async function load(force=false){
    check.disabled=true;check.setAttribute('aria-busy','true');
    try{const data=await request('/api/updates'+(force?'?refresh=1':''));render(data);if(['checking','installing','installed','restarting','restoring'].includes(data.state?.phase))watch(data.state.target);}
    catch(error){latest={guide:error.data?.guide};install.disabled=true;status.innerHTML=H`<div class="system-summary missing"><strong>Update-Status nicht erreichbar</strong><p>${escape(error.message)}</p><p>Die Workbench bleibt nutzbar. Du kannst später erneut prüfen oder die Anleitung öffnen.</p></div>`;}
    finally{check.disabled=watching;check.removeAttribute('aria-busy');}
  }
  async function guide(){
    const data=latest?.guide;
    const fallback=t('Lade das aktuelle Release herunter. Beende das Dashboard und folge der Update-Anleitung in der README. Bewahre persönliche Dateien und den bisherigen Programmordner auf.');
    await ask({title:t('Workbench manuell aktualisieren'),description:latest?.current?H`Installiert: ${latest.current}`:'',body:H`<ol class="dialog-steps">${(data?.steps||[fallback]).map(step=>H`<li>${escape(t(step))}</li>`).join('')}</ol><p><a href="https://github.com/benjarogit/wsc-local/releases/latest" target="_blank" rel="noopener">Aktuelles Release öffnen ↗</a></p><p><a href="https://github.com/benjarogit/wsc-local#aktualisieren-und-alte-installation" target="_blank" rel="noopener">Update-Anleitung öffnen ↗</a></p>`,confirm:t('Verstanden'),cancel:''});
  }
  async function watch(target){
    if(watching)return;watching=true;save('wsc-pending-install',null);save('wsc-pending-update',target);controls(true);
    if(!operations.busy())operations.begin(null,t('Die Workbench wird aktualisiert …'),'');
    let last=null;
    try{
      for(let attempt=0;attempt<180;attempt++){
        await new Promise(resolve=>setTimeout(resolve,1000));
        try{last=await request('/api/updates/state');}catch{document.getElementById('operation-message').textContent=t('Dashboard startet neu. Verbindung wird wiederhergestellt …');continue;}
        if(['failed','rolled_back'].includes(last.phase)){save('wsc-pending-update',null);throw new Error(last.error||t('Das Update wurde zurückgenommen. Die bisherige Version bleibt erhalten.'));}
        document.getElementById('operation-message').textContent=['installed','restarting'].includes(last.phase)?t('Dashboard startet neu. Verbindung wird wiederhergestellt …'):t('Release wird geprüft und installiert …');
        if(last.phase==='done'&&last.target===target){
          const running=await request('/api/version');
          if(running.release_version!==target)continue;
          save('wsc-pending-update',null);
          try{sessionStorage.setItem('wsc-update-success',target)}catch{}
          const url=new URL(location.href);url.searchParams.set('ui',running.version);location.replace(url.href);return;
        }
        if(attempt>10&&!['checking','installing','installed','restarting','restoring'].includes(last.phase))throw new Error(t('Ein Update-Auftrag konnte nicht bestätigt werden. Prüfe den Status erneut.'));
      }
      throw new Error(t('Der Update-Status ist noch nicht abgeschlossen. Prüfe erneut oder öffne die Anleitung.'));
    }catch(error){operations.result(t(error.message),true);}
    finally{watching=false;operations.end();controls(false);}
  }
  async function apply(){
    if(operations.busy()){operations.result(t('Ein Vorgang läuft noch. Bitte warte bis zum Abschluss.'),true);return;}
    const target=latest.latest;
    const choice=await ask({title:H`Workbench auf ${target} aktualisieren?`,description:t('Das Update wird nach der Prüfsummenkontrolle installiert. Danach startet nur das Dashboard neu.'),body:H`<p>Vorher wird ein Wiederherstellungsstand angelegt. Schlägt der neue Dashboard-Start fehl, wird die bisherige Version wiederhergestellt.</p><p>Projektdateien, Datenbanken und Zugangsdaten bleiben erhalten. Lokale Codeänderungen verhindern ein automatisches Update.</p>`,confirm:t('Update installieren')});
    if(!choice)return;
    controls(true);
    try{await request('/api/updates/apply',{method:'POST',body:JSON.stringify({version:target,confirm:true})});}
    catch(error){if(error.data){operations.result(error.message,true);controls(false);return;}/* A lost response can still mean the update started. */}
    await watch(target);
  }
  document.addEventListener('workbench-view',()=>{if(latest)document.getElementById('update-notice').hidden=!latest.available||stored('wsc-update-dismissed')===latest.latest||!document.getElementById('view-updates').hidden;});
  check.addEventListener('click',()=>load(true));install.addEventListener('click',apply);document.getElementById('updates-guide').addEventListener('click',guide);
  document.getElementById('update-dismiss').addEventListener('click',()=>{save('wsc-update-dismissed',latest?.latest||'');document.getElementById('update-notice').hidden=true;});
  try{const success=sessionStorage.getItem('wsc-update-success');if(success){sessionStorage.removeItem('wsc-update-success');operations.result(H`Update auf ${success} erfolgreich installiert.`)}}catch{}
  const pending=stored('wsc-pending-update');if(pending)watch(pending);
  load();
  window.setInterval(()=>{if(!watching&&!operations.busy())load()},3600000);
})();
