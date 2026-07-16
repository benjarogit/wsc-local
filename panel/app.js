(() => {
  const TOKEN = document.querySelector('meta[name="panel-token"]')?.content || '';
  const GITHUB = 'https://github.com/benjarogit/wsc-local';
  const lastLine = document.getElementById('last-line');
  const toastArea = document.getElementById('toast-area');
  const busyBar = document.getElementById('busy-bar');
  const feed = document.getElementById('activity-feed');
  let confirmResolve = null;
  let confirmMode = 'simple';
  let actionBusy = false;
  let activity = [];
  let lang = localStorage.getItem('wsc-panel-lang') || 'de';
  if (lang !== 'de' && lang !== 'en') lang = 'de';

  function t(key) {
    const pack = (window.WSC_I18N && window.WSC_I18N[lang]) || window.WSC_I18N.de;
    return (pack && pack[key] != null) ? pack[key] : key;
  }

  function actionLabel(action) {
    const pack = (window.WSC_I18N && window.WSC_I18N[lang]) || window.WSC_I18N.de;
    return (pack.actionLabels && pack.actionLabels[action]) || action;
  }

  function applyI18n() {
    document.documentElement.lang = lang;
    document.title = t('title');
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      if (key) el.textContent = t(key);
    });
    document.querySelectorAll('[data-i18n-title]').forEach((el) => {
      const key = el.getAttribute('data-i18n-title');
      if (key) el.title = t(key);
    });
    document.querySelectorAll('[data-i18n-aria]').forEach((el) => {
      const key = el.getAttribute('data-i18n-aria');
      if (key) el.setAttribute('aria-label', t(key));
    });
    document.getElementById('lang-de').classList.toggle('active', lang === 'de');
    document.getElementById('lang-en').classList.toggle('active', lang === 'en');
    renderFeed();
  }

  function setLang(next) {
    lang = next === 'en' ? 'en' : 'de';
    localStorage.setItem('wsc-panel-lang', lang);
    applyI18n();
    refresh().catch(() => {});
  }

  document.getElementById('lang-de').addEventListener('click', () => setLang('de'));
  document.getElementById('lang-en').addEventListener('click', () => setLang('en'));

  function setLast(msg) {
    lastLine.textContent = msg;
  }

  function friendlyNetError(err) {
    const m = String(err?.message || err || '');
    if (/NetworkError|Failed to fetch|network/i.test(m)) return t('netError');
    return m;
  }

  function stripAnsi(s) {
    return String(s || '').replace(/\x1b\[[0-9;]*m/g, '');
  }

  function summarizeOutput(raw) {
    const text = stripAnsi(raw).trim();
    if (!text) return { lines: [], checks: [], level: 'ok' };
    const lines = text.split(/\n+/).map((l) => l.trim()).filter(Boolean);
    const checks = [];
    let level = 'ok';
    const bullet = [];

    for (const line of lines) {
      const clean = line.replace(/^[→✓✗⚠●○]\s*/, '').replace(/^[-*]\s*/, '');
      if (/✓|OK|erreichbar|bereit|fertig|Gestartet|Läuft|pass/i.test(line) && !/nicht|fehl|warn/i.test(line)) {
        checks.push({ label: clean.slice(0, 80), kind: 'pass' });
      } else if (/✗|fehl|Fehler|fail|error/i.test(line)) {
        checks.push({ label: clean.slice(0, 80), kind: 'fail' });
        level = 'error';
      } else if (/⚠|warn|Hinweis|nicht erreichbar|gestoppt|fehlt/i.test(line)) {
        checks.push({ label: clean.slice(0, 80), kind: 'warn' });
        if (level === 'ok') level = 'warn';
      }
    }

    // Kurzfassung: letzte sinnvolle Zeilen
    const interesting = lines.filter((l) =>
      /✓|✗|⚠|OK|Fehler|fertig|Hinweis|Website|MySQL|WoltLab|Docker|TLS|php|Mail/i.test(l)
    );
    const pick = (interesting.length ? interesting : lines).slice(-6);
    for (const l of pick) bullet.push(l.replace(/^[→]\s*/, '').slice(0, 120));

    // Logs: Dienst-Blöcke
    if (/^=== /.test(text)) {
      const sections = text.split(/=== /).filter(Boolean).slice(0, 6);
      return {
        lines: sections.map((s) => {
          const title = s.split('\n')[0].replace(/=+/g, '').trim();
          const body = s.split('\n').slice(1).filter(Boolean);
          return body.length ? `${title}: ${body.length} ${lang === 'de' ? 'Zeilen' : 'lines'}` : title;
        }),
        checks: sections.map((s) => {
          const title = s.split('\n')[0].replace(/=+/g, '').trim();
          const kind = /gestoppt|stopped/i.test(title) ? 'warn' : 'pass';
          return { label: title.slice(0, 60), kind };
        }),
        level: /gestoppt|stopped/i.test(text) ? 'warn' : 'ok',
      };
    }

    return {
      lines: bullet.slice(0, 5),
      checks: checks.slice(0, 12),
      level,
    };
  }

  function renderFeed() {
    if (!activity.length) {
      feed.innerHTML = `<div class="activity-empty">${esc(t('noActivity'))}</div>`;
      return;
    }
    feed.innerHTML = activity.map((item, idx) => {
      const icons = {
        ok: 'fa-check', warn: 'fa-exclamation', error: 'fa-times', running: 'fa-spinner fa-spin',
      };
      const icon = icons[item.level] || icons.ok;
      const checks = (item.checks || []).map((c) =>
        `<span class="act-check ${esc(c.kind)}">${esc(c.label)}</span>`
      ).join('');
      const summary = (item.lines || []).length
        ? `<ul class="act-summary">${item.lines.map((l) => `<li>${esc(l)}</li>`).join('')}</ul>`
        : '';
      const detailsId = `act-det-${idx}`;
      const hasRaw = !!(item.raw && item.raw.trim());
      return `<article class="act-card ${esc(item.level)}" data-idx="${idx}">
        <div class="act-head">
          <div class="act-title">
            <span class="act-icon" aria-hidden="true"><i class="fas ${icon}"></i></span>
            <span>${esc(item.title)}</span>
          </div>
          <div class="act-time">${esc(item.time)}</div>
        </div>
        ${item.message ? `<p class="hint mb-0 mt-1">${esc(item.message)}</p>` : ''}
        ${checks ? `<div class="act-checks">${checks}</div>` : ''}
        ${summary}
        ${hasRaw ? `<button type="button" class="act-toggle" data-toggle-details="${detailsId}">${esc(t('details'))}</button>
          <pre class="act-details d-none" id="${detailsId}">${esc(item.raw)}</pre>` : ''}
      </article>`;
    }).join('');
  }

  function pushActivity(entry) {
    const sum = summarizeOutput(entry.raw || '');
    activity.unshift({
      id: Date.now() + Math.random(),
      title: entry.title,
      message: entry.message || '',
      level: entry.level || sum.level || 'ok',
      lines: entry.lines || sum.lines,
      checks: entry.checks || sum.checks,
      raw: entry.raw || '',
      time: new Date().toLocaleTimeString(lang === 'de' ? 'de-DE' : 'en-GB'),
    });
    activity = activity.slice(0, 25);
    renderFeed();
  }

  function updateRunningActivity(title, message) {
    const existing = activity.find((a) => a.level === 'running' && a.title === title);
    if (existing) {
      existing.message = message;
      existing.time = new Date().toLocaleTimeString(lang === 'de' ? 'de-DE' : 'en-GB');
    } else {
      activity.unshift({
        id: Date.now(),
        title,
        message,
        level: 'running',
        lines: [],
        checks: [],
        raw: '',
        time: new Date().toLocaleTimeString(lang === 'de' ? 'de-DE' : 'en-GB'),
      });
      activity = activity.slice(0, 25);
    }
    renderFeed();
  }

  function finishRunning(title, result) {
    activity = activity.filter((a) => !(a.level === 'running' && a.title === title));
    pushActivity({ title, ...result });
  }

  feed.addEventListener('click', (ev) => {
    const btn = ev.target.closest('[data-toggle-details]');
    if (!btn) return;
    const id = btn.getAttribute('data-toggle-details');
    const pre = document.getElementById(id);
    if (!pre) return;
    const open = pre.classList.toggle('d-none') === false;
    btn.textContent = open ? t('hideDetails') : t('details');
  });

  $('#confirmOk').on('click', () => {
    if (confirmMode === 'reset') {
      const typed = (document.getElementById('confirmInput').value || '').trim();
      if (typed !== 'RESET') {
        toast(t('typeReset'), false);
        return;
      }
      const purge = document.getElementById('confirmPurge').checked;
      $('#confirmModal').modal('hide');
      if (confirmResolve) confirmResolve({ ok: true, purge });
      confirmResolve = null;
      return;
    }
    $('#confirmModal').modal('hide');
    if (confirmResolve) confirmResolve(true);
    confirmResolve = null;
  });
  $('#confirmModal').on('hidden.bs.modal', () => {
    if (confirmResolve) {
      confirmResolve(confirmMode === 'reset' ? { ok: false } : false);
      confirmResolve = null;
    }
    confirmMode = 'simple';
    document.getElementById('confirmExtra').classList.add('d-none');
    document.getElementById('confirmInput').value = '';
    document.getElementById('confirmPurge').checked = false;
  });
  document.getElementById('clear-out').addEventListener('click', () => {
    activity = [];
    renderFeed();
    setLast(t('ready'));
  });

  function confirm(msg) {
    confirmMode = 'simple';
    document.getElementById('confirmTitle').textContent = t('confirmTitle');
    document.getElementById('confirmBody').textContent = msg;
    document.getElementById('confirmExtra').classList.add('d-none');
    document.getElementById('confirmOk').textContent = t('continue');
    document.getElementById('confirmOk').className = 'btn btn-danger';
    $('#confirmModal').modal('show');
    return new Promise((r) => { confirmResolve = r; });
  }

  function confirmReset() {
    confirmMode = 'reset';
    document.getElementById('confirmTitle').textContent = t('resetTitle');
    document.getElementById('confirmBody').textContent = t('resetBody');
    document.getElementById('confirmExtra').classList.remove('d-none');
    document.getElementById('confirmOk').textContent = t('resetFinal');
    document.getElementById('confirmOk').className = 'btn btn-danger';
    $('#confirmModal').modal('show');
    setTimeout(() => document.getElementById('confirmInput').focus(), 300);
    return new Promise((r) => { confirmResolve = r; });
  }

  function toast(msg, ok = true) {
    const el = document.createElement('div');
    el.className = `alert alert-${ok ? 'success' : 'danger'} py-2 px-3 mb-2 shadow-sm`;
    el.textContent = msg;
    toastArea.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  }

  async function api(path, opts = {}) {
    let res;
    try {
      res = await fetch(path, {
        ...opts,
        headers: {
          'Content-Type': 'application/json',
          'X-Panel-Token': TOKEN,
          ...(opts.headers || {}),
        },
      });
    } catch (e) {
      throw new Error(friendlyNetError(e));
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  }

  function setBusy(busy) {
    actionBusy = busy;
    busyBar.classList.toggle('on', busy);
    busyBar.setAttribute('aria-hidden', busy ? 'false' : 'true');
    document.querySelectorAll('[data-action]').forEach((b) => { b.disabled = busy; });
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function localizeHealth(s) {
    const h = s.health || {};
    const f = s.flags || {};
    if (s.busy && s.busy.disrupts) {
      return {
        level: 'warn',
        title: `${t('healthWorking')}: ${s.busy.label || ''}`,
        hint: s.busy.hint || t('healthWorkingHint'),
        details: h.details || [],
      };
    }
    if (h.level === 'ok') {
      return { level: 'ok', title: t('healthOk'), hint: t('healthOkHint'), details: [] };
    }
    if ((f.services_up || 0) === 0 && !s.running) {
      return {
        level: 'warn',
        title: t('healthStopped'),
        hint: t('healthStoppedHint'),
        details: h.details || [],
      };
    }
    if (h.level === 'error') {
      return {
        level: 'error',
        title: t('healthError'),
        hint: t('healthErrorHint'),
        details: h.details || [],
      };
    }
    return {
      level: 'warn',
      title: t('healthWarn'),
      hint: t('healthWarnHint'),
      details: h.details || [],
    };
  }

  function renderStatus(s) {
    const h = localizeHealth(s);
    const f = s.flags || {};
    const level = h.level || 'warn';
    const card = document.getElementById('status-card');
    const icons = { ok: 'fa-check', warn: 'fa-exclamation', error: 'fa-times' };
    card.className = `status-card ${level}`;
    card.querySelector('.mark').innerHTML = `<i class="fas ${icons[level] || icons.warn}"></i>`;
    document.getElementById('status-title-text').textContent = h.title || t('loading');
    document.getElementById('status-hint').textContent = h.hint || '';

    const snap = s.last_snapshot;
    const snapTxt = snap
      ? `${t('backupLabel')}: ${snap.relative || snap.label}${s.snapshot_count > 1 ? ` (${s.snapshot_count})` : ''}`
      : t('noBackupYet');

    document.getElementById('flag-row').innerHTML = [
      [t('docker'), !!f.docker],
      [t('https'), !!f.https],
      [t('siteFlag'), !!f.site],
      [`${t('services')} ${f.services_up ?? 0}/${f.services_total ?? 0}`, (f.services_up || 0) === (f.services_total || 0) && (f.services_up || 0) > 0],
    ].map(([label, on]) =>
      `<span class="flag ${on ? 'on' : 'off'}"><span class="dot" aria-hidden="true"></span>${esc(label)}</span>`
    ).join('') + `<span class="flag"><span class="dot" style="background:#64748b" aria-hidden="true"></span>${esc(snapTxt)}</span>`;

    document.getElementById('service-boxes').innerHTML = (s.services || []).map((x) =>
      `<span class="svc-chip ${x.running ? 'up' : 'down'}" title="${esc(x.name)}">
        <span class="dot" aria-hidden="true"></span>${esc(x.label || x.name)}
      </span>`
    ).join('');

    const det = document.getElementById('status-details');
    const details = (h.details || []).filter(Boolean);
    if (details.length && level !== 'ok') {
      det.classList.remove('d-none');
      det.innerHTML = details.map((d) => `<li>${esc(d)}</li>`).join('');
    } else {
      det.classList.add('d-none');
      det.innerHTML = '';
    }
  }

  async function refresh() {
    const s = await api('/api/status');
    document.getElementById('meta-line').textContent =
      `WoltLab ${s.version || '—'} · ${s.project || 'wsc-local'}`;

    const badge = document.getElementById('stack-badge');
    if (s.busy && s.busy.disrupts) {
      badge.textContent = t('badgeWorking');
      badge.className = 'badge badge-warning';
    } else {
      badge.textContent = s.running ? t('badgeRunning') : t('badgeStopped');
      badge.className = `badge ${s.running ? 'badge-success' : 'badge-secondary'}`;
    }

    renderStatus(s);

    const btnStart = document.getElementById('btn-start');
    const btnOpen = document.getElementById('btn-open-site');
    const actionHint = document.getElementById('action-hint');
    if (btnStart) btnStart.classList.toggle('d-none', !!s.running && !s.busy);
    if (btnOpen) btnOpen.classList.toggle('d-none', !s.running || !!s.busy);
    if (actionHint) {
      if (s.busy) actionHint.textContent = s.busy.hint || `${s.busy.label}…`;
      else if ((s.flags?.services_up || 0) < (s.flags?.services_total || 4) && s.running) {
        actionHint.textContent = t('hintPartial');
      } else if (s.running) actionHint.textContent = t('hintRunning');
      else actionHint.textContent = t('hintStopped');
    }

    const extraLinks = (s.links || []).filter((l) => !l.primary && !/wsc\.local\/?$/i.test(l.url || ''));
    document.getElementById('links').innerHTML = `
      <a href="https://wsc.local" target="_blank" rel="noopener">${esc(t('website'))}</a>
      ${extraLinks.map((l) =>
        `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)}</a>`
      ).join('')}
      <a href="${GITHUB}" target="_blank" rel="noopener" title="${esc(t('githubTitle'))}">
        <i class="fab fa-github" aria-hidden="true"></i> ${esc(t('github'))}
      </a>`;

    const creds = document.getElementById('creds');
    if (s.user) {
      const pw = s.password || '';
      creds.innerHTML = `
        <div class="cred-row"><span>${esc(t('user'))}</span><strong>${esc(s.user)}</strong></div>
        <div class="cred-row">
          <span>${esc(t('password'))}</span>
          <span>
            <strong>${esc(pw || '—')}</strong>
            ${pw ? `<button type="button" class="btn btn-xs btn-default ml-1" id="copy-pw"><i class="fas fa-copy"></i> ${esc(t('copy'))}</button>` : ''}
          </span>
        </div>`;
      const btn = document.getElementById('copy-pw');
      if (btn) {
        btn.addEventListener('click', async () => {
          try {
            await navigator.clipboard.writeText(pw);
            toast(t('passwordCopied'));
            setLast(t('passwordCopied'));
          } catch {
            toast(t('copyFailed'), false);
          }
        });
      }
    }

    const snaps = await api('/api/snapshots');
    const box = document.getElementById('snapshots');
    if (!snaps.items?.length) {
      box.innerHTML = `<p class="text-muted p-3 mb-0 small">${esc(t('noBackups'))}</p>`;
    } else {
      box.innerHTML = `<table class="table table-sm table-hover mb-0">
        <thead class="thead-light"><tr><th>${esc(t('when'))}</th><th>${esc(t('size'))}</th><th class="text-right">${esc(t('actions'))}</th></tr></thead>
        <tbody>${snaps.items.map((it) => `
          <tr title="${esc(it.name)}">
            <td>
              <div class="snap-main">${esc(it.label || it.name)}</div>
              <div class="snap-sub">${esc(it.relative || t('backup'))}</div>
            </td>
            <td class="text-muted align-middle">${esc(it.size || '?')}</td>
            <td class="text-right text-nowrap align-middle">
              <button class="btn btn-xs btn-outline-primary" data-restore="${esc(it.name)}">${esc(t('restore'))}</button>
              <button class="btn btn-xs btn-outline-danger" data-delete="${esc(it.name)}">${esc(t('delete'))}</button>
            </td>
          </tr>`).join('')}
        </tbody></table>`;
    }

    document.getElementById('status-refreshed').textContent =
      `${t('refreshed')} ${new Date().toLocaleTimeString(lang === 'de' ? 'de-DE' : 'en-GB')}`;
  }

  async function waitJob(jobId, label) {
    const started = Date.now();
    const maxMs = 15 * 60 * 1000;
    while (Date.now() - started < maxMs) {
      await new Promise((r) => setTimeout(r, 1200));
      const data = await api(`/api/job?id=${encodeURIComponent(jobId)}`);
      const job = data.job;
      if (!job) throw new Error(lang === 'de' ? 'Auftrag verloren – Status prüfen.' : 'Job lost – check status.');
      setLast(`${label}: ${job.status === 'running' ? t('working') : job.message}`);
      updateRunningActivity(label, job.status === 'running' ? t('runningBg') : (job.message || ''));
      if (job.output) {
        const existing = activity.find((a) => a.level === 'running' && a.title === label);
        if (existing) existing.raw = job.output;
      }
      try { await refresh(); } catch { /* ignore */ }
      if (job.status === 'ok' || job.status === 'error') return job;
    }
    throw new Error(lang === 'de' ? 'Zeitüberschreitung – Status manuell prüfen.' : 'Timed out – check status manually.');
  }

  async function runAction(action, body = {}) {
    if (actionBusy) {
      toast(t('waitBusy'), false);
      return;
    }
    setBusy(true);
    const label = actionLabel(action);
    setLast(`${label} …`);
    updateRunningActivity(label, t('started'));
    try {
      const data = await api('/api/action', {
        method: 'POST',
        body: JSON.stringify({ action, ...body }),
      });

      if (data.async && data.job_id) {
        setLast(`${label} ${t('runningBg')}`);
        toast(data.message || `${label} ${t('started')}`);
        const job = await waitJob(data.job_id, label);
        const level = job.status === 'ok' ? (summarizeOutput(job.output).level || 'ok') : 'error';
        finishRunning(label, {
          message: job.message || (job.status === 'ok' ? t('finished') : t('failed')),
          level: job.status === 'ok' ? level : 'error',
          raw: job.output || job.error || '',
        });
        setLast(job.message || `${label}: ${job.status === 'ok' ? t('finished') : t('failed')}`);
        toast(job.message || (job.status === 'ok' ? t('finished') : t('failed')), job.status === 'ok');
        await refresh();
        return;
      }

      finishRunning(label, {
        message: data.message || t('finished'),
        level: 'ok',
        raw: data.output || '',
      });
      setLast((data.message || t('finished')).slice(0, 160));
      toast(data.message || t('finished'));
      if (action === 'reset') {
        setLast(t('resetStarted'));
        return;
      }
      await refresh();
    } catch (e) {
      const msg = friendlyNetError(e);
      finishRunning(label, { message: msg, level: 'error', raw: msg });
      setLast(`${t('error')}: ${msg}`);
      toast(msg, false);
      try { await refresh(); } catch { /* ignore */ }
    } finally {
      setBusy(false);
    }
  }

  document.body.addEventListener('click', async (ev) => {
    const tEl = ev.target.closest('[data-action],[data-restore],[data-delete]');
    if (!tEl) return;
    if (tEl.dataset.action) {
      const a = tEl.dataset.action;
      if (a === 'reset') {
        const r = await confirmReset();
        if (!r?.ok) return;
        return runAction('reset', { confirm: 'RESET', purge: !!r.purge });
      }
      if (a === 'stop' && !(await confirm(t('confirmStop')))) return;
      if (a === 'rebuild' && !(await confirm(t('confirmRebuild')))) return;
      if (a === 'repair' && !(await confirm(t('confirmRepair')))) return;
      if (a === 'snapshot-create') return runAction('snapshot_create');
      return runAction(a);
    }
    if (tEl.dataset.restore) {
      if (!(await confirm(t('confirmRestore')))) return;
      return runAction('snapshot_restore', { name: tEl.dataset.restore });
    }
    if (tEl.dataset.delete) {
      if (!(await confirm(t('confirmDelete')))) return;
      return runAction('snapshot_delete', { name: tEl.dataset.delete });
    }
  });

  applyI18n();
  renderFeed();
  refresh().catch((e) => {
    const msg = friendlyNetError(e);
    setLast(t('panelDown'));
    document.getElementById('status-title-text').textContent = t('panelDown');
    document.getElementById('status-hint').textContent = t('panelDownHint');
    pushActivity({ title: t('panelDown'), message: msg, level: 'error', raw: msg });
  });
  setInterval(() => {
    if (!actionBusy) refresh().catch(() => {});
  }, 8000);
})();
