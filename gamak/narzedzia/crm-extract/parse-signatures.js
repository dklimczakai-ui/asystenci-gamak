#!/usr/bin/env node
// parse-signatures.js — FAZA 2.2: parsowanie sygnatur z body wiadomości
// Czyta: kontakty-raw.json
// Output: kontakty-parsed.json + kontakty.csv
//
// Strategia:
// 1. Filter: tylko kontakty którzy WYSŁALI do nas (msgCount.from > 0) — to "klient-kandydaci"
// 2. Sort by msgCount desc, limit TOP_N
// 3. Dla każdego: fetch ostatniej wiadomości od nich (1 sample) → wyciągnij text/plain body
// 4. Parsuj sygnaturę: telefon, stanowisko, firma, miasto
// 5. Output: parsed JSON + CSV

const fs = require('fs');
const path = require('path');

const CREDS_PATH = 'C:/Users/klimc/.gmail-mcp/biuro/credentials.json';
const KEYS_PATH = 'C:/Users/klimc/.gmail-mcp/biuro/gcp-oauth.keys.json';
const IN_RAW = 'C:/Users/klimc/Desktop/Asystenci/gamak/dane/crm/kontakty-raw.json';
const OUT_PARSED = 'C:/Users/klimc/Desktop/Asystenci/gamak/dane/crm/kontakty-parsed.json';
const OUT_CSV = 'C:/Users/klimc/Desktop/Asystenci/gamak/dane/crm/kontakty.csv';
const OUT_LOG = 'C:/Users/klimc/Desktop/Asystenci/gamak/dane/crm/parse-progress.log';

const TOP_N = parseInt(process.env.TOP_N || '2000', 10); // limit liczby kontaktów do parsowania body

const log = (msg) => {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.log(line);
  fs.appendFileSync(OUT_LOG, line + '\n');
};

async function getAccessToken() {
  const creds = JSON.parse(fs.readFileSync(CREDS_PATH, 'utf-8'));
  const keys = JSON.parse(fs.readFileSync(KEYS_PATH, 'utf-8')).installed;
  const now = Date.now();
  if (!creds.expiry_date || creds.expiry_date - now < 5 * 60 * 1000) {
    log('Token refresh...');
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
    if (!r.ok) throw new Error(`Token refresh failed: ${r.status}`);
    const data = await r.json();
    creds.access_token = data.access_token;
    creds.expiry_date = now + (data.expires_in * 1000);
    if (data.refresh_token) creds.refresh_token = data.refresh_token;
    fs.writeFileSync(CREDS_PATH, JSON.stringify(creds, null, 2));
    log('Token odświeżony');
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
    tokenCache = null;
    tokenCache = await getAccessToken();
    r = await fetch(`https://gmail.googleapis.com/gmail/v1/users/me${pathStr}`, {
      headers: { Authorization: `Bearer ${tokenCache}` },
    });
  }
  if (!r.ok) throw new Error(`Gmail API ${pathStr}: ${r.status}`);
  return r.json();
}

// Wyciągnij text/plain z payload (rekursywnie po multipart)
function extractTextBody(payload) {
  if (!payload) return '';
  if (payload.mimeType === 'text/plain' && payload.body?.data) {
    return Buffer.from(payload.body.data, 'base64url').toString('utf-8');
  }
  if (payload.parts) {
    // Preferuj text/plain
    for (const p of payload.parts) {
      if (p.mimeType === 'text/plain' && p.body?.data) {
        return Buffer.from(p.body.data, 'base64url').toString('utf-8');
      }
    }
    // Fallback: rekurencja
    for (const p of payload.parts) {
      const r = extractTextBody(p);
      if (r) return r;
    }
    // Ostateczność: text/html (strip tagów)
    for (const p of payload.parts) {
      if (p.mimeType === 'text/html' && p.body?.data) {
        return Buffer.from(p.body.data, 'base64url').toString('utf-8')
          .replace(/<style[\s\S]*?<\/style>/gi, '')
          .replace(/<script[\s\S]*?<\/script>/gi, '')
          .replace(/<[^>]+>/g, ' ')
          .replace(/&nbsp;/g, ' ')
          .replace(/&amp;/g, '&')
          .replace(/&lt;/g, '<')
          .replace(/&gt;/g, '>')
          .replace(/&quot;/g, '"')
          .replace(/\s+/g, ' ');
      }
    }
  }
  return '';
}

// Parser sygnatury: telefon, stanowisko, firma, miasto
function parseSignature(body, contactName, contactEmail) {
  if (!body) return {};

  // Odetnij quoted reply (---- Original Message ----, On <date> wrote, > prefix)
  let txt = body
    .split(/\n----+\s*Original Message\s*----+/i)[0]
    .split(/\nOn\s+[^\n]+\s+wrote:/i)[0]
    .split(/\n[Dd]nia\s+[^\n]+\s+napisał/i)[0]
    .split(/\nW dniu\s+[^\n]+\s+(?:o\s+)?[^\n]+\s+(?:napisał|pisze)/i)[0];

  // Usuń linie zaczynające się od >
  const lines = txt.split('\n').filter(l => !/^\s*>/.test(l));
  txt = lines.join('\n');

  // Bierzemy ostatnie 30 linii niepustych jako prawdopodobną stopkę
  const sigLines = lines.map(l => l.trim()).filter(l => l.length > 0).slice(-30);
  const sig = sigLines.join('\n');

  const result = {};

  // 1. TELEFON — różne formaty PL/EU
  const phoneRegexes = [
    /(?:tel\.?|telefon|phone|mobile|mob\.?|kom\.?|gsm|t:|\+)[:\s]*((?:\+?\d{1,3}[\s\-.]?)?(?:\(?\d{2,4}\)?[\s\-.]?)?\d{3}[\s\-.]?\d{2,3}[\s\-.]?\d{2,3})/gi,
    /(\+?\d{2,3}[\s\-.]?\d{3}[\s\-.]?\d{3}[\s\-.]?\d{3})/g, // ogólny: +48 123 456 789
    /(\(\d{2,4}\)\s*\d{3}[\s\-.]?\d{2,3}[\s\-.]?\d{2,3})/g, // (12) 345 67 89
  ];
  const phones = new Set();
  for (const rx of phoneRegexes) {
    let m;
    rx.lastIndex = 0;
    while ((m = rx.exec(sig)) !== null) {
      const ph = m[1].replace(/[\s\-.]/g, ' ').replace(/\s+/g, ' ').trim();
      // Walidacja: tylko jeśli >= 9 cyfr (krótkie odrzucamy)
      const digits = ph.replace(/\D/g, '');
      if (digits.length >= 9 && digits.length <= 13) phones.add(ph);
    }
  }
  if (phones.size > 0) result.phones = Array.from(phones);

  // 2. STANOWISKO — keyword matching
  const positionKeywords = [
    'prezes', 'wiceprezes', 'dyrektor', 'wicedyrektor', 'kierownik', 'menedżer', 'manager',
    'specjalista', 'koordynator', 'asystent', 'konsultant', 'inżynier', 'project manager',
    'cto', 'ceo', 'cfo', 'coo', 'cmo', 'cso', 'cio',
    'director', 'head of', 'lead', 'senior', 'junior', 'principal',
    'naczelnik', 'wojewoda', 'starosta', 'burmistrz', 'wójt', 'sołtys',
    'sekretarz', 'skarbnik', 'księgowy', 'księgowa', 'główny',
    'inspektor', 'referent', 'urzędnik', 'pracownik',
    'właściciel', 'współwłaściciel', 'partner', 'wspólnik',
    'handlowiec', 'sprzedawca', 'doradca', 'sales',
    'architekt', 'projektant', 'kontroler',
  ];
  for (const line of sigLines) {
    const lower = line.toLowerCase();
    for (const kw of positionKeywords) {
      if (lower.includes(kw)) {
        // Pomiń linie które są oczywiście emailem albo zbyt długie
        if (line.length < 120 && !line.includes('@')) {
          result.position = line.trim();
          break;
        }
      }
    }
    if (result.position) break;
  }

  // 3. FIRMA — szukaj linii z formami prawnymi
  const companyKeywords = /\b(sp\.\s*z\s*o\.?\s*o\.?|s\.a\.|sp\.\s*j\.|sp\.\s*k\.|s\.c\.|s\.r\.o\.|gmbh|ltd\.?|llc|inc\.?|company|sa\.?|spółka|przedsiębiorstwo|firma|zakład|biuro\s+projektowe|urząd|gmina|powiat|starostwo|miasto|woj\.|ministerstwo|samorząd|sklep|hotel|fundacja|stowarzyszenie|spółdzielnia)\b/i;
  for (const line of sigLines) {
    if (companyKeywords.test(line) && line.length < 200 && !line.includes('@')) {
      result.company = line.trim();
      break;
    }
  }

  // 4. MIASTO — proste matching popularnych miast PL
  const polishCities = ['warszawa', 'kraków', 'krakow', 'poznań', 'poznan', 'wrocław', 'wroclaw',
    'gdańsk', 'gdansk', 'łódź', 'lodz', 'katowice', 'lublin', 'białystok', 'bialystok',
    'szczecin', 'bydgoszcz', 'gdynia', 'częstochowa', 'czestochowa', 'radom', 'sosnowiec',
    'toruń', 'torun', 'kielce', 'rzeszów', 'rzeszow', 'gliwice', 'zabrze', 'olsztyn',
    'bielsko-biała', 'bielsko-biala', 'bielsko biała', 'tychy', 'opole', 'gorzów', 'gorzow',
    'dąbrowa', 'dabrowa', 'płock', 'plock', 'elbląg', 'elblag', 'wałbrzych', 'walbrzych',
    'włocławek', 'wloclawek', 'tarnów', 'tarnow', 'chorzów', 'chorzow', 'koszalin',
    'kalisz', 'legnica', 'grudziądz', 'grudziadz', 'jaworzno', 'jelenia góra', 'jelenia gora',
    'nowy sącz', 'nowy sacz', 'konin', 'siedlce', 'piotrków', 'piotrkow', 'lipowa',
    'oświęcim', 'oswiecim', 'chrzanów', 'chrzanow', 'wadowice', 'andrychów', 'andrychow',
  ];
  for (const line of sigLines) {
    const lower = line.toLowerCase();
    for (const city of polishCities) {
      if (lower.includes(city)) {
        result.city = line.trim();
        break;
      }
    }
    if (result.city) break;
  }

  // 5. NAZWA — z headera lub spróbuj wyciągnąć z sygnatury
  // Z headera już mamy contactName. Jeśli pusty — szukaj linii "Imię Nazwisko" (2-3 słowa, każde z wielkiej)
  if (!contactName) {
    for (const line of sigLines.slice(-10)) {
      const m = line.match(/^([A-ZŚŁŻŹĆŃÓ][a-ząćęłńóśźż]{1,20}(?:\s+[A-ZŚŁŻŹĆŃÓ][a-ząćęłńóśźż]{1,20}){1,2})\s*$/);
      if (m) { result.fullName = m[1]; break; }
    }
  }

  return result;
}

// Heurystyczna kategoryzacja kontaktu na podstawie domeny i nazwy
function categorize(email, sampleSubject = '', names = []) {
  const domain = (email.split('@')[1] || '').toLowerCase();
  const local = (email.split('@')[0] || '').toLowerCase();
  const subject = (sampleSubject || '').toLowerCase();
  const name = (names[0] || '').toLowerCase();

  // System / no-reply / notyfikacje
  if (/^(no-?reply|noreply|donotreply|mailer-daemon|postmaster|bounces?|notifications?|alerts?|info|newsletter|marketing|automat|system|robot|admin|webmaster|kontakt)/i.test(local)) return 'system';
  if (/(facebook|instagram|linkedin|twitter|google|microsoft|apple|amazon|paypal|stripe|allegro|olx|ceneo|empik|booking|airbnb|netflix|spotify|youtube)\.(com|pl|eu)$/i.test(domain)) return 'system';
  if (/(\.bzp\.|\.uzp\.|portal-zamowien|przetargi-online|biznes-polska|oferty-biznesowe|smartzamowienia|ezamowienia)/i.test(domain)) return 'system-przetargi';

  // JST (Jednostki Samorządu Terytorialnego) — gov, gmina, powiat, urząd, starostwo
  if (/\.(gov|gov\.pl)$/i.test(domain)) return 'JST';
  if (/(gmina|powiat|um\.|umig\.|urzad|starostwo|wojewodztwo|woj\.|miasto|burmistrz|wojt|sejmik|rada-)/i.test(domain)) return 'JST';
  if (/(orlik|hala-sport|miejski-osir|mosir|cosir|osir|cks|mok|gok|szkola|sp\d|liceum|gimnazjum|przedszkole|biblioteka)/i.test(domain)) return 'JST-jednostka';

  // Edukacja / NGO
  if (/\.edu\.pl$/i.test(domain)) return 'edu';
  if (/(fundacja|stowarzyszenie|klub|zwiazek|federacja|izba)/i.test(domain)) return 'NGO';

  // Prywatne (osobiste skrzynki) — może być klient B2C lub osoba prywatna
  if (/^(gmail|googlemail|yahoo|outlook|hotmail|live|wp|onet|interia|o2|tlen|poczta|gazeta|op|tenbit|vp|pl\.aol)\.(com|pl|eu|net)$/i.test(domain)) return 'private';

  // Dostawcy china/azja (rozpoznawalne domeny)
  if (/\.(cn|com\.cn|hk|sg)$/i.test(domain)) return 'B2B-asia';
  if (/(alibaba|aliexpress|made-in-china|globalsources|dhgate|1688)/i.test(domain)) return 'B2B-asia';

  // Domeny biznesowe: .pl, .com, .eu, .de, .sk, .hu, ...
  if (/\.(pl|com|eu|net|de|sk|hu|cz|at|fr|it|es|uk|co\.uk|biz)$/i.test(domain)) return 'B2B';

  return 'inne';
}

// Próba podziału name → first + last
function splitName(fullName) {
  if (!fullName) return { first: '', last: '' };
  // Usuń tytuły
  const cleaned = fullName.replace(/\b(mgr|inż\.?|dr|prof\.?|dr hab\.?|hab\.?|inz)\.?\s*/gi, '').trim();
  const parts = cleaned.split(/\s+/);
  if (parts.length === 1) return { first: parts[0], last: '' };
  if (parts.length === 2) return { first: parts[0], last: parts[1] };
  // 3+ słów: pierwsze = imię, reszta = nazwisko
  return { first: parts[0], last: parts.slice(1).join(' ') };
}

function csvEscape(v) {
  if (v === null || v === undefined) return '';
  const s = String(v);
  if (/[",\n;]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

async function main() {
  fs.writeFileSync(OUT_LOG, '');
  log('=== START parse-signatures.js ===');
  log(`TOP_N = ${TOP_N}`);

  if (!fs.existsSync(IN_RAW)) {
    throw new Error(`Brak pliku ${IN_RAW} — uruchom najpierw extract-contacts.js`);
  }
  const raw = JSON.parse(fs.readFileSync(IN_RAW, 'utf-8'));
  log(`Wczytano ${raw.contacts.length} kontaktów z ${IN_RAW}`);

  // Filter: tylko ci którzy wysłali do nas (msgCount.from > 0) ALBO są właścicielami emaila firmowego
  const candidates = raw.contacts
    .filter(c => (c.sources?.from || 0) > 0)
    .sort((a, b) => b.msgCount - a.msgCount)
    .slice(0, TOP_N);
  log(`Kandydaci do parsowania (sources.from > 0, top ${TOP_N}): ${candidates.length}`);

  const parsed = [];
  let processed = 0;
  let parseErrors = 0;

  for (const c of candidates) {
    try {
      // Pobierz pełną wiadomość od tego kontaktu (sampleMessageId — to wiadomość gdzie email pojawił się PIERWSZY raz, nie zawsze od niego, ale to sample)
      // Lepsze podejście: szukać 1 wiadomości WHERE from:c.email
      const search = await gmail(`/messages?maxResults=1&q=${encodeURIComponent('from:' + c.email)}`);
      const msgId = search.messages?.[0]?.id;
      const category = categorize(c.email, c.sampleSubject, c.names);
      if (!msgId) {
        // Fallback: użyj sampleMessageId
        if (!c.sampleMessageId) { processed++; continue; }
        const msg = await gmail(`/messages/${c.sampleMessageId}?format=full`);
        const body = extractTextBody(msg.payload);
        const sig = parseSignature(body, c.names?.[0] || '', c.email);
        const fn = c.names?.[0] || sig.fullName || '';
        const split = splitName(fn);
        parsed.push({
          email: c.email, category, fullName: fn, firstName: split.first, lastName: split.last,
          phones: sig.phones || [], position: sig.position || '', company: sig.company || '',
          location: sig.city || '', msgCount: c.msgCount, sources: c.sources,
          firstSeen: c.firstSeen, lastSeen: c.lastSeen, _bodySource: 'sampleFallback',
        });
      } else {
        const msg = await gmail(`/messages/${msgId}?format=full`);
        const body = extractTextBody(msg.payload);
        const sig = parseSignature(body, c.names?.[0] || '', c.email);
        const fn = c.names?.[0] || sig.fullName || '';
        const split = splitName(fn);
        parsed.push({
          email: c.email, category, fullName: fn, firstName: split.first, lastName: split.last,
          phones: sig.phones || [], position: sig.position || '', company: sig.company || '',
          location: sig.city || '', msgCount: c.msgCount, sources: c.sources,
          firstSeen: c.firstSeen, lastSeen: c.lastSeen, _bodySource: 'fromSearch',
        });
      }
    } catch (e) {
      parseErrors++;
      parsed.push({
        email: c.email, category: categorize(c.email, c.sampleSubject, c.names),
        fullName: c.names?.[0] || '', firstName: '', lastName: '',
        phones: [], position: '', company: '', location: '',
        msgCount: c.msgCount, sources: c.sources, firstSeen: c.firstSeen, lastSeen: c.lastSeen,
        _error: e.message,
      });
    }
    processed++;
    if (processed % 50 === 0 || processed === candidates.length) {
      log(`  ${processed}/${candidates.length} (errors: ${parseErrors}, with phone: ${parsed.filter(p => p.phones?.length > 0).length}, with position: ${parsed.filter(p => p.position).length})`);
    }
  }

  // JSON output
  fs.writeFileSync(OUT_PARSED, JSON.stringify({
    generatedAt: new Date().toISOString(),
    sourceContactsTotal: raw.contacts.length,
    candidatesProcessed: parsed.length,
    parseErrors,
    contacts: parsed,
  }, null, 2));
  log(`Zapisano JSON: ${OUT_PARSED}`);

  // CSV output
  const headers = ['category', 'email', 'firstName', 'lastName', 'fullName', 'phones', 'position', 'company', 'location', 'msgCount', 'fromCount', 'toCount', 'ccCount', 'firstSeen', 'lastSeen'];
  const rows = [headers.join(',')];
  for (const p of parsed) {
    rows.push([
      csvEscape(p.category || ''),
      csvEscape(p.email),
      csvEscape(p.firstName),
      csvEscape(p.lastName),
      csvEscape(p.fullName),
      csvEscape((p.phones || []).join(' / ')),
      csvEscape(p.position),
      csvEscape(p.company),
      csvEscape(p.location),
      p.msgCount || 0,
      p.sources?.from || 0,
      p.sources?.to || 0,
      p.sources?.cc || 0,
      csvEscape(p.firstSeen),
      csvEscape(p.lastSeen),
    ].join(','));
  }
  fs.writeFileSync(OUT_CSV, rows.join('\n'), 'utf-8');
  log(`Zapisano CSV: ${OUT_CSV}`);

  // Stats summary
  const withPhone = parsed.filter(p => p.phones?.length > 0).length;
  const withPosition = parsed.filter(p => p.position).length;
  const withCompany = parsed.filter(p => p.company).length;
  const withLocation = parsed.filter(p => p.location).length;
  log(`=== STATS ===`);
  log(`  Kontakty sparsowane: ${parsed.length}`);
  log(`  Z telefonem: ${withPhone} (${(withPhone / parsed.length * 100).toFixed(1)}%)`);
  log(`  Ze stanowiskiem: ${withPosition} (${(withPosition / parsed.length * 100).toFixed(1)}%)`);
  log(`  Z firmą: ${withCompany} (${(withCompany / parsed.length * 100).toFixed(1)}%)`);
  log(`  Z lokalizacją: ${withLocation} (${(withLocation / parsed.length * 100).toFixed(1)}%)`);
  log(`  Błędy parsowania: ${parseErrors}`);

  // Kategoryzacja stats
  const catCounts = {};
  for (const p of parsed) {
    catCounts[p.category || 'inne'] = (catCounts[p.category || 'inne'] || 0) + 1;
  }
  log(`=== KATEGORIE ===`);
  Object.entries(catCounts).sort((a, b) => b[1] - a[1]).forEach(([cat, n]) => {
    log(`  ${cat}: ${n} (${(n / parsed.length * 100).toFixed(1)}%)`);
  });

  log('=== KONIEC ===');
}

main().catch(err => {
  log(`FATAL: ${err.message}\n${err.stack}`);
  process.exit(1);
});
