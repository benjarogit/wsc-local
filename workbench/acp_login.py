"""Normal WoltLab login, transferred once to the user's local browser."""
from __future__ import annotations
import base64
import hashlib
import http.cookiejar
import json
import os
import re
import ssl
import time
import threading
import urllib.parse
import urllib.request
from cli import read_project, parse_env, project_status, _SetupFormParser, _post_setup_step, _IPv4HTTPHandler, _IPv4HTTPSHandler

TTL = 60


def local_origin(url: str) -> tuple[str, str, int]:
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or ''
    if parsed.scheme not in {'http', 'https'} or not (host in {'localhost', '127.0.0.1'} or re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+localhost',host)) or parsed.username or parsed.password:
        raise ValueError('ACP-Direktlogin ist nur für lokale Projektadressen verfügbar.')
    return parsed.scheme, host, parsed.port or (443 if parsed.scheme == 'https' else 80)


class LocalRedirects(urllib.request.HTTPRedirectHandler):
    def __init__(self, origin): self.origin = origin
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if local_origin(newurl) != self.origin:
            raise ValueError('Die ACP-Anmeldung wurde wegen einer abweichenden Zieladresse abgebrochen.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def authenticate(base: str, values: dict, user_agent: str) -> http.cookiejar.CookieJar:
    origin = local_origin(base)
    jar = http.cookiejar.CookieJar()
    context = ssl._create_unverified_context()  # Only a verified local instance is allowed above.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(jar), LocalRedirects(origin), _IPv4HTTPHandler(), _IPv4HTTPSHandler(context=context))
    url = base.rstrip('/') + '/acp/'
    with opener.open(urllib.request.Request(url, headers={'User-Agent': user_agent}), timeout=30) as response:
        page = response.read(4*1024*1024).decode('utf-8','replace');url=response.geturl()
    form = _SetupFormParser();form.feed(page)
    target = urllib.parse.urljoin(url, form.action)
    if local_origin(target) != origin: raise ValueError('Die ACP-Anmeldung verweist auf eine fremde Adresse.')
    fields = {**form.fields, 'username':values.get('WSC_ADMIN_USERNAME','admin'), 'password':values.get('WSC_ADMIN_PASSWORD',''), 'send':'1'}
    fields['t'] = next((urllib.parse.unquote(c.value) for c in jar if c.name=='XSRF-TOKEN'),fields.get('t',''))
    # Use the same User-Agent for every request; WoltLab sessions can bind it.
    class BrowserAgent(urllib.request.BaseHandler):
        def http_request(self, request): request.add_header('User-Agent',user_agent);return request
        https_request = http_request
    opener.add_handler(BrowserAgent())
    final, page = _post_setup_step(opener,target,fields,url)
    if local_origin(final)!=origin or 'rescue-mode' in final or re.search(r'<input\b[^>]*\btype=["\']password["\']',page,re.I) or not re.search(r'\bUser\.init\(\s*[1-9]\d*\s*,',page):
        raise ValueError('Der gespeicherte Adminzugang wurde von WoltLab nicht akzeptiert. Öffne das ACP manuell; bei geändertem Passwort oder Zwei-Faktor-Anmeldung ist eine normale Anmeldung nötig.')
    return jar


def prepare(name: str, user_agent: str) -> dict:
    cfg, root, secret = read_project(name)
    local_origin(cfg['url'])
    status = project_status(name)
    if not status.get('site_ready') or not status.get('running'):
        raise ValueError('Starte zuerst die vollständig eingerichtete WoltLab-Installation.')
    if not user_agent or len(user_agent)>1024 or '\r' in user_agent or '\n' in user_agent:
        raise ValueError('Ungültige Browserkennung.')
    jar = authenticate(cfg['url'],parse_env(secret),user_agent)
    cookies=[]
    for cookie in jar:
        if not re.fullmatch(r'[A-Za-z0-9_\-]+',cookie.name) or re.search(r'[\s;,\r\n]',cookie.value):
            raise ValueError('Die WoltLab-Sitzung konnte nicht sicher an den Browser übergeben werden.')
        rest={key.lower():value for key,value in cookie._rest.items()}
        cookies.append({'name':cookie.name,'value':cookie.value,'path':cookie.path or '/','domain':cookie.domain if cookie.domain_specified else '', 'secure':cookie.secure,'httponly':'httponly' in rest,'samesite':rest.get('samesite','Lax'),'expires':cookie.expires or 0})
    if not cookies: raise ValueError('WoltLab hat keine verwendbare Anmeldesitzung erstellt.')
    for stale in (root/'site').glob('wsc-local-acp-*.php'):
        try:
            if stale.stat().st_mtime < time.time()-TTL: stale.unlink(missing_ok=True)
        except FileNotFoundError:
            pass
    token=os.urandom(32).hex();filename='wsc-local-acp-'+os.urandom(16).hex()+'.php'
    payload=base64.b64encode(json.dumps(cookies).encode()).decode()
    expected_host=urllib.parse.urlsplit(cfg['url']).netloc
    script='''<?php
header('Cache-Control: no-store');
header('Referrer-Policy: no-referrer');
header('X-Frame-Options: DENY');
if (time() > EXPIRES) { @unlink(__FILE__); http_response_code(410); exit('Login link expired. Return to the Workbench.'); }
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST' || ($_SERVER['HTTP_HOST'] ?? '') !== EXPECTED_HOST || !hash_equals(TOKEN_HASH, hash('sha256', (string)($_POST['token'] ?? '')))) { http_response_code(403); exit('Invalid login request.'); }
if (!@unlink(__FILE__)) { http_response_code(410); exit('Login link already used.'); }
foreach (json_decode(base64_decode(COOKIES), true) as $cookie) {
    $options = ['expires'=>$cookie['expires'], 'path'=>$cookie['path'], 'secure'=>$cookie['secure'], 'httponly'=>$cookie['httponly'], 'samesite'=>$cookie['samesite']];
    if ($cookie['domain'] !== '') $options['domain'] = $cookie['domain'];
    setrawcookie($cookie['name'], $cookie['value'], $options);
}
header('Location: ./acp/', true, 303);
'''
    for key,value in {'EXPIRES':str(int(time.time())+TTL),'EXPECTED_HOST':json.dumps(expected_host),'TOKEN_HASH':json.dumps(hashlib.sha256(token.encode()).hexdigest()),'COOKIES':json.dumps(payload)}.items():script=script.replace(key,value)
    target=root/'site'/filename
    descriptor=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(descriptor,'w',encoding='utf-8') as stream:
        stream.write(script)
    cleanup = threading.Timer(TTL + 2, lambda: target.unlink(missing_ok=True))
    cleanup.daemon = True
    cleanup.start()
    return {'url':cfg['url'].rstrip('/')+'/'+filename,'token':token,'expires_in':TTL,'manual_url':cfg['url'].rstrip('/')+'/acp/'}
