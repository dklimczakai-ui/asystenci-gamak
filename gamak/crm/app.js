// =============================================================
// GAMAK CRM v0.2 — app.js
// IndexedDB + Alpine.js
// V0.2 features:
// - Activity timeline + linked records (tabs in modals)
// - Multi-pipeline (lodowiska/padel/nawierzchnie/rolby)
// - Saved views, Bulk actions, Inline editing
// - Custom fields, Reports (Chart.js), Documents
// - Keyboard shortcuts
// =============================================================

const DB_NAME = 'gamak-crm';
const DB_VERSION = 2;

// ---- IndexedDB wrapper ----
const DB = {
  db: null,
  async open() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      // Timeout — jeśli open nie kończy w 10s, mamy blokadę (inna karta z DB v1?)
      const timeoutId = setTimeout(() => {
        reject(new Error('IndexedDB.open() timeout 10s — prawdopodobnie inna karta CRM blokuje migrację. Zamknij wszystkie karty CRM i odśwież.'));
      }, 10000);
      req.onerror = () => { clearTimeout(timeoutId); reject(req.error); };
      req.onsuccess = () => { clearTimeout(timeoutId); this.db = req.result; resolve(this.db); };
      req.onblocked = () => {
        clearTimeout(timeoutId);
        reject(new Error('IndexedDB BLOCKED — masz inną kartę CRM otwartą ze starszą wersją bazy danych. Zamknij wszystkie karty CRM i odśwież.'));
      };
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        const old = e.oldVersion;
        // V1 stores
        if (!db.objectStoreNames.contains('contacts')) {
          const s = db.createObjectStore('contacts', { keyPath: 'id' });
          s.createIndex('email', 'email', { unique: false });
          s.createIndex('category', 'category', { unique: false });
          s.createIndex('company', 'company', { unique: false });
          s.createIndex('lastSeen', 'lastSeen', { unique: false });
        }
        if (!db.objectStoreNames.contains('companies')) {
          const s = db.createObjectStore('companies', { keyPath: 'id' });
          s.createIndex('name', 'name', { unique: false });
          s.createIndex('type', 'type', { unique: false });
        }
        if (!db.objectStoreNames.contains('deals')) {
          const s = db.createObjectStore('deals', { keyPath: 'id' });
          s.createIndex('stage', 'stage', { unique: false });
          s.createIndex('status', 'status', { unique: false });
          s.createIndex('dueDate', 'dueDate', { unique: false });
          s.createIndex('pipelineId', 'pipelineId', { unique: false });
        }
        if (!db.objectStoreNames.contains('tasks')) {
          const s = db.createObjectStore('tasks', { keyPath: 'id' });
          s.createIndex('status', 'status', { unique: false });
          s.createIndex('dueDate', 'dueDate', { unique: false });
        }
        if (!db.objectStoreNames.contains('activities')) {
          const s = db.createObjectStore('activities', { keyPath: 'id' });
          s.createIndex('contactId', 'contactId', { unique: false });
          s.createIndex('dealId', 'dealId', { unique: false });
          s.createIndex('date', 'date', { unique: false });
        }
        if (!db.objectStoreNames.contains('settings')) {
          db.createObjectStore('settings', { keyPath: 'key' });
        }
        // V2 stores
        if (!db.objectStoreNames.contains('pipelines')) {
          db.createObjectStore('pipelines', { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains('savedViews')) {
          db.createObjectStore('savedViews', { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains('customFields')) {
          const s = db.createObjectStore('customFields', { keyPath: 'id' });
          s.createIndex('entity', 'entity', { unique: false });
        }
      };
    });
  },
  tx(stores, mode = 'readonly') { return this.db.transaction(stores, mode); },
  async getAll(store) {
    return new Promise((resolve, reject) => {
      const r = this.tx(store).objectStore(store).getAll();
      r.onsuccess = () => resolve(r.result);
      r.onerror = () => reject(r.error);
    });
  },
  async get(store, key) {
    return new Promise((resolve, reject) => {
      const r = this.tx(store).objectStore(store).get(key);
      r.onsuccess = () => resolve(r.result);
      r.onerror = () => reject(r.error);
    });
  },
  async put(store, value) {
    return new Promise((resolve, reject) => {
      const t = this.tx(store, 'readwrite');
      // Deep-clone to strip Alpine.js reactive Proxies
      const cleaned = JSON.parse(JSON.stringify(value));
      const r = t.objectStore(store).put(cleaned);
      r.onsuccess = () => resolve(cleaned);
      r.onerror = () => reject(r.error);
    });
  },
  async delete(store, key) {
    return new Promise((resolve, reject) => {
      const t = this.tx(store, 'readwrite');
      const r = t.objectStore(store).delete(key);
      r.onsuccess = () => resolve();
      r.onerror = () => reject(r.error);
    });
  },
  async clear(store) {
    return new Promise((resolve, reject) => {
      const t = this.tx(store, 'readwrite');
      const r = t.objectStore(store).clear();
      r.onsuccess = () => resolve();
      r.onerror = () => reject(r.error);
    });
  },
  async bulkPut(store, items) {
    return new Promise((resolve, reject) => {
      const t = this.tx(store, 'readwrite');
      const os = t.objectStore(store);
      // Deep-clone via JSON to strip Alpine.js reactive Proxies
      // (structuredClone can't handle Proxy-wrapped arrays from Alpine)
      const cleaned = JSON.parse(JSON.stringify(items));
      for (const it of cleaned) os.put(it);
      t.oncomplete = () => resolve(cleaned.length);
      t.onerror = () => reject(t.error);
    });
  }
};

// ---- Helpers ----
function uuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0; return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}
function nowISO() { return new Date().toISOString(); }
function parseCSV(text) {
  const rows = [];
  let row = [], field = '', inQuotes = false, i = 0;
  while (i < text.length) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') { field += '"'; i += 2; continue; }
        inQuotes = false; i++; continue;
      }
      field += ch; i++; continue;
    }
    if (ch === '"') { inQuotes = true; i++; continue; }
    if (ch === ',') { row.push(field); field = ''; i++; continue; }
    if (ch === '\r') { i++; continue; }
    if (ch === '\n') { row.push(field); rows.push(row); row = []; field = ''; i++; continue; }
    field += ch; i++;
  }
  if (field.length > 0 || row.length > 0) { row.push(field); rows.push(row); }
  return rows;
}
function csvEscape(v) {
  if (v === null || v === undefined) return '';
  const s = String(v);
  if (/[",\n;]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

// ---- Default pipelines GAMAK ----
const DEFAULT_PIPELINES = [
  {
    id: 'lodowiska', name: 'Lodowiska', icon: '🏒', order: 1,
    stages: [
      { id: 'lead', name: 'Lead', color: '#94a3b8' },
      { id: 'qualified', name: 'Qualified', color: '#60a5fa' },
      { id: 'site_visit', name: 'Wizyta na obiekcie', color: '#a78bfa' },
      { id: 'pfu', name: 'PFU / Specyfikacja', color: '#f59e0b' },
      { id: 'offer', name: 'Oferta złożona', color: '#fb923c' },
      { id: 'negotiation', name: 'Negocjacje', color: '#fbbf24' },
      { id: 'tender_announced', name: 'Przetarg ogłoszony', color: '#06b6d4' },
      { id: 'won', name: 'Wygrany ✅', color: '#10b981' },
      { id: 'lost', name: 'Przegrany ❌', color: '#ef4444' },
    ]
  },
  {
    id: 'padel', name: 'Padel Raze', icon: '🎾', order: 2,
    stages: [
      { id: 'lead', name: 'Lead', color: '#94a3b8' },
      { id: 'qualified', name: 'Qualified', color: '#60a5fa' },
      { id: 'site_visit', name: 'Wizyta', color: '#a78bfa' },
      { id: 'spec', name: 'Specyfikacja kortu', color: '#f59e0b' },
      { id: 'offer', name: 'Oferta', color: '#fb923c' },
      { id: 'order', name: 'Zamówienie', color: '#fbbf24' },
      { id: 'shipping', name: 'Wysyłka/Montaż', color: '#06b6d4' },
      { id: 'won', name: 'Zrealizowane ✅', color: '#10b981' },
      { id: 'lost', name: 'Przegrany ❌', color: '#ef4444' },
    ]
  },
  {
    id: 'nawierzchnie', name: 'Nawierzchnie', icon: '🏟', order: 3,
    stages: [
      { id: 'lead', name: 'Lead', color: '#94a3b8' },
      { id: 'qualified', name: 'Qualified', color: '#60a5fa' },
      { id: 'sample_sent', name: 'Próbki wysłane', color: '#a78bfa' },
      { id: 'offer', name: 'Oferta', color: '#fb923c' },
      { id: 'tender', name: 'Przetarg', color: '#06b6d4' },
      { id: 'won', name: 'Wygrany ✅', color: '#10b981' },
      { id: 'lost', name: 'Przegrany ❌', color: '#ef4444' },
    ]
  },
  {
    id: 'rolby', name: 'Rolby Engo', icon: '🚜', order: 4,
    stages: [
      { id: 'lead', name: 'Lead', color: '#94a3b8' },
      { id: 'qualified', name: 'Qualified', color: '#60a5fa' },
      { id: 'demo', name: 'Demo / Wizyta', color: '#a78bfa' },
      { id: 'offer', name: 'Oferta', color: '#fb923c' },
      { id: 'tender', name: 'Przetarg', color: '#06b6d4' },
      { id: 'won', name: 'Wygrany ✅', color: '#10b981' },
      { id: 'lost', name: 'Przegrany ❌', color: '#ef4444' },
    ]
  },
  {
    id: 'inne', name: 'Inne', icon: '📦', order: 5,
    stages: [
      { id: 'lead', name: 'Lead', color: '#94a3b8' },
      { id: 'qualified', name: 'Qualified', color: '#60a5fa' },
      { id: 'offer', name: 'Oferta', color: '#fb923c' },
      { id: 'won', name: 'Wygrany ✅', color: '#10b981' },
      { id: 'lost', name: 'Przegrany ❌', color: '#ef4444' },
    ]
  },
];

// ---- Activity types ----
const ACTIVITY_TYPES = [
  { id: 'note', name: 'Notatka', icon: '📝', color: 'bg-slate-100 text-slate-700' },
  { id: 'call', name: 'Telefon', icon: '📞', color: 'bg-blue-100 text-blue-800' },
  { id: 'email', name: 'Email', icon: '✉️', color: 'bg-emerald-100 text-emerald-800' },
  { id: 'meeting', name: 'Spotkanie', icon: '🤝', color: 'bg-purple-100 text-purple-800' },
  { id: 'visit', name: 'Wizyta', icon: '🚗', color: 'bg-amber-100 text-amber-800' },
  { id: 'tender', name: 'Przetarg', icon: '📋', color: 'bg-cyan-100 text-cyan-800' },
];

// ---- Alpine component ----
function app() {
  return {
    // === STATE ===
    ready: false,
    loadingMsg: 'Ładuję bazę danych...',
    view: 'dashboard',
    contacts: [],
    companies: [],
    deals: [],
    tasks: [],
    activities: [],
    pipelines: [],
    savedViews: [],
    customFields: [],
    activePipelineId: 'lodowiska',
    modal: null,
    modalTab: 'info',
    editing: {},
    editingActivity: null,
    toast: { visible: false, msg: '', type: 'ok' },
    showShortcutsHelp: false,
    activityTypes: ACTIVITY_TYPES,
    darkMode: false,

    // search & filters
    globalSearch: '',
    contactsFilter: { search: '', category: '', status: '', tag: '' },
    contactsSort: { field: 'msgCount', dir: 'desc' },
    contactsPage: 1,
    contactsPerPage: 50,
    tasksFilter: 'pending',
    companiesSearch: '',
    draggedDealId: null,

    // bulk + inline
    selected: [],  // array of contact ids (for bulk)
    inlineEdit: null,  // { id, field }
    inlineValue: '',

    // === INIT ===
    async init() {
      console.log('[CRM] init() START');
      try {
        console.log('[CRM] DB.open()...');
        await DB.open();
        console.log('[CRM] DB.open() OK');
        this.loadingMsg = 'Inicjalizacja...';
        await this.ensureDefaults();
        this.loadingMsg = 'Wczytuję dane...';
        await this.loadAll();
        console.log('[CRM] loadAll() OK, contacts:', this.contacts.length);

        // Sprawdź czy enriched CSV jest nowszy niż last-import → auto-aktualizuj
        let enrichedHeaders = null;
        try {
          const head = await fetch('../dane/crm/kontakty-enriched.csv', { method: 'HEAD' });
          if (head.ok) enrichedHeaders = head.headers;
        } catch (e) { /* offline/file:// */ }

        const lastImport = await DB.get('settings', 'lastImportEnriched');
        const enrichedMtime = enrichedHeaders?.get('last-modified') || null;
        const needsImport = enrichedHeaders && (!lastImport || lastImport.value !== enrichedMtime);

        if (needsImport) {
          this.loadingMsg = 'Aktualizuję kontakty (Bedrock-enriched)...';
          console.log('[CRM] Auto-import enriched (newer file detected)');
          try {
            await this.fetchAndImportEnriched();
            await DB.put('settings', { key: 'lastImportEnriched', value: enrichedMtime, at: nowISO() });
            console.log('[CRM] Enriched import OK, contacts:', this.contacts.length);
          } catch (e) {
            console.warn('[CRM] Enriched import FAIL, fallback do raw CSV:', e.message);
            // Fallback: raw CSV jeśli enriched failed
            const initFlag = await DB.get('settings', 'initialized');
            if (!initFlag) {
              try { await this.importDefaultCSV(true); } catch (e2) { /* noop */ }
              await DB.put('settings', { key: 'initialized', value: true, at: nowISO() });
            }
          }
        } else if (this.contacts.length === 0) {
          // Pierwszy raz, brak enriched (offline/file://) → import raw
          this.loadingMsg = 'Auto-import kontaktów...';
          try { await this.importDefaultCSV(true); } catch (e) { /* noop */ }
          await DB.put('settings', { key: 'initialized', value: true, at: nowISO() });
        }

        const dm = await DB.get('settings', 'darkMode');
        if (dm?.value) this.toggleDarkMode(true);

        this.setupKeyboardShortcuts();
        this.ready = true;
        console.log('[CRM] init() DONE, ready=true, contacts=', this.contacts.length);
      } catch (e) {
        console.error('[CRM] init() FATAL:', e);
        this.loadingMsg = '❌ ' + e.message;
        setTimeout(() => { this.ready = true; this.showToast(e.message, 'error'); }, 5000);
      }
    },

    async fetchAndImportEnriched() {
      const r = await fetch('../dane/crm/kontakty-enriched.csv');
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const text = await r.text();
      await this.processCSVText(text, { forceReplaceFields: ['company', 'position', 'phones', 'location', 'firstName', 'lastName', 'fullName'] });
    },

    async ensureDefaults() {
      // Pipelines
      const pipelines = await DB.getAll('pipelines');
      if (pipelines.length === 0) {
        for (const p of DEFAULT_PIPELINES) await DB.put('pipelines', p);
      }
    },

    async loadAll() {
      [this.contacts, this.companies, this.deals, this.tasks, this.activities, this.pipelines, this.savedViews, this.customFields] = await Promise.all([
        DB.getAll('contacts'),
        DB.getAll('companies'),
        DB.getAll('deals'),
        DB.getAll('tasks'),
        DB.getAll('activities'),
        DB.getAll('pipelines'),
        DB.getAll('savedViews'),
        DB.getAll('customFields'),
      ]);
      this.pipelines.sort((a, b) => (a.order || 0) - (b.order || 0));
    },

    showToast(msg, type = 'ok') {
      this.toast = { visible: true, msg, type };
      setTimeout(() => this.toast.visible = false, 3500);
    },

    // === UI HELPERS ===
    formatDate(d) {
      if (!d) return '';
      try {
        return new Date(d).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' });
      } catch { return d; }
    },
    formatDateTime(d) {
      if (!d) return '';
      try {
        return new Date(d).toLocaleString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
      } catch { return d; }
    },
    formatCurrency(n) {
      if (!n) return '0 zł';
      return new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN', maximumFractionDigits: 0 }).format(n);
    },
    daysUntil(dueDate) {
      if (!dueDate) return null;
      const today = new Date(); today.setHours(0, 0, 0, 0);
      const due = new Date(dueDate); due.setHours(0, 0, 0, 0);
      return Math.round((due - today) / 86400000);
    },
    daysUntilLabel(dueDate) {
      const d = this.daysUntil(dueDate);
      if (d === null) return '';
      if (d < 0) return `${-d}d po terminie`;
      if (d === 0) return 'dziś';
      if (d === 1) return 'jutro';
      return `za ${d}d`;
    },
    timeAgo(date) {
      if (!date) return '';
      const sec = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
      if (sec < 60) return 'przed chwilą';
      if (sec < 3600) return `${Math.floor(sec / 60)} min temu`;
      if (sec < 86400) return `${Math.floor(sec / 3600)} h temu`;
      if (sec < 2592000) return `${Math.floor(sec / 86400)} dni temu`;
      return this.formatDate(date);
    },
    categoryColor(cat) {
      switch (cat) {
        case 'B2B': return 'bg-blue-100 text-blue-800';
        case 'JST': return 'bg-purple-100 text-purple-800';
        case 'JST-jednostka': return 'bg-purple-50 text-purple-700';
        case 'edu': return 'bg-emerald-100 text-emerald-800';
        case 'NGO': return 'bg-amber-100 text-amber-800';
        case 'private': return 'bg-slate-100 text-slate-700';
        case 'system': return 'bg-red-50 text-red-600';
        case 'system-przetargi': return 'bg-red-100 text-red-700';
        case 'B2B-asia': return 'bg-cyan-100 text-cyan-800';
        case 'dostawca': return 'bg-orange-100 text-orange-800';
        default: return 'bg-slate-100 text-slate-600';
      }
    },
    priorityColor(p) {
      if (p === 'high') return 'bg-red-100 text-red-700';
      if (p === 'low') return 'bg-slate-100 text-slate-600';
      return 'bg-amber-100 text-amber-700';
    },
    activityTypeMeta(type) {
      return ACTIVITY_TYPES.find(t => t.id === type) || ACTIVITY_TYPES[0];
    },

    // === COMPUTED ===
    get filteredContacts() {
      let arr = this.contacts;
      const f = this.contactsFilter;
      if (f.category) arr = arr.filter(c => c.category === f.category);
      if (f.status) arr = arr.filter(c => c.status === f.status);
      if (f.tag) {
        const t = f.tag.toLowerCase();
        arr = arr.filter(c => (c.tags || []).some(x => x.toLowerCase().includes(t)));
      }
      if (f.search) {
        const q = f.search.toLowerCase();
        arr = arr.filter(c =>
          (c.fullName || '').toLowerCase().includes(q) ||
          (c.email || '').toLowerCase().includes(q) ||
          (c.company || '').toLowerCase().includes(q) ||
          (c.position || '').toLowerCase().includes(q) ||
          ((c.phones || []).join(' ').toLowerCase().includes(q)) ||
          (c.location || '').toLowerCase().includes(q)
        );
      }
      const { field, dir } = this.contactsSort;
      arr = [...arr].sort((a, b) => {
        let av = a[field], bv = b[field];
        if (av === undefined || av === null) av = '';
        if (bv === undefined || bv === null) bv = '';
        if (typeof av === 'string') av = av.toLowerCase();
        if (typeof bv === 'string') bv = bv.toLowerCase();
        if (av < bv) return dir === 'asc' ? -1 : 1;
        if (av > bv) return dir === 'asc' ? 1 : -1;
        return 0;
      });
      return arr;
    },
    get pagedContacts() {
      const start = (this.contactsPage - 1) * this.contactsPerPage;
      return this.filteredContacts.slice(start, start + this.contactsPerPage);
    },
    get contactsTotalPages() {
      return Math.max(1, Math.ceil(this.filteredContacts.length / this.contactsPerPage));
    },
    get filteredCompanies() {
      const q = (this.companiesSearch || '').toLowerCase();
      if (!q) return [...this.companies].sort((a, b) => (a.name || '').localeCompare(b.name || ''));
      return this.companies.filter(c =>
        (c.name || '').toLowerCase().includes(q) ||
        (c.region || '').toLowerCase().includes(q) ||
        (c.notes || '').toLowerCase().includes(q)
      ).sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    },
    get filteredTasks() {
      const f = this.tasksFilter;
      let arr = this.tasks;
      if (f === 'pending') arr = arr.filter(t => t.status !== 'done');
      else if (f === 'done') arr = arr.filter(t => t.status === 'done');
      arr = arr.map(t => ({
        ...t,
        contactName: t.contactId ? (this.contacts.find(c => c.id === t.contactId)?.fullName || '') : (t.contactEmail || ''),
        dealName: t.dealId ? (this.deals.find(d => d.id === t.dealId)?.name || '') : '',
      }));
      arr.sort((a, b) => {
        if (a.status === 'done' && b.status !== 'done') return 1;
        if (a.status !== 'done' && b.status === 'done') return -1;
        if (!a.dueDate && b.dueDate) return 1;
        if (a.dueDate && !b.dueDate) return -1;
        if (!a.dueDate && !b.dueDate) return 0;
        return new Date(a.dueDate) - new Date(b.dueDate);
      });
      return arr;
    },
    get urgentTasks() {
      const now = new Date(); now.setHours(0, 0, 0, 0);
      const horizon = new Date(now.getTime() + 7 * 86400000);
      return this.tasks
        .filter(t => t.status !== 'done' && t.dueDate)
        .map(t => ({
          ...t,
          contactName: t.contactId ? (this.contacts.find(c => c.id === t.contactId)?.fullName || '') : (t.contactEmail || ''),
          daysLeft: this.daysUntil(t.dueDate),
        }))
        .filter(t => new Date(t.dueDate) <= horizon)
        .sort((a, b) => new Date(a.dueDate) - new Date(b.dueDate));
    },
    get topRecentContacts() {
      return [...this.contacts]
        .filter(c => c.lastSeen)
        .sort((a, b) => new Date(b.lastSeen) - new Date(a.lastSeen))
        .slice(0, 10);
    },
    get winRate() {
      const won = this.deals.filter(d => d.status === 'won').length;
      const lost = this.deals.filter(d => d.status === 'lost').length;
      const total = won + lost;
      if (total === 0) return 0;
      return Math.round(won / total * 100);
    },

    // === PIPELINE LOGIC ===
    get activePipeline() {
      return this.pipelines.find(p => p.id === this.activePipelineId) || this.pipelines[0];
    },
    get activeStages() { return this.activePipeline?.stages || []; },
    dealsAtStage(stageId) {
      const pid = this.activePipelineId;
      return this.deals.filter(d => {
        if (d.pipelineId && d.pipelineId !== pid) return false;
        if (!d.pipelineId && pid !== 'lodowiska') return false; // legacy: brak pipelineId = lodowiska
        if (stageId === 'won') return d.status === 'won';
        if (stageId === 'lost') return d.status === 'lost';
        return d.stage === stageId && (d.status === 'open' || !d.status);
      });
    },

    // === CONTACTS CRUD ===
    newContact() {
      this.editing = { id: '', email: '', firstName: '', lastName: '', fullName: '', phonesStr: '', position: '', company: '', location: '', category: 'B2B', status: 'lead', tagsStr: '', notes: '', msgCount: 0, _customFields: {} };
      this.modalTab = 'info';
      this.modal = 'contact';
    },
    editContact(c) {
      this.editing = {
        ...c,
        phonesStr: (c.phones || []).join(' / '),
        tagsStr: (c.tags || []).join(', '),
        _customFields: c.customFields || {},
      };
      this.modalTab = 'info';
      this.modal = 'contact';
    },
    async saveContact() {
      if (!this.editing.email) { this.showToast('Email wymagany', 'error'); return; }
      const c = {
        ...this.editing,
        phones: (this.editing.phonesStr || '').split('/').map(s => s.trim()).filter(Boolean),
        tags: (this.editing.tagsStr || '').split(',').map(s => s.trim()).filter(Boolean),
        customFields: this.editing._customFields || {},
      };
      delete c.phonesStr; delete c.tagsStr; delete c._customFields;
      if (!c.id) c.id = uuid();
      c.updatedAt = nowISO();
      if (!c.createdAt) c.createdAt = nowISO();
      await DB.put('contacts', c);
      await this.loadAll();
      this.modal = null;
      this.showToast('Zapisano kontakt');
    },
    async deleteContact(c) {
      if (!confirm(`Usunąć kontakt ${c.email}?`)) return;
      await DB.delete('contacts', c.id);
      await this.loadAll();
      this.modal = null;
      this.showToast('Usunięto kontakt');
    },
    sortContacts(field) {
      if (this.contactsSort.field === field) {
        this.contactsSort.dir = this.contactsSort.dir === 'asc' ? 'desc' : 'asc';
      } else {
        this.contactsSort = { field, dir: 'desc' };
      }
    },
    resetContactsFilter() {
      this.contactsFilter = { search: '', category: '', status: '', tag: '' };
      this.contactsPage = 1;
    },

    // === BULK ACTIONS ===
    isSelected(id) { return this.selected.includes(id); },
    toggleSelect(id) {
      if (this.selected.includes(id)) {
        this.selected = this.selected.filter(x => x !== id);
      } else {
        this.selected = [...this.selected, id];
      }
    },
    selectAllVisible() {
      const ids = this.pagedContacts.map(c => c.id);
      const allSelected = ids.every(id => this.selected.includes(id));
      if (allSelected) {
        this.selected = this.selected.filter(id => !ids.includes(id));
      } else {
        this.selected = [...new Set([...this.selected, ...ids])];
      }
    },
    clearSelection() { this.selected = []; },
    async bulkAddTag() {
      if (this.selected.length === 0) return;
      const tag = prompt('Dodaj tag do zaznaczonych kontaktów:');
      if (!tag) return;
      for (const id of this.selected) {
        const c = this.contacts.find(x => x.id === id);
        if (!c) continue;
        c.tags = [...new Set([...(c.tags || []), tag])];
        c.updatedAt = nowISO();
        await DB.put('contacts', c);
      }
      await this.loadAll();
      this.showToast(`Dodano "${tag}" do ${this.selected.length} kontaktów`);
      this.clearSelection();
    },
    async bulkSetCategory() {
      if (this.selected.length === 0) return;
      const cat = prompt('Kategoria (B2B/JST/JST-jednostka/private/edu/NGO/dostawca/inne):');
      if (!cat) return;
      for (const id of this.selected) {
        const c = this.contacts.find(x => x.id === id);
        if (!c) continue;
        c.category = cat; c.updatedAt = nowISO();
        await DB.put('contacts', c);
      }
      await this.loadAll();
      this.showToast(`Ustawiono "${cat}" dla ${this.selected.length} kontaktów`);
      this.clearSelection();
    },
    async bulkSetStatus() {
      if (this.selected.length === 0) return;
      const s = prompt('Status (lead/active/customer/archived):');
      if (!s) return;
      for (const id of this.selected) {
        const c = this.contacts.find(x => x.id === id);
        if (!c) continue;
        c.status = s; c.updatedAt = nowISO();
        await DB.put('contacts', c);
      }
      await this.loadAll();
      this.showToast(`Ustawiono status "${s}" dla ${this.selected.length} kontaktów`);
      this.clearSelection();
    },
    async bulkDelete() {
      if (this.selected.length === 0) return;
      if (!confirm(`Usunąć ${this.selected.length} kontaktów?`)) return;
      for (const id of this.selected) await DB.delete('contacts', id);
      await this.loadAll();
      this.showToast(`Usunięto ${this.selected.length} kontaktów`);
      this.clearSelection();
    },

    // === INLINE EDITING ===
    startInlineEdit(id, field, currentValue) {
      this.inlineEdit = { id, field };
      this.inlineValue = currentValue || '';
      this.$nextTick(() => {
        const el = document.querySelector('[data-inline-edit-input]');
        if (el) { el.focus(); el.select?.(); }
      });
    },
    async commitInlineEdit() {
      if (!this.inlineEdit) return;
      const c = this.contacts.find(x => x.id === this.inlineEdit.id);
      if (!c) { this.inlineEdit = null; return; }
      c[this.inlineEdit.field] = this.inlineValue;
      c.updatedAt = nowISO();
      await DB.put('contacts', c);
      await this.loadAll();
      this.inlineEdit = null;
    },
    cancelInlineEdit() { this.inlineEdit = null; this.inlineValue = ''; },

    // === SAVED VIEWS ===
    async saveCurrentView() {
      const name = prompt('Nazwa widoku:');
      if (!name) return;
      const v = { id: uuid(), name, filter: { ...this.contactsFilter }, sort: { ...this.contactsSort }, createdAt: nowISO() };
      await DB.put('savedViews', v);
      await this.loadAll();
      this.showToast(`Zapisano widok "${name}"`);
    },
    async applyView(v) {
      this.contactsFilter = { ...v.filter };
      if (v.sort) this.contactsSort = { ...v.sort };
      this.contactsPage = 1;
      this.showToast(`Zastosowano widok "${v.name}"`);
    },
    async deleteView(v) {
      if (!confirm(`Usunąć widok "${v.name}"?`)) return;
      await DB.delete('savedViews', v.id);
      await this.loadAll();
    },

    // === DEALS CRUD ===
    newDeal() {
      this.editing = { id: '', name: '', pipelineId: this.activePipelineId, stage: this.activeStages[0]?.id || 'lead', status: 'open', value: 0, dueDate: '', companyName: '', contactEmailsStr: '', tagsStr: '', notes: '', documents: [], _customFields: {} };
      this.modalTab = 'info';
      this.modal = 'deal';
    },
    editDeal(d) {
      this.editing = {
        ...d,
        contactEmailsStr: this.contactEmailsForDeal(d).join(', '),
        tagsStr: (d.tags || []).join(', '),
        documents: d.documents || [],
        _customFields: d.customFields || {},
      };
      this.modalTab = 'info';
      this.modal = 'deal';
    },
    contactEmailsForDeal(d) {
      return (d.contactIds || []).map(id => this.contacts.find(c => c.id === id)?.email).filter(Boolean);
    },
    async saveDeal() {
      if (!this.editing.name) { this.showToast('Nazwa deala wymagana', 'error'); return; }
      const d = {
        ...this.editing,
        contactIds: this.resolveContactIdsByEmails((this.editing.contactEmailsStr || '').split(',').map(s => s.trim()).filter(Boolean)),
        tags: (this.editing.tagsStr || '').split(',').map(s => s.trim()).filter(Boolean),
        documents: this.editing.documents || [],
        customFields: this.editing._customFields || {},
      };
      delete d.contactEmailsStr; delete d.tagsStr; delete d._customFields;
      if (!d.id) d.id = uuid();
      d.updatedAt = nowISO();
      if (!d.createdAt) d.createdAt = nowISO();
      if (d.stage === 'won') d.status = 'won';
      else if (d.stage === 'lost') d.status = 'lost';
      else if (d.status === 'won' || d.status === 'lost') d.status = 'open';
      await DB.put('deals', d);
      await this.loadAll();
      this.modal = null;
      this.showToast('Zapisano deal');
    },
    async deleteDeal(d) {
      if (!confirm(`Usunąć deal "${d.name}"?`)) return;
      await DB.delete('deals', d.id);
      await this.loadAll();
      this.modal = null;
      this.showToast('Usunięto deal');
    },
    resolveContactIdsByEmails(emails) {
      return emails
        .map(e => this.contacts.find(c => c.email && c.email.toLowerCase() === e.toLowerCase())?.id)
        .filter(Boolean);
    },
    async onDealDrop(ev, stageId) {
      if (!this.draggedDealId) return;
      const d = this.deals.find(x => x.id === this.draggedDealId);
      if (!d) return;
      d.stage = stageId;
      d.pipelineId = this.activePipelineId;
      if (stageId === 'won') d.status = 'won';
      else if (stageId === 'lost') d.status = 'lost';
      else d.status = 'open';
      d.updatedAt = nowISO();
      await DB.put('deals', d);
      await this.loadAll();
      this.draggedDealId = null;
      this.showToast(`Deal → ${this.activeStages.find(s => s.id === stageId)?.name}`);
    },

    // === DOCUMENTS (per deal) ===
    addDocument() {
      const name = prompt('Nazwa dokumentu (np. Oferta_Chrzanow_v2.pdf):');
      if (!name) return;
      const url = prompt('URL lub ścieżka pliku:');
      if (!url) return;
      this.editing.documents = [...(this.editing.documents || []), {
        id: uuid(), name, url, addedAt: nowISO()
      }];
    },
    removeDocument(docId) {
      this.editing.documents = (this.editing.documents || []).filter(d => d.id !== docId);
    },

    // === TASKS CRUD ===
    newTask() {
      this.editing = { id: '', title: '', dueDate: '', priority: 'med', status: 'pending', contactEmail: '', dealName: '', notes: '' };
      this.modalTab = 'info';
      this.modal = 'task';
    },
    editTask(t) {
      const c = t.contactId ? this.contacts.find(c => c.id === t.contactId) : null;
      const d = t.dealId ? this.deals.find(x => x.id === t.dealId) : null;
      this.editing = { ...t, contactEmail: c?.email || t.contactEmail || '', dealName: d?.name || '' };
      this.modalTab = 'info';
      this.modal = 'task';
    },
    async saveTask() {
      if (!this.editing.title) { this.showToast('Tytuł wymagany', 'error'); return; }
      const t = { ...this.editing };
      if (t.contactEmail) {
        const c = this.contacts.find(c => c.email && c.email.toLowerCase() === t.contactEmail.toLowerCase());
        if (c) t.contactId = c.id;
      }
      delete t.contactEmail; delete t.dealName;
      if (!t.id) t.id = uuid();
      t.updatedAt = nowISO();
      if (!t.createdAt) t.createdAt = nowISO();
      await DB.put('tasks', t);
      await this.loadAll();
      this.modal = null;
      this.showToast('Zapisano zadanie');
    },
    async deleteTask(t) {
      if (!confirm(`Usunąć zadanie "${t.title}"?`)) return;
      await DB.delete('tasks', t.id);
      await this.loadAll();
      this.modal = null;
      this.showToast('Usunięto zadanie');
    },
    async toggleTask(t) {
      const upd = { ...t, status: t.status === 'done' ? 'pending' : 'done', updatedAt: nowISO() };
      await DB.put('tasks', upd);
      await this.loadAll();
    },

    // === COMPANIES CRUD ===
    newCompany() {
      this.editing = { id: '', name: '', type: 'B2B', region: '', website: '', address: '', notes: '' };
      this.modalTab = 'info';
      this.modal = 'company';
    },
    editCompany(c) { this.editing = { ...c }; this.modalTab = 'info'; this.modal = 'company'; },
    async saveCompany() {
      if (!this.editing.name) { this.showToast('Nazwa wymagana', 'error'); return; }
      const c = { ...this.editing };
      if (!c.id) c.id = uuid();
      c.updatedAt = nowISO();
      if (!c.createdAt) c.createdAt = nowISO();
      await DB.put('companies', c);
      await this.loadAll();
      this.modal = null;
      this.showToast('Zapisano firmę');
    },
    async deleteCompany(c) {
      if (!confirm(`Usunąć firmę "${c.name}"?`)) return;
      await DB.delete('companies', c.id);
      await this.loadAll();
      this.modal = null;
      this.showToast('Usunięto firmę');
    },

    // === ACTIVITIES (timeline + linked) ===
    activitiesForContact(cid) {
      return this.activities.filter(a => a.contactId === cid).sort((a, b) => new Date(b.date) - new Date(a.date));
    },
    activitiesForDeal(did) {
      return this.activities.filter(a => a.dealId === did).sort((a, b) => new Date(b.date) - new Date(a.date));
    },
    dealsForContact(cid) {
      return this.deals.filter(d => (d.contactIds || []).includes(cid));
    },
    tasksForContact(cid) {
      return this.tasks.filter(t => t.contactId === cid);
    },
    contactsForDeal(did) {
      const d = this.deals.find(x => x.id === did);
      if (!d) return [];
      return (d.contactIds || []).map(cid => this.contacts.find(c => c.id === cid)).filter(Boolean);
    },
    tasksForDeal(did) {
      return this.tasks.filter(t => t.dealId === did);
    },
    newActivity(type) {
      this.editingActivity = {
        id: '', type, content: '',
        contactId: this.editing.id || null,
        dealId: this.editing.id && this.modal === 'deal' ? this.editing.id : null,
        date: nowISO(),
      };
    },
    async saveActivity() {
      if (!this.editingActivity?.content) {
        this.showToast('Treść aktywności wymagana', 'error'); return;
      }
      const a = { ...this.editingActivity };
      if (!a.id) a.id = uuid();
      if (!a.createdAt) a.createdAt = nowISO();
      // Set proper contact/deal id based on context
      if (this.modal === 'contact') a.contactId = this.editing.id;
      if (this.modal === 'deal') a.dealId = this.editing.id;
      await DB.put('activities', a);
      this.activities = await DB.getAll('activities');
      this.editingActivity = null;
      this.showToast('Zapisano aktywność');
    },
    cancelActivity() { this.editingActivity = null; },
    async deleteActivity(a) {
      if (!confirm('Usunąć aktywność?')) return;
      await DB.delete('activities', a.id);
      this.activities = await DB.getAll('activities');
    },

    // === CUSTOM FIELDS ===
    customFieldsFor(entity) {
      return this.customFields.filter(f => f.entity === entity);
    },
    async addCustomField() {
      const entity = prompt('Entity (contact/deal):');
      if (!['contact', 'deal'].includes(entity)) { this.showToast('Wpisz "contact" lub "deal"', 'error'); return; }
      const name = prompt('Nazwa pola:');
      if (!name) return;
      const type = prompt('Typ (text/number/date/select):');
      if (!['text', 'number', 'date', 'select'].includes(type)) { this.showToast('Typ: text/number/date/select', 'error'); return; }
      let options = [];
      if (type === 'select') {
        const opts = prompt('Opcje (oddziel przecinkami):');
        options = (opts || '').split(',').map(s => s.trim()).filter(Boolean);
      }
      const f = { id: uuid(), entity, name, type, options, createdAt: nowISO() };
      await DB.put('customFields', f);
      await this.loadAll();
      this.showToast('Dodano custom field');
    },
    async deleteCustomField(f) {
      if (!confirm(`Usunąć pole "${f.name}"?`)) return;
      await DB.delete('customFields', f.id);
      await this.loadAll();
    },

    // === MODAL ===
    closeModal() {
      this.modal = null;
      this.editing = {};
      this.modalTab = 'info';
      this.editingActivity = null;
    },

    // === GLOBAL SEARCH ===
    onGlobalSearch() {
      if (!this.globalSearch) return;
      this.contactsFilter.search = this.globalSearch;
      this.view = 'contacts';
      this.contactsPage = 1;
    },

    // === IMPORT/EXPORT ===
    async importDefaultCSV(silent = false) {
      let text;
      try {
        const r = await fetch('../dane/crm/kontakty.csv');
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        text = await r.text();
      } catch (e) {
        if (silent) throw e;
        this.showToast('Nie znaleziono ../dane/crm/kontakty.csv (uruchom python -m http.server). Użyj "Import z pliku".', 'error');
        return;
      }
      await this.processCSVText(text);
      if (!silent) this.showToast('Zaimportowano kontakty');
    },
    async importEnrichedCSV() {
      // Re-import z kontakty-enriched.csv (po Bedrock Haiku) — FORCE REPLACE company/position/phones/location
      // Zachowuje: status, tags, notes, customFields (ręczne edycje w CRM)
      // ZERO CONFIRM — po prostu robi.
      try {
        await this.fetchAndImportEnriched();
        // Update lastImportEnriched timestamp
        try {
          const head = await fetch('../dane/crm/kontakty-enriched.csv', { method: 'HEAD' });
          await DB.put('settings', { key: 'lastImportEnriched', value: head.headers.get('last-modified'), at: nowISO() });
        } catch (e) { /* noop */ }
        this.showToast(`✅ Zaimportowano ${this.contacts.length} kontaktów (Bedrock-enriched)`);
      } catch (e) {
        this.showToast('Nie znaleziono kontakty-enriched.csv. Uruchom node enrich-contacts.js', 'error');
      }
    },
    async importContactsCSV(ev) {
      const f = ev.target.files[0];
      if (!f) return;
      const text = await f.text();
      await this.processCSVText(text);
      ev.target.value = '';
      this.showToast('Zaimportowano CSV');
    },
    async processCSVText(text, opts = {}) {
      const rows = parseCSV(text);
      if (rows.length === 0) return;
      const headers = rows[0].map(h => h.trim());
      const records = [];
      for (let i = 1; i < rows.length; i++) {
        const row = rows[i];
        if (row.every(v => !v)) continue;
        const obj = {};
        for (let j = 0; j < headers.length; j++) obj[headers[j]] = row[j] || '';
        records.push(obj);
      }
      const existing = this.contacts.reduce((m, c) => { if (c.email) m[c.email.toLowerCase()] = c; return m; }, {});
      const force = opts.forceReplaceFields || [];
      const isForced = (f) => force.includes(f);
      // Smart merge: prefer new if not empty, OR force replace (even with empty)
      const merge = (newVal, oldVal, fieldName) => {
        if (isForced(fieldName)) return (newVal !== undefined && newVal !== null) ? newVal : '';
        return newVal || oldVal || '';
      };
      const toSave = [];
      for (const r of records) {
        if (!r.email) continue;
        const e = r.email.toLowerCase();
        const ex = existing[e] || {};
        const phones = (r.phones || '').split('/').map(s => s.trim()).filter(Boolean);
        const phonesMerged = isForced('phones') ? phones : (phones.length > 0 ? phones : (ex.phones || []));
        toSave.push({
          id: ex.id || uuid(),
          email: e,
          firstName: merge(r.firstName, ex.firstName, 'firstName'),
          lastName: merge(r.lastName, ex.lastName, 'lastName'),
          fullName: merge(r.fullName, ex.fullName, 'fullName'),
          phones: phonesMerged,
          position: merge(r.position, ex.position, 'position'),
          company: merge(r.company, ex.company, 'company'),
          location: merge(r.location, ex.location, 'location'),
          category: r.category || ex.category || 'B2B',
          status: ex.status || 'lead',  // never overwrite manual status
          tags: ex.tags || [],          // never overwrite manual tags
          notes: ex.notes || '',         // never overwrite manual notes
          msgCount: parseInt(r.msgCount || ex.msgCount || 0, 10),
          fromCount: parseInt(r.fromCount || 0, 10),
          toCount: parseInt(r.toCount || 0, 10),
          ccCount: parseInt(r.ccCount || 0, 10),
          firstSeen: r.firstSeen || ex.firstSeen || '',
          lastSeen: r.lastSeen || ex.lastSeen || '',
          customFields: ex.customFields || {},
          createdAt: ex.createdAt || nowISO(),
          updatedAt: nowISO(),
        });
      }
      await DB.bulkPut('contacts', toSave);
      await this.loadAll();
    },

    // === EXPORT ===
    download(filename, content, mime = 'text/plain') {
      const blob = new Blob([content], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = filename; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
    exportContactsCSV() {
      const headers = ['category', 'email', 'firstName', 'lastName', 'fullName', 'phones', 'position', 'company', 'location', 'status', 'tags', 'msgCount', 'firstSeen', 'lastSeen'];
      const rows = [headers.join(',')];
      for (const c of this.filteredContacts) {
        rows.push([
          csvEscape(c.category || ''), csvEscape(c.email), csvEscape(c.firstName), csvEscape(c.lastName),
          csvEscape(c.fullName), csvEscape((c.phones || []).join(' / ')), csvEscape(c.position),
          csvEscape(c.company), csvEscape(c.location), csvEscape(c.status || ''),
          csvEscape((c.tags || []).join(', ')), c.msgCount || 0, csvEscape(c.firstSeen), csvEscape(c.lastSeen),
        ].join(','));
      }
      this.download(`gamak-crm-kontakty-${new Date().toISOString().split('T')[0]}.csv`, rows.join('\n'), 'text/csv');
    },
    exportDealsCSV() {
      const headers = ['name', 'pipeline', 'stage', 'status', 'value', 'dueDate', 'companyName', 'contactEmails', 'tags', 'notes'];
      const rows = [headers.join(',')];
      for (const d of this.deals) {
        rows.push([
          csvEscape(d.name), csvEscape(d.pipelineId || ''), csvEscape(d.stage), csvEscape(d.status), d.value || 0,
          csvEscape(d.dueDate), csvEscape(d.companyName || ''),
          csvEscape(this.contactEmailsForDeal(d).join('; ')),
          csvEscape((d.tags || []).join(', ')), csvEscape(d.notes || ''),
        ].join(','));
      }
      this.download(`gamak-crm-deals-${new Date().toISOString().split('T')[0]}.csv`, rows.join('\n'), 'text/csv');
    },
    async exportAllJSON() {
      const data = {
        version: 2,
        exportedAt: nowISO(),
        contacts: this.contacts,
        companies: this.companies,
        deals: this.deals,
        tasks: this.tasks,
        activities: this.activities,
        pipelines: this.pipelines,
        savedViews: this.savedViews,
        customFields: this.customFields,
      };
      this.download(`gamak-crm-backup-${new Date().toISOString().split('T')[0]}.json`, JSON.stringify(data, null, 2), 'application/json');
    },
    async importJSON(ev) {
      const f = ev.target.files[0];
      if (!f) return;
      if (!confirm(`UWAGA: Import nadpisze WSZYSTKIE dane. Kontynuować?`)) {
        ev.target.value = ''; return;
      }
      const text = await f.text();
      const data = JSON.parse(text);
      const stores = ['contacts', 'companies', 'deals', 'tasks', 'activities', 'pipelines', 'savedViews', 'customFields'];
      for (const s of stores) await DB.clear(s);
      for (const s of stores) {
        if (data[s] && Array.isArray(data[s]) && data[s].length > 0) {
          await DB.bulkPut(s, data[s]);
        }
      }
      await this.loadAll();
      ev.target.value = '';
      this.showToast('Zaimportowano JSON');
    },

    async resetAllData() {
      if (!confirm(`UWAGA: skasować WSZYSTKIE dane CRM (kontakty, deals, tasks, activities, pipelines, ...)?`)) return;
      if (!confirm(`To NIE da się cofnąć. Na pewno?`)) return;
      const stores = ['contacts', 'companies', 'deals', 'tasks', 'activities', 'pipelines', 'savedViews', 'customFields', 'settings'];
      for (const s of stores) await DB.clear(s);
      await this.ensureDefaults();
      await this.loadAll();
      this.showToast('Wyczyszczono wszystkie dane');
    },

    // === REPORTS (Chart.js) ===
    chartInstances: {},
    initReports() {
      // Wywołaj po przejściu do view='reports'
      this.$nextTick(() => {
        this.renderChart_pipelineValue();
        this.renderChart_winRate();
        this.renderChart_topCategories();
        this.renderChart_dealsOverTime();
      });
    },
    destroyChart(key) {
      if (this.chartInstances[key]) {
        this.chartInstances[key].destroy();
        delete this.chartInstances[key];
      }
    },
    renderChart_pipelineValue() {
      const ctx = document.getElementById('chart-pipeline-value');
      if (!ctx || typeof Chart === 'undefined') return;
      this.destroyChart('pipelineValue');
      const stages = this.activeStages;
      const labels = stages.map(s => s.name);
      const data = stages.map(s => this.dealsAtStage(s.id).reduce((sum, d) => sum + (d.value || 0), 0));
      const colors = stages.map(s => s.color);
      this.chartInstances.pipelineValue = new Chart(ctx, {
        type: 'bar', data: { labels, datasets: [{ label: 'Wartość (PLN)', data, backgroundColor: colors }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
      });
    },
    renderChart_winRate() {
      const ctx = document.getElementById('chart-win-rate');
      if (!ctx || typeof Chart === 'undefined') return;
      this.destroyChart('winRate');
      const won = this.deals.filter(d => d.status === 'won').length;
      const lost = this.deals.filter(d => d.status === 'lost').length;
      const open = this.deals.filter(d => d.status === 'open' || !d.status).length;
      this.chartInstances.winRate = new Chart(ctx, {
        type: 'doughnut',
        data: { labels: ['Won', 'Lost', 'Open'], datasets: [{ data: [won, lost, open], backgroundColor: ['#10b981', '#ef4444', '#94a3b8'] }] },
        options: { responsive: true, maintainAspectRatio: false }
      });
    },
    renderChart_topCategories() {
      const ctx = document.getElementById('chart-categories');
      if (!ctx || typeof Chart === 'undefined') return;
      this.destroyChart('categories');
      const counts = {};
      this.contacts.forEach(c => counts[c.category || 'inne'] = (counts[c.category || 'inne'] || 0) + 1);
      const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
      this.chartInstances.categories = new Chart(ctx, {
        type: 'bar',
        data: { labels: sorted.map(s => s[0]), datasets: [{ label: 'Kontakty', data: sorted.map(s => s[1]), backgroundColor: '#0284c7' }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
      });
    },
    renderChart_dealsOverTime() {
      const ctx = document.getElementById('chart-deals-time');
      if (!ctx || typeof Chart === 'undefined') return;
      this.destroyChart('dealsTime');
      // Group deals by month created
      const byMonth = {};
      this.deals.forEach(d => {
        if (!d.createdAt) return;
        const key = d.createdAt.substring(0, 7); // YYYY-MM
        byMonth[key] = (byMonth[key] || 0) + 1;
      });
      const sortedKeys = Object.keys(byMonth).sort();
      this.chartInstances.dealsTime = new Chart(ctx, {
        type: 'line',
        data: { labels: sortedKeys, datasets: [{ label: 'Nowe deals', data: sortedKeys.map(k => byMonth[k]), borderColor: '#0284c7', backgroundColor: 'rgba(2,132,199,0.1)', fill: true, tension: 0.3 }] },
        options: { responsive: true, maintainAspectRatio: false }
      });
    },

    // === DARK MODE ===
    async toggleDarkMode(force) {
      this.darkMode = (force !== undefined) ? !!force : !this.darkMode;
      document.documentElement.classList.toggle('dark', this.darkMode);
      await DB.put('settings', { key: 'darkMode', value: this.darkMode });
    },

    // === KEYBOARD SHORTCUTS ===
    setupKeyboardShortcuts() {
      window.addEventListener('keydown', (e) => {
        const inInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);
        // ESC zawsze działa
        if (e.key === 'Escape') {
          if (this.modal) { this.closeModal(); return; }
          if (this.showShortcutsHelp) { this.showShortcutsHelp = false; return; }
          if (this.inlineEdit) { this.cancelInlineEdit(); return; }
          if (inInput) document.activeElement.blur();
          return;
        }
        if (inInput) return;
        // Ctrl+K → focus global search
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
          e.preventDefault();
          document.querySelector('input[placeholder*="globalnie"]')?.focus();
          return;
        }
        // Single letter shortcuts
        switch (e.key) {
          case 'g': // 'g' then letter (vim-like)
            this._gPressed = true;
            setTimeout(() => this._gPressed = false, 1000);
            break;
          case 'd': if (this._gPressed) { this.view = 'dashboard'; this._gPressed = false; } break;
          case 'c': if (this._gPressed) { this.view = 'contacts'; this._gPressed = false; } break;
          case 'p': if (this._gPressed) { this.view = 'pipeline'; this._gPressed = false; } break;
          case 't': if (this._gPressed) { this.view = 'tasks'; this._gPressed = false; } break;
          case 'r': if (this._gPressed) { this.view = 'reports'; this.initReports(); this._gPressed = false; } break;
          case 'f': if (this._gPressed) { this.view = 'companies'; this._gPressed = false; } break;
          case 's': if (this._gPressed) { this.view = 'settings'; this._gPressed = false; } break;
          case 'n':
            if (!this._gPressed) {
              if (this.view === 'contacts') this.newContact();
              else if (this.view === 'pipeline') this.newDeal();
              else if (this.view === 'tasks') this.newTask();
              else if (this.view === 'companies') this.newCompany();
            }
            break;
          case '?':
            this.showShortcutsHelp = true;
            break;
        }
      });
    },
  };
}

window.app = app;
