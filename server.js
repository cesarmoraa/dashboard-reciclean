const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { URL } = require('url');

const PORT = Number(process.env.PORT || 3000);
const NODE_ENV = process.env.NODE_ENV || 'development';
const HOST = process.env.HOST || (NODE_ENV === 'production' ? '0.0.0.0' : '127.0.0.1');
const ACCESS_PASSWORD = process.env.ACCESS_PASSWORD;

if (!ACCESS_PASSWORD) {
  console.error('Falta ACCESS_PASSWORD. Define la variable de entorno antes de iniciar el servidor.');
  process.exit(1);
}

const BASE_DIR = __dirname;
const DASHBOARD_FILE = path.join(BASE_DIR, 'dashboard_reciclean_registros_mes_actual.html');
const LOGIN_FILE = path.join(BASE_DIR, 'public', 'login.html');
const SESSION_COOKIE_NAME = 'reciclean_session';
const SESSION_DURATION_MS = 1000 * 60 * 60 * 12;
const SESSION_SECRET = process.env.SESSION_SECRET
  || crypto.createHash('sha256').update(`${ACCESS_PASSWORD}|reciclean-dashboard|session`).digest('hex');

function safeEqualString(left, right) {
  const leftBuffer = Buffer.from(String(left || ''));
  const rightBuffer = Buffer.from(String(right || ''));
  if (leftBuffer.length !== rightBuffer.length) {
    return false;
  }
  return crypto.timingSafeEqual(leftBuffer, rightBuffer);
}

function base64urlEncode(value) {
  return Buffer.from(value).toString('base64url');
}

function base64urlDecode(value) {
  return Buffer.from(value, 'base64url').toString('utf8');
}

function signPayload(payload) {
  return crypto.createHmac('sha256', SESSION_SECRET).update(payload).digest('base64url');
}

function createSessionToken() {
  const payload = JSON.stringify({
    issuedAt: Date.now(),
    expiresAt: Date.now() + SESSION_DURATION_MS,
    nonce: crypto.randomBytes(12).toString('hex')
  });
  return `${base64urlEncode(payload)}.${signPayload(payload)}`;
}

function readSessionToken(token) {
  if (!token || !token.includes('.')) {
    return { valid: false, reason: 'missing' };
  }

  const [encodedPayload, signature] = token.split('.');
  if (!encodedPayload || !signature) {
    return { valid: false, reason: 'malformed' };
  }

  try {
    const payload = base64urlDecode(encodedPayload);
    const expectedSignature = signPayload(payload);
    if (!safeEqualString(signature, expectedSignature)) {
      return { valid: false, reason: 'signature' };
    }

    const parsed = JSON.parse(payload);
    if (!parsed.expiresAt || parsed.expiresAt <= Date.now()) {
      return { valid: false, reason: 'expired' };
    }

    return { valid: true, data: parsed };
  } catch (error) {
    return { valid: false, reason: 'invalid' };
  }
}

function parseCookies(req) {
  const header = req.headers.cookie;
  if (!header) {
    return {};
  }

  return header.split(';').reduce((accumulator, part) => {
    const [rawKey, ...rest] = part.trim().split('=');
    if (!rawKey) {
      return accumulator;
    }
    accumulator[rawKey] = decodeURIComponent(rest.join('='));
    return accumulator;
  }, {});
}

function json(res, statusCode, payload, headers = {}) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
    ...headers
  });
  res.end(body);
}

function redirect(res, location) {
  res.writeHead(302, {
    Location: location,
    'Cache-Control': 'no-store'
  });
  res.end();
}

function sendHtmlFile(res, filePath) {
  fs.readFile(filePath, 'utf8', (error, content) => {
    if (error) {
      json(res, 500, { ok: false, message: 'No fue posible cargar la vista solicitada.' });
      return;
    }

    res.writeHead(200, {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store'
    });
    res.end(content);
  });
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let raw = '';
    req.on('data', chunk => {
      raw += chunk;
      if (raw.length > 1024 * 32) {
        reject(new Error('Body demasiado grande.'));
        req.destroy();
      }
    });
    req.on('end', () => {
      if (!raw) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(raw));
      } catch (error) {
        reject(new Error('JSON inválido.'));
      }
    });
    req.on('error', reject);
  });
}

function buildSessionCookie(token, maxAgeSeconds) {
  const parts = [
    `${SESSION_COOKIE_NAME}=${encodeURIComponent(token)}`,
    'Path=/',
    'HttpOnly',
    'SameSite=Lax',
    `Max-Age=${maxAgeSeconds}`
  ];

  if (NODE_ENV === 'production') {
    parts.push('Secure');
  }

  return parts.join('; ');
}

function clearSessionCookie() {
  const parts = [
    `${SESSION_COOKIE_NAME}=`,
    'Path=/',
    'HttpOnly',
    'SameSite=Lax',
    'Max-Age=0'
  ];

  if (NODE_ENV === 'production') {
    parts.push('Secure');
  }

  return parts.join('; ');
}

function requireSession(req, res, onSuccess) {
  const cookies = parseCookies(req);
  const token = cookies[SESSION_COOKIE_NAME];
  const session = readSessionToken(token);

  if (session.valid) {
    onSuccess();
    return;
  }

  const hadCookie = Boolean(token);
  redirect(res, hadCookie ? '/login?reason=expired' : '/login');
}

function routeRequest(req, res) {
  const requestUrl = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const { pathname } = requestUrl;

  if (req.method === 'GET' && pathname === '/health') {
    json(res, 200, { ok: true, status: 'ok' });
    return;
  }

  if (req.method === 'GET' && pathname === '/login') {
    const cookies = parseCookies(req);
    const session = readSessionToken(cookies[SESSION_COOKIE_NAME]);
    if (session.valid) {
      redirect(res, '/');
      return;
    }
    sendHtmlFile(res, LOGIN_FILE);
    return;
  }

  if (req.method === 'POST' && pathname === '/api/login') {
    readJsonBody(req)
      .then(body => {
        const password = typeof body.password === 'string' ? body.password : '';
        if (!safeEqualString(password, ACCESS_PASSWORD)) {
          json(res, 401, { ok: false, message: 'No fue posible validar el acceso.' });
          return;
        }

        const token = createSessionToken();
        json(
          res,
          200,
          { ok: true },
          { 'Set-Cookie': buildSessionCookie(token, Math.floor(SESSION_DURATION_MS / 1000)) }
        );
      })
      .catch(() => {
        json(res, 400, { ok: false, message: 'No fue posible validar el acceso.' });
      });
    return;
  }

  if (req.method === 'POST' && pathname === '/api/logout') {
    json(
      res,
      200,
      { ok: true },
      { 'Set-Cookie': clearSessionCookie() }
    );
    return;
  }

  if (req.method === 'GET' && pathname === '/api/session') {
    const cookies = parseCookies(req);
    const session = readSessionToken(cookies[SESSION_COOKIE_NAME]);
    if (!session.valid) {
      json(res, 401, { authenticated: false, message: 'No fue posible validar la sesión.' });
      return;
    }

    json(res, 200, {
      authenticated: true,
      expiresAt: session.data.expiresAt
    });
    return;
  }

  if (req.method === 'GET' && (pathname === '/' || pathname === '/dashboard' || pathname === '/dashboard_reciclean_registros_mes_actual.html')) {
    requireSession(req, res, () => sendHtmlFile(res, DASHBOARD_FILE));
    return;
  }

  if (req.method === 'GET' && pathname === '/favicon.ico') {
    res.writeHead(204);
    res.end();
    return;
  }

  json(res, 404, { ok: false, message: 'Ruta no encontrada.' });
}

const server = http.createServer(routeRequest);

server.listen(PORT, HOST, () => {
  console.log(`Reciclean dashboard disponible en http://${HOST}:${PORT}`);
});
