const $ = (id) => document.getElementById(id);

function formatUptime(seconds) {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return [d && `${d}d`, (d || h) && `${h}h`, `${m}m`, `${s}s`].filter(Boolean).join(' ');
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString('es-AR') : '—';
}

function setLive(ok, text) {
  $('live-dot').className = `dot ${ok ? 'ok' : 'bad'}`;
  $('live-text').textContent = text;
}

async function loadInfo() {
  try {
    const res = await fetch('/api/info');
    const info = await res.json();

    $('version').textContent = `v${info.version}`;
    $('environment').textContent = info.environment;
    $('commit').textContent = info.commit ? info.commit.slice(0, 7) : '—';
    $('deployed').textContent = formatDate(info.deployedAt || info.startedAt);
    $('python').textContent = info.python;
    $('hostname').textContent = info.hostname;
    $('platform').textContent = info.platform;
    $('uptime').textContent = formatUptime(info.uptimeSeconds);
    $('memory').textContent = info.memoryMb != null ? `${info.memoryMb} MB` : '—';

    const db = info.database;
    const up = db.status === 'up';
    $('db-pill').textContent = up ? 'conectada' : 'caída';
    $('db-pill').className = `pill ${up ? 'ok' : 'bad'}`;
    $('db-latency').textContent = up ? `${db.latencyMs} ms` : db.error || '';
    $('db-name').textContent = db.name || '—';
    $('db-version').textContent = db.version || '—';
    $('db-time').textContent = formatDate(db.serverTime);

    setLive(up, up ? 'Todo en línea' : 'Base de datos no disponible');
  } catch {
    setLive(false, 'Servidor no responde');
  }
}

function animateCounter(el, target) {
  const duration = 900;
  const start = performance.now();
  const step = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    el.textContent = Math.round(target * (1 - Math.pow(1 - progress, 3))).toLocaleString('es-AR');
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

async function registerVisit() {
  try {
    const res = await fetch('/api/visits', { method: 'POST' });
    if (!res.ok) return;
    const { total } = await res.json();
    animateCounter($('visits'), total);
  } catch {}
}

function renderMessage(msg) {
  const li = document.createElement('li');
  const meta = document.createElement('div');
  meta.className = 'meta';
  const author = document.createElement('strong');
  author.textContent = msg.author;
  meta.append(author, ` · ${formatDate(msg.created_at)}`);
  const body = document.createElement('div');
  body.textContent = msg.content;
  li.append(meta, body);
  return li;
}

async function loadMessages() {
  const list = $('messages');
  try {
    const res = await fetch('/api/messages');
    const messages = await res.json();
    list.replaceChildren(...messages.map(renderMessage));
    if (!messages.length) {
      const empty = document.createElement('li');
      empty.className = 'empty';
      empty.textContent = 'Todavía no hay mensajes. ¡Sé el primero!';
      list.append(empty);
    }
  } catch {
    list.replaceChildren();
  }
}

$('message-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const button = e.target.querySelector('button');
  $('form-error').textContent = '';
  button.disabled = true;
  try {
    const res = await fetch('/api/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ author: $('author').value, content: $('content').value }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'No se pudo enviar');
    $('content').value = '';
    await loadMessages();
  } catch (err) {
    $('form-error').textContent = err.message;
  } finally {
    button.disabled = false;
  }
});

loadInfo();
registerVisit();
loadMessages();
setInterval(loadInfo, 5000);
