const {test,before,after}=require('node:test');
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');const os=require('node:os');const path=require('node:path');const net=require('node:net');
let browser,server,base,temp;
before(async()=>{
 temp=fs.mkdtempSync(path.join(os.tmpdir(),'wsc-ui-'));
 const socket=net.createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));base=`http://127.0.0.1:${port}`;
 server=spawn(process.env.PYTHON || (process.platform==='win32'?'python':'python3'),['scripts/panel_server.py'],{cwd:path.resolve(__dirname,'../..'),env:{...process.env,PANEL_PORT:String(port),WSC_LOCAL_HOME:temp,XDG_CONFIG_HOME:temp},stdio:'ignore'});
 let ready=false;for(let i=0;i<100;i++){try{if((await fetch(base+'/api/version')).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,50));}assert.ok(ready,'Isolated dashboard server must start');
 browser=await chromium.launch({headless:true,...(process.env.WSC_TEST_BROWSER?{executablePath:process.env.WSC_TEST_BROWSER}:{})});
});
after(async()=>{await browser?.close();server?.kill();if(server)await new Promise(r=>{if(server.exitCode!==null)return r();server.once('exit',r)});fs.rmSync(temp,{recursive:true,force:true});});
async function fixture(options={}){
 const context=await browser.newContext({viewport:{width:1440,height:1000},colorScheme:'light',locale:options.browserLocale || 'de-DE'});const page=await context.newPage();const calls=[],errors=[];let removed=false,recovery=false;const jobs=new Map();
 page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>{errors.push('Native browser dialog: '+d.type());d.dismiss();});
 await page.route('**/api/**',async route=>{
  const req=route.request(),url=new URL(req.url());let data={};let status=200;
  if(url.pathname==='/api/instances')data={items:removed?[]:[{name:'e2e-project',suite:'6.3',php:'8.5',webserver:'nginx-php-fpm',database:'mariadb',url:'https://e2e-project.localhost:8081',running:!options.prepared,site_ready:!options.prepared,files_available:!options.prepared,core_available:!!options.prepared,experimental:true,tls_enabled:true,recovery_enabled:recovery,installation:{state:options.prepared?'prepared':'ready'},services:[{name:'web',state:'running'},{name:'php',state:'running'},{name:'database',state:'running'}]}]};
  else if(url.pathname==='/api/system')data={ready:!options.missingHost,host:{label:'Test Linux',architecture:'x64'},checks:[],installation:{supported:true,steps:['Install packages'],command:'bash ./setup.sh --install-deps'}};
  else if(url.pathname==='/api/catalog')data={profiles:[]};
  else if(url.pathname.endsWith('/snapshots'))data={items:[{name:'20261028_120000'}]};
  else if(url.pathname.endsWith('/exports'))data={items:[{name:'e2e-project-20261028_120000.tar.gz',size:1024}]};
  else if(url.pathname.endsWith('/acp-login')||url.pathname==='/api/system/install'){
   const action=url.pathname.endsWith('/acp-login')?'acp_login':'host_install';calls.push({action});const id=String(jobs.size+1).padStart(32,'0');jobs.set(id,{action,polls:0});data={job_id:id,name:'e2e-project',action};status=202;
  }else if(url.pathname==='/api/workbench'){
   const body=req.postDataJSON();calls.push(body);
   if(body.action==='uploads_preview')data={ok:true,output:'upload_max_filesize = 256M\npost_max_size = 320M'};
   else{const id=String(jobs.size+1).padStart(32,'0');jobs.set(id,{action:body.action,polls:0});if(options.dropResponse){options.dropResponse=false;return route.abort('connectionaborted');}data={job_id:id,name:body.name,action:body.action};status=202;}
  }else if(url.pathname==='/api/jobs')data={items:[...jobs.entries()].map(([job_id,job])=>({job_id,action:job.action,name:'e2e-project',state:job.polls>=2?'done':'running'}))};
  else if(url.pathname.startsWith('/api/jobs/')){
   const job=jobs.get(url.pathname.split('/').pop());job.polls++;const done=job.polls>=2;
   if(done&&job.action==='remove')removed=true;if(done&&job.action==='recovery_install')recovery=true;if(done&&job.action==='recovery_remove')recovery=false;
   data={name:'e2e-project',action:job.action,state:done?'done':'running',stage:'Sicherung und Werkzeug werden vorbereitet',output:'Sicherung: /isolated/snapshot\nhttps://manual.woltlab.com/de/',error:'',result:job.action==='acp_login'?{url:'https://e2e-project.localhost:8081/wsc-local-acp-test.php',token:'one-use-token'}:{completed:true}};if(done&&job.action==='host_install')options.missingHost=false;if(options.failAcp&&job.action==='acp_login'){data.state='failed';data.error='Admin password changed';}
  }else if(url.pathname.endsWith('/recovery'))data={url:'https://e2e-project.localhost:8081/wsc-recovery.php',directory:'/isolated/project/site'};
  else if(url.pathname.endsWith('/credentials'))data={admin:{username:options.username||'admin',email:'admin@example.test',password:options.password||'test-password'},database:{host:'database',name:'woltlab',username:'wsc',password:'test-db-password'}};
  else return route.fulfill({status:404,contentType:'application/json',body:JSON.stringify({error:'Unmocked route '+url.pathname})});
  return route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
 });
 await page.goto(base,{waitUntil:'networkidle'});const card=page.locator('[data-project=e2e-project]');await card.waitFor();await card.locator('[data-project-open]').first().click();await card.locator('[data-tab=tools]').click();
 return {context,page,card,calls,errors};
}
async function completed(page){await page.waitForFunction(()=>!document.querySelector('#operation-result').hidden);assert.equal(await page.locator('#operation-result').evaluate(e=>e.classList.contains('error')),false);await page.waitForFunction(()=>document.querySelector('#operation-status').hidden);}

test('contextual help, keyboard dismissal, and theme icons persist',async()=>{const {context,page,errors}=await fixture();await page.locator('[data-info=recovery]').click();await page.locator('#action-dialog').waitFor({state:'visible'});assert.match(await page.locator('#action-heading').innerText(),/Recovery/);await page.keyboard.press('Escape');assert.equal(await page.locator('[data-info=recovery]').evaluate(e=>e===document.activeElement),true);assert.equal(await page.locator('.theme-switch select, .header-controls [data-info=theme]').count(),0);assert.equal(await page.locator('.theme-switch button').count(),3);await page.locator('[data-color-mode=dark]').click();assert.equal(await page.locator('[data-color-mode=dark]').getAttribute('aria-pressed'),'true');assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');await page.reload({waitUntil:'networkidle'});assert.equal(await page.locator('[data-color-mode=dark]').getAttribute('aria-pressed'),'true');await page.locator('[data-color-mode=system]').click();await page.emulateMedia({colorScheme:'light'});await page.waitForFunction(()=>document.documentElement.dataset.theme==='light');assert.equal(await page.locator('html').getAttribute('data-theme'),'light');await page.emulateMedia({colorScheme:'dark'});await page.waitForFunction(()=>document.documentElement.dataset.theme==='dark');assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');await page.locator('[data-color-mode=light]').focus();await page.keyboard.press('Enter');assert.equal(await page.locator('html').getAttribute('data-theme'),'light');await page.setViewportSize({width:390,height:844});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);assert.deepEqual(errors,[]);await context.close();});

for(const action of ['guide_domain','guide_directory','guide_migration','recovery_install','recovery_remove'])test(`${action}: modal confirmation, background status, explained result`,async()=>{const {context,page,card,calls,errors}=await fixture();if(action==='recovery_remove'){await card.locator('[data-action=recovery_install]').click();await page.locator('#action-accept').click();await completed(page);await page.locator('#action-dialog').waitFor({state:'visible'});await page.locator('#action-accept').click();}
 await card.locator(`[data-action=${action}]`).click();await page.locator('#action-dialog').waitFor({state:'visible'});await page.locator('#action-cancel').click();assert.equal(calls.filter(c=>c.action===action).length,0);
 await card.locator(`[data-action=${action}]`).click();await page.locator('#action-accept').click();await page.locator('#operation-status').waitFor({state:'visible'});if(action==='guide_domain')await page.reload({waitUntil:'networkidle'});await completed(page);
 if(action!=='recovery_remove'){await page.locator('#action-dialog').waitFor({state:'visible'});assert.ok((await page.locator('#action-description').innerText()).length>40);if(action==='guide_migration')assert.equal(await page.locator('#action-content a[download]').count(),1);await page.locator('#action-accept').click();}
 assert.equal(calls.filter(c=>c.action===action).length,1);assert.deepEqual(errors,[]);await context.close();});

test('delete requires matching project name in the modal',async()=>{const {context,page,card,calls,errors}=await fixture();await card.locator('[data-action=remove]').click();await page.locator('#action-input').fill('wrong');await page.locator('#action-accept').click();assert.equal(await page.locator('#action-input-error').isVisible(),true);assert.equal(calls.length,0);await page.locator('#action-input').fill('e2e-project');await page.locator('#action-accept').click();await completed(page);await card.waitFor({state:'detached'});assert.equal(calls[0].action,'remove');assert.deepEqual(errors,[]);await context.close();});

test('upload dialog validates size and shows a separate change preview',async()=>{const {context,page,card,calls,errors}=await fixture();await card.locator('[data-action=uploads]').click();await page.locator('#action-input').fill('invalid');await page.locator('#action-accept').click();assert.equal(await page.locator('#action-input-error').isVisible(),true);assert.equal(calls.length,0);await page.locator('#action-input').fill('256M');await page.locator('#action-accept').click();await page.locator('.change-preview').waitFor();assert.match(await page.locator('.change-preview').innerText(),/upload_max_filesize/);await page.locator('#action-accept').click();await page.waitForFunction(()=>document.querySelector('#operation-status').hidden);assert.deepEqual(calls.map(c=>c.action),['uploads_preview','uploads_apply']);assert.deepEqual(errors,[]);await context.close();});

 test('reload discovers a started tool even when its initial response was lost',async()=>{const {context,page,card,errors}=await fixture({dropResponse:true});await card.locator('[data-action=guide_directory]').click();await page.locator('#action-accept').click();await page.waitForFunction(()=>document.querySelector('#operation-result').classList.contains('error'));await page.reload({waitUntil:'networkidle'});await page.locator('#action-dialog').waitFor({state:'visible'});assert.match(await page.locator('#action-heading').innerText(),/Sicherung erstellt/);await page.locator('#action-accept').click();assert.deepEqual(errors,[]);await context.close();});

test('German is default; English persists and leaves credentials untouched',async()=>{
 const username='Sicherung erstellen',password='Projekt vorbereiten " <&';
 const {context,page,card,calls,errors}=await fixture({browserLocale:'en-US',username,password});
 assert.equal(await page.locator('html').getAttribute('lang'),'de');
 await page.locator('#language-toggle').click();await page.waitForFunction(()=>document.documentElement.lang==='en');await page.waitForLoadState('networkidle');
 assert.equal(await page.locator('#page-title').innerText(),'Your WoltLab projects');
 await card.locator('[data-tab=tools]').waitFor({state:'visible'});
 assert.match(await card.locator('[data-panel=tools]').innerText(),/Diagnostics and settings/);
 await card.locator('[data-action=guide_domain]').click();assert.equal(await page.locator('#action-heading').innerText(),'Prepare a domain change');await page.locator('#action-cancel').click();assert.equal(calls.length,0);
 await card.locator('[data-tab=credentials]').click();await card.locator('.credential-grid').first().waitFor();
 assert.equal(await card.locator('.credential-grid dd span').first().innerText(),username);
 assert.equal(await card.locator('.credential-value input').first().inputValue(),password);
 await page.reload({waitUntil:'networkidle'});assert.equal(await page.locator('html').getAttribute('lang'),'en');
 await page.locator('#language-toggle').click();await page.waitForFunction(()=>document.documentElement.lang==='de');assert.equal(await page.locator('#page-title').innerText(),'Deine WoltLab-Projekte');assert.deepEqual(errors,[]);await context.close();
});

test('language is an icon switch with an explicit saved state',async()=>{const {context,page}=await fixture();const button=page.locator('#language-toggle');assert.equal(await button.getAttribute('role'),'switch');assert.equal(await button.getAttribute('aria-checked'),'false');assert.equal(await button.locator('use').getAttribute('href'),'/icons.svg#globe');await button.click();await page.waitForFunction(()=>document.documentElement.lang==='en');assert.equal(await button.getAttribute('aria-checked'),'true');await context.close();});

test('ACP click hands a one-use token to a new tab by POST',async()=>{const {context,page,card,errors}=await fixture();let posted=null;await context.route('**/wsc-local-acp-test.php',async route=>{posted=route.request();await route.fulfill({body:'ACP session received',contentType:'text/plain'});});const popupPromise=page.waitForEvent('popup');await card.locator('[data-action=acp_login]').click();const popup=await popupPromise;await popup.waitForURL('**/wsc-local-acp-test.php');await popup.waitForLoadState();assert.equal(posted.method(),'POST');assert.equal(posted.postData(),'token=one-use-token');assert.equal(new URL(posted.url()).search,'');assert.deepEqual(errors,[]);await context.close();});

test('failed ACP login explains the normal manual fallback',async()=>{const {context,page,card,errors}=await fixture({failAcp:true});await card.locator('[data-action=acp_login]').click();await page.locator('#action-dialog').waitFor({state:'visible'});assert.match(await page.locator('#action-description').innerText(),/password changed/);assert.equal(await page.locator('#action-content a').getAttribute('href'),'https://e2e-project.localhost:8081/acp/');assert.deepEqual(errors,[]);await context.close();});

test('missing prerequisites require preview before launching the terminal',async()=>{const {context,page,calls,errors}=await fixture({missingHost:true});await page.locator('.app-nav [data-view=system]').click();await page.locator('[data-action=host_install]').click();assert.match(await page.locator('#action-content').innerText(),/Install packages/);await page.locator('#action-cancel').click();assert.equal(calls.length,0);await page.locator('[data-action=host_install]').click();await page.locator('#action-accept').click();await completed(page);assert.equal(calls[0].action,'host_install');assert.equal(await page.locator('[data-action=host_install]').count(),0);assert.deepEqual(errors,[]);await context.close();});

for(const language of ['de','en'])test(`automatic installation passes the selected ${language} dashboard language`,async()=>{const {context,page,card,calls,errors}=await fixture({prepared:true,browserLocale:'en-US'});if(language==='en'){await page.locator('#language-toggle').click();await page.waitForFunction(()=>document.documentElement.lang==='en');await page.waitForLoadState('networkidle');}await card.locator('[data-tab=credentials]').click();await card.locator('[data-action=install]').click();await page.locator('#operation-status').waitFor({state:'visible'});if(language==='en'){await page.locator('#language-toggle').click();await page.waitForFunction(()=>document.documentElement.lang==='de');await page.waitForLoadState('networkidle');}await completed(page);const install=calls.find(call=>call.action==='install');assert.ok(install);assert.equal(install.language,language);assert.equal(calls.filter(call=>call.action==='install').length,1);assert.deepEqual(errors,[]);await context.close();});
