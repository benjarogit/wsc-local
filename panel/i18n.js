// Catalog lookups apply only to authored UI copy. Interpolated values stay untouched.
(() => {
  const key='wsc-ui-language';
  let language='de';
  try {if(localStorage.getItem(key)==='en')language='en';}catch(_){}
  const requested=new URL(window.location.href).searchParams.get('lang');
  if(['de','en'].includes(requested))language=requested;
  const english=window.WorkbenchEnglish;
  function text(source) {
    if(language!=='en'||typeof source!=='string')return source;
    const match=source.match(/^(\s*)([\s\S]*?)(\s*)$/);
    const original=match[2];
    let translated=english[original];
    if(translated===undefined){
      if(original.startsWith('Linux-Container · Docker '))translated=original.replace('Linux-Container','Linux containers');
      else if(/^.+ bauen und starten – beim ersten Mal kann das mehrere Minuten dauern$/.test(original))translated='Building and starting '+original.split(' bauen und starten')[0]+' – the first run can take several minutes';
      else if(original.startsWith('Installationsschritt: '))translated='Installation step: '+text(original.slice(21));
      else if(original.startsWith('WoltLab-Core installieren ('))translated=original.replace('WoltLab-Core installieren','Installing WoltLab Core');
      else if(original.startsWith('lokale Browser-/HTTPS-Prüfung ('))translated=original.replace('lokale Browser-/HTTPS-Prüfung','Local browser/HTTPS check');
      if(/^(\{\d+\}) kopieren$/.test(original))translated=original.replace(/^(\{\d+\}) kopieren$/,'Copy $1');
      if(/^(\{\d+\}) verwalten$/.test(original))translated=original.replace(/^(\{\d+\}) verwalten$/,'Manage $1');
      const prefix=original.match(/^(\{\d+\})+(.*)$/s);
      if(prefix&&english[prefix[2]]!==undefined)translated=prefix[1]+english[prefix[2]];
    }
    return translated===undefined?source:match[1]+translated+match[3];
  }
  function markup(source) {
    if(language!=='en')return source;
    return source.split(/(<[^>]+>)/g).map(part=>part.startsWith('<')
      ? part.replace(/((?:aria-label|title|placeholder)\s*=\s*)(["'])(.*?)\2/g,(_,prefix,quote,value)=>prefix+quote+text(value)+quote).replaceAll('https://manual.woltlab.com/de/','https://manual.woltlab.com/en/')
      : text(part)).join('');
  }
  function html(parts,...values) {
    const source=typeof parts==='string'?parts:parts.map((part,i)=>part+(i<values.length?`{${i}}`:'')).join('');
    const translated=source.includes('<')?markup(source):text(source);
    return translated.replace(/\{(\d+)\}/g,(marker,index)=>index<values.length?String(values[index]):marker);
  }
  function localizeResponse(data) {
    if(language!=='en'||!data||typeof data!=='object')return data;
    if(Array.isArray(data)){data.forEach(localizeResponse);return data;}
    for(const [field,value]of Object.entries(data)){
      if(['error','message','label','help','detail','status_error','stage'].includes(field)&&typeof value==='string')data[field]=text(value);
      else if(value&&typeof value==='object')localizeResponse(value);
    }
    return data;
  }
  document.documentElement.lang=language;
  // This script runs before the application renders any project or credentials.
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  let node;while((node=walker.nextNode())){
    if(node.parentElement.closest('script,style,code,pre'))continue;
    node.nodeValue=text(node.nodeValue);
  }
  for(const element of document.querySelectorAll('[aria-label],[title],[placeholder]')){
    for(const attribute of ['aria-label','title','placeholder'])if(element.hasAttribute(attribute))element.setAttribute(attribute,text(element.getAttribute(attribute)));
  }
  if(language==='en')document.querySelectorAll('a[href^="https://manual.woltlab.com/de/"]').forEach(link=>link.href=link.href.replace('/de/','/en/'));
  const button=document.getElementById('language-toggle');
  button.textContent=language==='de'?'EN':'DE';
  button.title=language==='de'?'English':'Deutsch';
  button.setAttribute('aria-label',language==='de'?'Switch to English':'Auf Deutsch umschalten');
  button.addEventListener('click',()=>{
    try{
      localStorage.setItem(key,language==='de'?'en':'de');
      const open=document.querySelector('.project-drawer:not([hidden])')?.closest('[data-project]');
      sessionStorage.setItem('wsc-language-view',JSON.stringify({view:document.querySelector('.app-nav [aria-current=page]')?.dataset.view||'projects',name:open?.dataset.project,tab:open?.querySelector('[aria-selected=true]')?.dataset.tab}));
    }catch(_){}
    const url=new URL(window.location.href);url.searchParams.set('lang',language==='de'?'en':'de');window.location.assign(url.href);
  });
  window.WorkbenchLocale={language,t:text,html,localizeResponse};
})();
