'use strict';

const Hapi = require('@hapi/hapi');
const Inert = require('@hapi/inert');
const fs = require('fs').promises;
const path = require('path');
const os = require('os');

const STORE = path.join(os.tmpdir(), `notes_${Math.random().toString(36).substring(2, 15)}`);

function parseQuery(qs = '') {
  const out = {};
  for (const pair of qs.split('&')) {
    if (!pair) continue;
    let [k, v = ''] = pair.split('=');
    k = decodeURIComponent(k.replace(/\+/g, ' '));
    v = decodeURIComponent(v.replace(/\+/g, ' '));
    const parts = k.split(/\[|\]/).filter(Boolean);
    let cur = out;
    for (let i = 0; i < parts.length - 1; i++) {
      cur = cur[parts[i]] = cur[parts[i]] || {};
    }
    cur[parts.at(-1)] = v;
  }
  return out;
}

const file = t => path.join(STORE, t);

const validateTitle = t => {
  if (!t)
    throw new Error('Title required');
  if (typeof t !== 'string')
    throw new Error('Title must be a string');
  if (t.length > 8)
    throw new Error('Title too long (max 8 chars)');
  return t;
};

(async () => {
  await fs.mkdir(STORE, { recursive: true });

  const server = Hapi.server({ port: 3000, host: '0.0.0.0', routes: { cors: true } });
  await server.register(Inert);

  server.ext('onPreHandler', (req, h) => {
    const qs = req.raw.req.url.split('?')[1] || '';
    req.args = parseQuery(qs);
    return h.continue;
  });
  server.route([
    { method: 'GET', path: '/', handler: { file: 'index.html' } },
    {
      path: '/notes', method: 'POST',
      handler: async (req, h) => {
        try {
          validateTitle(req.payload.title);
          
          try {
            await fs.access(file(req.payload.title));
            return h.response({ error: 'Note with this title already exists' }).code(409);
          } catch (err) {}
          
        } catch (err) {
          return h.response({ error: err.message }).code(400);
        }
        const note = { title: req.payload.title, content: req.payload.content };
        await fs.writeFile(file(note.title), JSON.stringify(note, null, 2));
        return h.response(note).code(201);
      }
    },
    {
      path: '/notes', method: 'GET',
      handler: async req => {
        const files = await fs.readdir(STORE);
        if (req.args?.length === 'true') return { length: files.length };
        return Promise.all(files.map(f => fs.readFile(file(f), 'utf8').then(JSON.parse)));
      }
    },
    {
      path: '/note/{title}', method: 'GET',
      handler: async (req, h) => {
        try {
          const title = validateTitle(req.params.title);
          const filepath = file(title);
          await fs.access(filepath);
          return h
            .file(filepath, { confine: false, filename: title })
            .type('application/json');
        } catch (err) {
          const isTitleErr = err.message.startsWith('Title');
          return h.response({ error: isTitleErr ? err.message : 'Note not found' }).code(isTitleErr ? 400 : 404);
        }
      }
    }
  ]);

  await server.start();
  console.log(`Server running at ${server.info.uri}`);
})();
