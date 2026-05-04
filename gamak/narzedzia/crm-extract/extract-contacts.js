#!/usr/bin/env node
// extract-contacts.js — Ekstrakcja kontaktów z Gmail biuro.gamak@gmail.com
// Zero deps (Node 18+ ma natywne fetch).
//
// Faza 1 (ten plik): listing wszystkich wiadomości + zbiór unikalnych adresów + raw headers
// Output: kontakty-raw.json (do dalszego parsowania w faza 2)

const fs = require('fs');
const path = require('path');

const CREDS_PATH = 'C:/Users/klimc/.gmail-mcp/biuro/credentials.json';
const KEYS_PATH = 'C:/Users/klimc/.gmail-mcp/biuro/gcp-oauth.keys.json';
const OUT_DIR = 'C:/Users/klimc/Desktop/Asystenci/gamak/dane/crm';
const OUT_RAW = path.join(OUT_DIR, 'kontakty-raw.json');
const OUT_LOG = path.join(OUT_DIR, 'extract-progress.log');

const log = (msg) => {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.log(line);
  fs.appendFileSync(OUT_LOG, line + '\n');
};

async function getAccessToken() {
  const creds = JSON.parse(fs.readFileSync(CREDS_PATH, 'utf-8'));
  const keys = JSON.parse(fs.readFileSync(KEYS_PATH, 'utf-8')).installed;
  const now = Date.now();
  // Refresh jeśli wygasł lub <5 min do wygaśnięcia
  if (!creds.expiry_date || creds.expiry_date - now < 5 * 60 * 1000) {
    log('Token wygasł lub blisko wygaśnięcia, refreshuję...');
    const r = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: keys.client_id,
        client_secret: keys.client_secret,
        refresh_token: creds.refresh_token,
        grant_type: 'refresh_token',
      }),
    });
    if (!r.ok) throw new Error(`Token refresh failed: ${r.status} ${await r.text()}`);
    const data = await r.json();
    creds.access_token = data.access_token;
    creds.expiry_date = now + (data.expires_in * 1000);
    if (data.refresh_token) creds.refresh_token = data.refresh_token;
    fs.writeFileSync(CREDS_PATH, JSON.stringify(creds, null, 2));
    log('Token odświeżony, valid do ' + new Date(creds.expiry_date).toISOString());
  }
  return creds.access_token;
}

async function gmail(token, pathStr) {
  const r = await fetch(`https://gmail.googleapis.com/gmail/v1/users/me${pathStr}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`Gmail API ${pathStr} failed: ${r.status} ${txt}`);
  }
  return r.json();
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  // Wyczyść log
  fs.writeFileSync(OUT_LOG, '');
  log('=== START extract-contacts.js ===');

  const token = await getAccessToken();

  // 1. Whoami
  const profile = await gmail(token, '/profile');
  log(`Konto: ${profile.emailAddress} | wiadomości total: ${profile.messagesTotal} | wątki: ${profile.threadsTotal}`);

  if (profile.emailAddress !== 'biuro.gamak@gmail.com') {
    log(`UWAGA: oczekiwano biuro.gamak@gmail.com, dostalem ${profile.emailAddress}`);
  }

  // 2. Listing wszystkich messageIds (paginacja po 500, NIE w SPAM/TRASH)
  log('Pobieranie listy ID wszystkich wiadomości...');
  const allIds = [];
  let pageToken = undefined;
  let pageNum = 0;
  do {
    pageNum++;
    const qs = new URLSearchParams({ maxResults: '500' });
    if (pageToken) qs.set('pageToken', pageToken);
    const data = await gmail(token, `/messages?${qs}`);
    if (data.messages) allIds.push(...data.messages.map(m => m.id));
    pageToken = data.nextPageToken;
    if (pageNum % 5 === 0 || !pageToken) {
      log(`  page ${pageNum}: zebrano ${allIds.length} message IDs`);
    }
  } while (pageToken);
  log(`Zebrano łącznie ${allIds.length} message IDs`);

  // 3. Dla każdego message: GET metadata (format=metadata, fields=From/To/Cc/Date/Subject)
  // Strategia: zbieramy wszystkie From/To/Cc → potem deduplikacja po emailu
  log('Pobieranie metadata dla każdej wiadomości (może potrwać kilka minut)...');
  const contacts = new Map(); // email_lowercase → { emails:Set, names:Set, lastSeen, firstSeen, msgCount, sources:{from,to,cc}, sampleMessageId }
  const errors = [];
  const batchSize = 20; // paralelizacja
  let processed = 0;

  for (let i = 0; i < allIds.length; i += batchSize) {
    const batch = allIds.slice(i, i + batchSize);
    const results = await Promise.allSettled(batch.map(id =>
      gmail(token, `/messages/${id}?format=metadata&metadataHeaders=From&metadataHeaders=To&metadataHeaders=Cc&metadataHeaders=Date&metadataHeaders=Subject&metadataHeaders=Reply-To`)
    ));
    for (let j = 0; j < results.length; j++) {
      const r = results[j];
      if (r.status === 'rejected') {
        errors.push({ id: batch[j], err: String(r.reason) });
        continue;
      }
      const msg = r.value;
      const headers = (msg.payload?.headers || []).reduce((acc, h) => {
        acc[h.name.toLowerCase()] = h.value;
        return acc;
      }, {});
      const dateMs = parseInt(msg.internalDate || '0', 10);

      const addContact = (raw, source) => {
        if (!raw) return;
        // Parsuj "Name <email>" lub "email" lub multiple separated by ,
        const parts = raw.split(/,(?![^<]*>)/);
        for (const p of parts) {
          const m = p.match(/^\s*"?([^"<]*?)"?\s*<\s*([^>]+)\s*>\s*$/) || p.match(/^\s*([^@\s]+@[^\s]+)\s*$/);
          if (!m) continue;
          let name, email;
          if (m.length === 3) {
            name = (m[1] || '').trim();
            email = (m[2] || '').trim().toLowerCase();
          } else {
            name = '';
            email = (m[1] || '').trim().toLowerCase();
          }
          // Filtry: pomiń nasze własne, no-reply, mailery
          if (!email || !email.includes('@')) continue;
          if (email === 'biuro.gamak@gmail.com') return;
          if (/^(no-?reply|noreply|donotreply|mailer-daemon|postmaster|notifications?@|alerts?@)/i.test(email)) return;

          let c = contacts.get(email);
          if (!c) {
            c = {
              email,
              names: new Set(),
              firstSeenMs: dateMs,
              lastSeenMs: dateMs,
              msgCount: 0,
              sources: { from: 0, to: 0, cc: 0, replyTo: 0 },
              sampleMessageId: msg.id,
              sampleSubject: headers.subject || '',
            };
            contacts.set(email, c);
          }
          if (name) c.names.add(name);
          if (dateMs > c.lastSeenMs) c.lastSeenMs = dateMs;
          if (dateMs < c.firstSeenMs) c.firstSeenMs = dateMs;
          c.msgCount++;
          c.sources[source] = (c.sources[source] || 0) + 1;
        }
      };

      addContact(headers.from, 'from');
      addContact(headers.to, 'to');
      addContact(headers.cc, 'cc');
      addContact(headers['reply-to'], 'replyTo');
    }
    processed += batch.length;
    if (processed % 200 === 0 || processed === allIds.length) {
      log(`  Przetworzono ${processed}/${allIds.length} wiadomości (${contacts.size} unikalnych kontaktów do tej pory)`);
    }
  }

  log(`=== ZAKOŃCZONO LISTING ===`);
  log(`Total messages processed: ${allIds.length}`);
  log(`Errors: ${errors.length}`);
  log(`Unique contacts found: ${contacts.size}`);

  // 4. Konwersja Map → array, sortowanie po msgCount desc
  const result = Array.from(contacts.values()).map(c => ({
    email: c.email,
    names: Array.from(c.names),
    firstSeen: new Date(c.firstSeenMs).toISOString(),
    lastSeen: new Date(c.lastSeenMs).toISOString(),
    msgCount: c.msgCount,
    sources: c.sources,
    sampleMessageId: c.sampleMessageId,
    sampleSubject: c.sampleSubject,
  })).sort((a, b) => b.msgCount - a.msgCount);

  fs.writeFileSync(OUT_RAW, JSON.stringify({
    generatedAt: new Date().toISOString(),
    account: profile.emailAddress,
    totalMessagesProcessed: allIds.length,
    errors: errors.length,
    uniqueContactsCount: result.length,
    contacts: result,
  }, null, 2));

  log(`Zapisano: ${OUT_RAW}`);
  log('=== KONIEC ===');

  // Quick stats
  console.log('\n=== TOP 20 kontaktów po liczbie wiadomości ===');
  result.slice(0, 20).forEach((c, i) => {
    console.log(`${i + 1}. ${c.email} | ${c.names.join(' / ') || '(brak nazwy)'} | msg: ${c.msgCount}`);
  });
}

main().catch(err => {
  log(`FATAL: ${err.message}\n${err.stack}`);
  process.exit(1);
});
