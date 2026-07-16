(() => {
  const TOKEN = document.querySelector('meta[name="panel-token"]')?.content || '';
  const out = document.getElementById('output');
  const toastArea = document.getElementById('toast-area');
  let confirmResolve = null;

  $('#confirmOk').on('click', () => {
    $('#confirmModal').modal('hide');
    if (confirmResolve) confirmResolve(true);
    confirmResolve = null;
  });
  $('#confirmModal').on('hidden.bs.modal', () => {
    if (confirmResolve) confirmResolve(false);
    confirmResolve = null;
  });

  function confirm(msg) {
    document.getElementById('confirmBody').textContent = msg;
    $('#confirmModal').modal('show');
    return new Promise((r) => { confirmResolve = r; });
  }

  function toast(msg, ok = true) {
    const el = document.createElement('div');
    el.className = `alert alert-${ok ? 'success' : 'danger'} py-2 px-3 mb-2 shadow-sm`;
    el.textContent = msg;
    toastArea.appendChild(el);
    setTimeout(() => el.remove(), 3500);
  }

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        'X-Panel-Token': TOKEN,
        ...(opts.headers || {}),
      },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  }

  function setBusy(busy) {
    document.querySelectorAll('[data-action]').forEach((b) => { b.disabled = busy; });
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  async function refresh() {
    const s = await api('/api/status');
    document.getElementById('meta-prefix').textContent =
      `Prefix ${s.prefix} · ${s.project}`;
    const badge = document.getElementById('stack-badge');
    badge.textContent = s.running ? 'läuft' : 'gestoppt';
    badge.className = `badge ${s.running ? 'badge-success' : 'badge-secondary'}`;

    const icons = {
      web: 'fa-globe',
      mysql: 'fa-database',
      phpmyadmin: 'fa-table',
      mailhog: 'fa-envelope',
    };
    const colors = {
      web: 'bg-info',
      mysql: 'bg-success',
      phpmyadmin: 'bg-warning',
      mailhog: 'bg-danger',
    };
    document.getElementById('service-boxes').innerHTML = (s.services || []).map((x) => {
      const key = x.name.split('-').pop();
      const icon = icons[key] || 'fa-cube';
      const bg = colors[key] || 'bg-secondary';
      return `<div class="col-md-3 col-sm-6">
        <div class="info-box">
          <span class="info-box-icon ${bg}"><i class="fas ${icon}"></i></span>
          <div class="info-box-content">
            <span class="info-box-text">${esc(x.name)}</span>
            <span class="info-box-number" style="font-size:1rem">${x.running ? 'up' : 'down'}</span>
          </div>
        </div>
      </div>`;
    }).join('');

    document.getElementById('links').innerHTML = (s.links || []).map((l) =>
      `<li class="mb-2"><a href="${l.url}" target="_blank" rel="noopener"><i class="fas fa-external-link-alt mr-1"></i>${esc(l.label)}</a></li>`
    ).join('');

    const creds = document.getElementById('creds');
    if (s.user) {
      creds.innerHTML = `<div>Benutzer: <strong>${esc(s.user)}</strong></div>
        <div>Passwort: <strong>${esc(s.password || '(siehe .env)')}</strong></div>`;
    }

    const snaps = await api('/api/snapshots');
    const box = document.getElementById('snapshots');
    if (!snaps.items?.length) {
      box.innerHTML = '<p class="text-muted p-3 mb-0 small">Noch keine Snapshots.</p>';
    } else {
      box.innerHTML = `<table class="table table-sm table-striped mb-0">
        <thead><tr><th>Name</th><th>Größe</th><th></th></tr></thead>
        <tbody>${snaps.items.map((it) => `
          <tr>
            <td><code>${esc(it.name)}</code></td>
            <td class="text-muted">${esc(it.size || '?')}</td>
            <td class="text-right text-nowrap">
              <button class="btn btn-xs btn-outline-primary" data-restore="${esc(it.name)}">Restore</button>
              <button class="btn btn-xs btn-outline-danger" data-delete="${esc(it.name)}">Löschen</button>
            </td>
          </tr>`).join('')}
        </tbody></table>`;
    }
  }

  async function runAction(action, body = {}) {
    setBusy(true);
    out.textContent = `Läuft: ${action} …`;
    try {
      const data = await api('/api/action', {
        method: 'POST',
        body: JSON.stringify({ action, ...body }),
      });
      out.textContent = data.output || 'OK';
      toast(data.message || 'Fertig');
      await refresh();
    } catch (e) {
      out.textContent = String(e.message || e);
      toast(String(e.message || e), false);
    } finally {
      setBusy(false);
    }
  }

  document.body.addEventListener('click', async (ev) => {
    const t = ev.target.closest('[data-action],[data-restore],[data-delete]');
    if (!t) return;
    if (t.dataset.action) {
      const a = t.dataset.action;
      if (a === 'stop' || a === 'rebuild' || a === 'repair') {
        if (!(await confirm(`Wirklich „${a}“? Nur dieses wsc-local-Projekt.`))) return;
      }
      if (a === 'snapshot-create') return runAction('snapshot_create');
      return runAction(a);
    }
    if (t.dataset.restore) {
      if (!(await confirm(`Snapshot „${t.dataset.restore}“ einspielen? Überschreibt Dateien + DB.`))) return;
      return runAction('snapshot_restore', { name: t.dataset.restore });
    }
    if (t.dataset.delete) {
      if (!(await confirm(`Snapshot „${t.dataset.delete}“ löschen?`))) return;
      return runAction('snapshot_delete', { name: t.dataset.delete });
    }
  });

  refresh().catch((e) => { out.textContent = 'Panel nicht erreichbar: ' + e.message; });
  setInterval(() => refresh().catch(() => {}), 8000);
})();
