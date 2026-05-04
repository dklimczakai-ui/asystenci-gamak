#!/usr/bin/env node
// enrich-contacts.js — Re-parse sygnatur przez Claude Haiku 4.5 na Bedrock
// Naprawia regex-based parsing który łapał temat maila / cytaty / RODO jako "company"

const fs = require('fs');
const path = require('path');
const { BedrockRuntimeClient, InvokeModelCommand } = require('@aws-sdk/client-bedrock-runtime');

const CREDS_PATH = 'C:/Users/klimc/.gmail-mcp/biuro/credentials.json';
const KEYS_PATH = 'C:/Users/klimc/.gmail-mcp/biuro/gcp-oauth.keys.json';
const IN_PARSED = 'C:/Users/klimc/Desktop/Asystenci/gamak/dane/crm/kontakty-parsed.json';
const OUT_ENRICHED = 'C:/Users/klimc/Desktop/Asystenci/gamak/dane/crm/kontakty-enriched.json';
const OUT_CSV = 'C:/Users/klimc/Desktop/Asystenci/gamak/dane/crm/kontakty-enriched.csv';
const OUT_LOG = 'C:/Users/klimc/Desktop/Asystenci/gamak/dane/crm/enrich-progress.log';

const MODEL_ID = 'eu.anthropic.claude-haiku-4-5-20251001-v1:0';
const REGION = 'eu-central-1';
const BATCH_SIZE = parseInt(process.env.BATCH || '8', 10);
const MAX_CONTACTS = parseInt(process.env.MAX || '99999', 10);

const log = (msg) => {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.log(line);
  fs.appendFileSync(OUT_LOG, line + '\n');
};

const bedrock = new BedrockRuntimeClient({ region: REGION });

async function getAccessToken() {
  const creds = JSON.parse(fs.readFileSync(CREDS_PATH, 'utf-8'));
  const keys = JSON.parse(fs.readFileSync(KEYS_PATH, 'utf-8')).installed;
  const now = Date.now();
  if (!creds.expiry_date || creds.expiry_date - now < 5 * 60 * 1000) {
    const r = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: keys.client_id, client_secret: keys.client_secret,
        refresh_token: creds.refresh_token, grant_type: 'refresh_token',
      }),
    });
    if (!r.ok) throw new Error(`Token refresh: ${r.status}`);
    const data = await r.json();
    creds.access_token = data.access_token;
    creds.expiry_date = now + (data.expires_in * 1000);
    if (data.refresh_token) creds.refresh_token = data.refresh_token;
    fs.writeFileSync(CREDS_PATH, JSON.stringify(creds, null, 2));
    log('Token refreshed');
  }
  return creds.access_token;
}

let tokenCache = null;
async function gmail(pathStr) {
  if (!tokenCache) tokenCache = await getAccessToken();
  let r = await fetch(`https://gmail.googleapis.com/gmail/v1/users/me${pathStr}`, {
    headers: { Authorization: `Bearer ${tokenCache}` },
  });
  if (r.status === 401) {
    tokenCache = null; tokenCache = await getAccessToken();
    r = await fetch(`https://gmail.googleapis.com/gmail/v1/users/me${pathStr}`, {
      headers: { Authorization: `Bearer ${tokenCache}` },
    });
  }
  if (!r.ok) throw new Error(`Gmail ${pathStr}: ${r.status}`);
  return r.json();
}

function extractTextBody(payload) {
  if (!payload) return '';
  if (payload.mimeType === 'text/plain' && payload.body?.data) {
    return Buffer.from(payload.body.data, 'base64url').toString('utf-8');
  }
  if (payload.parts) {
    for (const p of payload.parts) {
      if (p.mimeType === 'text/plain' && p.body?.data) {
        return Buffer.from(p.body.data, 'base64url').toString('utf-8');
      }
    }
    for (const p of payload.parts) {
      const r = extractTextBody(p);
      if (r) return r;
    }
    for (const p of payload.parts) {
      if (p.mimeType === 'text/html' && p.body?.data) {
        return Buffer.from(p.body.data, 'base64url').toString('utf-8')
          .replace(/<style[\s\S]*?<\/style>/gi, '')
          .replace(/<script[\s\S]*?<\/script>/gi, '')
          .replace(/<[^>]+>/g, ' ')
          .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
          .replace(/[ \t]+/g, ' ');
      }
    }
  }
  return '';
}

function extractSignature(body) {
  if (!body) return '';
  // Cut quoted reply
  let txt = body
    .split(/\n----+\s*Original Message\s*----+/i)[0]
    .split(/\nOn\s+[^\n]+\s+wrote:/i)[0]
    .split(/\n[Dd]nia\s+[^\n]+\s+napisał/i)[0]
    .split(/\nW dniu\s+[^\n]+\s+(?:o\s+)?[^\n]+\s+(?:napisał|pisze)/i)[0]
    .split(/\n----+\s*Wiadomość przekazana\s*----+/i)[0]
    .split(/\n----+\s*Forwarded message\s*----+/i)[0];
  // Strip > quoted lines
  const lines = txt.split('\n').filter(l => !/^\s*>/.test(l));
  // Last 30 non-empty lines as likely signature
  const nonEmpty = lines.map(l => l.trim()).filter(Boolean);
  return nonEmpty.slice(-30).join('\n');
}

async function bedrockExtract(signature, headerName, headerEmail) {
  const prompt = `Wyciagnij dane kontaktowe z ponizszej STOPKI/SYGNATURY emaila. Zwroc WYLACZNIE valid JSON (bez markdown, bez \`\`\`).

Kontekst:
- Email nadawcy: ${headerEmail}
- Nazwa z headera (moze byc niepoprawna): ${headerName || '(brak)'}

Zwroc dokladnie ten format:
{"firstName": string|null, "lastName": string|null, "position": string|null, "company": string|null, "phones": [string], "location": string|null}

Reguly:
- firstName/lastName: imie/nazwisko z sygnatury (NIE z domeny emaila)
- position: stanowisko (Dyrektor, Kierownik, Manager, Specjalista, itp.) - tylko jesli widoczne
- company: nazwa firmy/instytucji (np. "GAMAK Sp. z o.o.", "MOSiR Torun"). NIE temat maila, NIE "dniu... pisze:", NIE adresy URL, NIE klauzule RODO, NIE adresy fizyczne
- phones: tablica numerow telefonow w formacie ktorym byly podane. Pomin numery klienta z tematu maila
- location: miasto/region z adresu (np. "Bielsko-Biala", "Mazowieckie"). NIE pelna ulica
- Jesli czegos nie ma w sygnaturze, uzyj null (nie pusty string)

STOPKA:
"""
${signature.substring(0, 3000)}
"""

JSON:`;

  const cmd = new InvokeModelCommand({
    modelId: MODEL_ID,
    contentType: 'application/json',
    accept: 'application/json',
    body: JSON.stringify({
      anthropic_version: 'bedrock-2023-05-31',
      max_tokens: 400,
      messages: [{ role: 'user', content: prompt }],
    }),
  });

  const resp = await bedrock.send(cmd);
  const data = JSON.parse(new TextDecoder().decode(resp.body));
  let text = data.content[0].text.trim();
  // Strip markdown code fences if present
  text = text.replace(/^```json\s*/i, '').replace(/^```\s*/i, '').replace(/\s*```\s*$/, '').trim();
  // Find JSON object
  const m = text.match(/\{[\s\S]*\}/);
  if (m) text = m[0];
  try {
    return { result: JSON.parse(text), tokens: data.usage };
  } catch (e) {
    throw new Error(`Bedrock returned non-JSON: ${text.substring(0, 200)}`);
  }
}

async function processOne(c) {
  // 1. Find sample message FROM this email
  let msgId = null;
  try {
    const search = await gmail(`/messages?maxResults=3&q=${encodeURIComponent('from:' + c.email)}`);
    if (search.messages && search.messages.length > 0) {
      msgId = search.messages[0].id;
    }
  } catch (e) { /* ignore */ }

  if (!msgId) return { ...c, _enrichSkip: 'no_message_from' };

  // 2. Fetch full body
  let body;
  try {
    const msg = await gmail(`/messages/${msgId}?format=full`);
    body = extractTextBody(msg.payload);
  } catch (e) {
    return { ...c, _enrichSkip: 'fetch_failed', _enrichErr: e.message };
  }

  if (!body || body.length < 30) return { ...c, _enrichSkip: 'no_body' };

  // 3. Extract signature (last lines, no quoted)
  const sig = extractSignature(body);
  if (!sig || sig.length < 20) return { ...c, _enrichSkip: 'sig_too_short' };

  // 4. Bedrock parse
  let extract;
  try {
    const { result, tokens } = await bedrockExtract(sig, c.fullName, c.email);
    extract = result;
    extract._tokens = tokens;
  } catch (e) {
    return { ...c, _enrichSkip: 'bedrock_failed', _enrichErr: e.message };
  }

  // 5. Merge: prefer Bedrock; fallback to original if Bedrock returned null
  return {
    ...c,
    fullName: extract.firstName && extract.lastName
      ? `${extract.firstName} ${extract.lastName}`
      : (c.fullName || extract.firstName || extract.lastName || ''),
    firstName: extract.firstName || c.firstName || '',
    lastName: extract.lastName || c.lastName || '',
    position: extract.position || c.position || '',
    company: extract.company || '',  // Bedrock null = jawnie "brak firmy" (lepiej niż śmieć)
    phones: (extract.phones && extract.phones.length > 0) ? extract.phones : (c.phones || []),
    location: extract.location || c.location || '',
    _enriched: true,
    _enrichTokens: extract._tokens,
  };
}

async function processBatch(batch) {
  return Promise.allSettled(batch.map(c => processOne(c)));
}

function csvEscape(v) {
  if (v === null || v === undefined) return '';
  const s = String(v);
  if (/[",\n;]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

async function main() {
  fs.writeFileSync(OUT_LOG, '');
  log('=== START enrich-contacts.js ===');

  const inData = JSON.parse(fs.readFileSync(IN_PARSED, 'utf-8'));
  log(`Wczytano ${inData.contacts.length} kontaktów z ${IN_PARSED}`);

  // Process all parsed contacts
  const toProcess = inData.contacts.slice(0, MAX_CONTACTS);
  log(`Do enrichment: ${toProcess.length} kontaktów (BATCH=${BATCH_SIZE})`);
  log(`Model: ${MODEL_ID}`);

  const results = [];
  let totalInputTokens = 0, totalOutputTokens = 0, errors = 0, skipped = 0, enriched = 0;

  // Resume support: jeśli jest poprzedni output, kontynuuj od miejsca przerwania
  let startIdx = 0;
  if (fs.existsSync(OUT_ENRICHED)) {
    try {
      const prev = JSON.parse(fs.readFileSync(OUT_ENRICHED, 'utf-8'));
      if (prev.contacts && prev.contacts.length > 0) {
        results.push(...prev.contacts);
        startIdx = prev.contacts.length;
        log(`Resume: ${startIdx} już przetworzonych z poprzedniego runu`);
      }
    } catch (e) { /* ignore, restart */ }
  }

  for (let i = startIdx; i < toProcess.length; i += BATCH_SIZE) {
    const batch = toProcess.slice(i, i + BATCH_SIZE);
    const batchResults = await processBatch(batch);
    for (const r of batchResults) {
      if (r.status === 'fulfilled') {
        results.push(r.value);
        if (r.value._enriched) {
          enriched++;
          if (r.value._enrichTokens) {
            totalInputTokens += r.value._enrichTokens.input_tokens || 0;
            totalOutputTokens += r.value._enrichTokens.output_tokens || 0;
          }
        }
        if (r.value._enrichSkip) skipped++;
      } else {
        errors++;
        log(`Batch error: ${r.reason}`);
      }
    }
    // Save progress every batch (resume support)
    if ((i + BATCH_SIZE) % 80 === 0 || i + BATCH_SIZE >= toProcess.length) {
      fs.writeFileSync(OUT_ENRICHED, JSON.stringify({
        generatedAt: new Date().toISOString(),
        sourceTotal: inData.contacts.length,
        processed: results.length,
        enriched, skipped, errors,
        totalInputTokens, totalOutputTokens,
        estCost: ((totalInputTokens / 1e6) * 1.0 + (totalOutputTokens / 1e6) * 5.0).toFixed(4),
        contacts: results,
      }, null, 2));
    }
    log(`  ${results.length}/${toProcess.length} (enriched: ${enriched}, skipped: ${skipped}, errors: ${errors}, tokens: ${totalInputTokens}/${totalOutputTokens}, est. cost: $${((totalInputTokens / 1e6) * 1.0 + (totalOutputTokens / 1e6) * 5.0).toFixed(2)})`);
  }

  // Final save
  fs.writeFileSync(OUT_ENRICHED, JSON.stringify({
    generatedAt: new Date().toISOString(),
    sourceTotal: inData.contacts.length,
    processed: results.length,
    enriched, skipped, errors,
    totalInputTokens, totalOutputTokens,
    estCost: ((totalInputTokens / 1e6) * 1.0 + (totalOutputTokens / 1e6) * 5.0).toFixed(4),
    contacts: results,
  }, null, 2));
  log(`Zapisano JSON: ${OUT_ENRICHED}`);

  // CSV
  const headers = ['category', 'email', 'firstName', 'lastName', 'fullName', 'phones', 'position', 'company', 'location', 'msgCount', 'fromCount', 'toCount', 'ccCount', 'firstSeen', 'lastSeen'];
  const rows = [headers.join(',')];
  for (const c of results) {
    rows.push([
      csvEscape(c.category || ''), csvEscape(c.email),
      csvEscape(c.firstName), csvEscape(c.lastName), csvEscape(c.fullName),
      csvEscape((c.phones || []).join(' / ')),
      csvEscape(c.position), csvEscape(c.company), csvEscape(c.location),
      c.msgCount || 0, c.sources?.from || 0, c.sources?.to || 0, c.sources?.cc || 0,
      csvEscape(c.firstSeen), csvEscape(c.lastSeen),
    ].join(','));
  }
  fs.writeFileSync(OUT_CSV, rows.join('\n'), 'utf-8');
  log(`Zapisano CSV: ${OUT_CSV}`);

  // Stats
  log(`=== STATS ===`);
  log(`  Total processed: ${results.length}`);
  log(`  Enriched (Bedrock): ${enriched} (${(enriched / results.length * 100).toFixed(1)}%)`);
  log(`  Skipped: ${skipped} (${(skipped / results.length * 100).toFixed(1)}%)`);
  log(`  Errors: ${errors}`);
  log(`  Tokens: ${totalInputTokens} in + ${totalOutputTokens} out`);
  log(`  Cost: $${((totalInputTokens / 1e6) * 1.0 + (totalOutputTokens / 1e6) * 5.0).toFixed(4)}`);
  log(`=== KONIEC ===`);
}

main().catch(err => {
  log(`FATAL: ${err.message}\n${err.stack}`);
  process.exit(1);
});
