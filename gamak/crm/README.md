# GAMAK CRM v0.2

Lokalny CRM dla GAMAK. Single-page web app, IndexedDB, zero deploy, zero kosztów.

## Co nowego w V0.2 (vs V0.1)

✅ **Activity timeline per kontakt/deal** — log call/email/meeting/visit/note/tender z timeline
✅ **Linked records** — tabs w modal: Info | Activities | Deals | Tasks (per kontakt) i Info | Activities | Tasks | Documents (per deal)
✅ **Multi-pipeline** — 5 pipelines GAMAK: 🏒 Lodowiska, 🎾 Padel Raze, 🏟 Nawierzchnie, 🚜 Rolby Engo, 📦 Inne. Każdy ma własne stages.
✅ **Saved views** — sidebar w Kontaktach: zapisz current filter jako named view, kliknij żeby zastosować
✅ **Bulk actions** — checkbox na każdym kontakcie, masowe Tag/Category/Status/Delete
✅ **Inline editing** — klik w komórkę Category/Status w tabeli → dropdown bez modala
✅ **Custom fields** — Settings → Custom fields → dodaj pole (text/number/date/select), pojawia się w modal kontakt/deal
✅ **Reports tab** — 4 charts (Chart.js): pipeline value bar, win rate doughnut, kontakty per kategoria horizontal bar, deals over time line
✅ **Documents/attachments** — w Deal modal tab Dokumenty: dodaj URL/ścieżkę pliku (oferty PDF, PFU, ...)
✅ **Keyboard shortcuts** — Ctrl+K search, N nowy, ? help, Esc close, vim-style g+litera (g d/c/p/t/r/f/s)
✅ **Dark mode** — przycisk 🌙/☀️ w topbarze, persist w settings

## Co działa (V0.1 + V0.2)

- ✅ Dashboard — KPIs, urgent tasks, pipeline (per active pipeline), recent contacts
- ✅ Kontakty — 1348 importowanych, search/filter/sort/pagination/saved views/bulk/inline edit
- ✅ Pipeline — multi-pipeline kanban z drag-and-drop, wartość per stage
- ✅ Tasks — dueDate, priority, deadline reminders
- ✅ Companies — manual CRUD
- ✅ Activities — timeline per kontakt/deal (6 typów: 📝📞✉️🤝🚗📋)
- ✅ Reports — 4 charts
- ✅ Documents per deal — link do plików
- ✅ Tagi + Notes
- ✅ Import/Export — CSV per encja + JSON full backup
- ✅ Custom fields
- ✅ Saved views, Bulk actions, Inline edit
- ✅ Keyboard shortcuts, Dark mode
- ✅ Global search w topbar

## Czego NIE ma (V0.3 / V0.4 roadmap)

❌ Email sync z Gmail biuro.gamak (auto-import każdego maila do activity log)
❌ AI assistance (Bedrock Haiku 4.5 — draft emaila, summarize notes, lead scoring)
❌ Multi-user / współdzielenie (Cognito + DynamoDB sync)
❌ PWA install (manifest + service worker)
❌ Mobile native
❌ Recurring tasks
❌ Reports per pipeline / per produkt / per region (konfigurowalne)
❌ Calendar integration (Google Calendar)
❌ Email tracking (open/click rates)
❌ Forecast / quotas
❌ Marketing automation
❌ BZP/UZP integration (auto-fetch przetargi)

## Jak uruchomić

### Opcja A — przez `python -m http.server` (zalecane, auto-import działa)

```bash
cd ~/Desktop/Asystenci/gamak
python -m http.server 8000
# Otwórz: http://localhost:8000/crm/
```

CRM auto-zaimportuje 1348 kontaktów z `gamak/dane/crm/kontakty.csv` przy pierwszym uruchomieniu.

### Opcja B — bez serwera (file://)

Otwórz `gamak/crm/index.html` bezpośrednio w Chrome/Edge.

⚠️ Auto-import nie zadziała przez CORS. Zaimportuj ręcznie:
1. Settings → "Import z pliku" → wybierz `gamak/dane/crm/kontakty.csv`

## Stack techniczny

- **Frontend:** Vanilla HTML + Alpine.js 3.13 + Tailwind CSS + Chart.js 4.4 (wszystkie przez CDN, zero build step)
- **Storage:** IndexedDB v2 (browser local DB)
- **Files:** 
  - `index.html` (886 linii) — struktura SPA + szablony Alpine + 4 modale + tabs
  - `app.js` (1204 linie) — logika (DB wrapper + Alpine component, IndexedDB v2, Chart.js renderers, keyboard shortcuts)
  - `style.css` (21 linii) — minimalny custom CSS
  - `README.md`

**Rozmiar:** ~85 KB total (bez CDN). Zero build step.

## Schema IndexedDB v2

```
contacts: { id, email, firstName, lastName, fullName, phones[], position, company,
            location, category, status, tags[], notes, customFields, msgCount, ... }
companies: { id, name, type, region, website, address, notes, contactIds[] }
deals: { id, name, pipelineId, stage, status, value, dueDate, contactIds[],
         companyName, tags[], notes, documents[], customFields }
tasks: { id, title, dueDate, priority, status, contactId, dealId, notes }
activities: { id, type, contactId, dealId, date, content }
pipelines: { id, name, icon, order, stages[{id, name, color}] }
savedViews: { id, name, filter, sort }
customFields: { id, entity, name, type, options[] }
settings: { key, value }
```

## Pipelines (V0.2)

🏒 **Lodowiska** — Lead → Qualified → Wizyta → PFU → Oferta → Negocjacje → Przetarg → Won/Lost
🎾 **Padel Raze** — Lead → Qualified → Wizyta → Specyfikacja → Oferta → Zamówienie → Wysyłka/Montaż → Won/Lost
🏟 **Nawierzchnie** — Lead → Qualified → Próbki → Oferta → Przetarg → Won/Lost
🚜 **Rolby Engo** — Lead → Qualified → Demo → Oferta → Przetarg → Won/Lost
📦 **Inne** — Lead → Qualified → Oferta → Won/Lost

## Activity types

📝 Notatka · 📞 Telefon · ✉️ Email · 🤝 Spotkanie · 🚗 Wizyta · 📋 Przetarg

## Skróty klawiszowe

| Skrót | Akcja |
|---|---|
| `Ctrl+K` | Globalne szukanie |
| `N` | Nowy (kontekstowy) |
| `Esc` | Zamknij modal/help |
| `?` | Pomoc skrótów |
| `g d` | Dashboard |
| `g c` | Kontakty |
| `g p` | Pipeline |
| `g t` | Zadania |
| `g r` | Reports |
| `g f` | Firmy |
| `g s` | Settings |

## Roadmap

**V0.3** (cloud + multi-user):
- AWS Lambda + DynamoDB sync (jak ai-rekomendator template)
- Cognito auth (2-5 users z różnymi rolami)
- Hosting `crm.bizneszai.pl` lub `crm.gamak.eu`
- PWA install (manifest + service worker)
- Email sync z Gmail biuro.gamak (Gmail API + Pub/Sub)

**V0.4** (AI + automatyzacje):
- AI draft emaila (Bedrock Haiku 4.5) z kontekstu notes/activities
- AI summarize długiej korespondencji
- AI lead scoring (heurystyczne + Bedrock)
- Recurring tasks (cron-like)
- Calendar integration (Google Calendar)
- Email tracking (pixel + UTM)

**V0.5** (przetargi):
- BZP/UZP scraper (auto-fetch po słowach kluczowych)
- Auto-create deal z dopasowanego przetargu
- Telegram alerts deadlinów
- Document storage S3 (zamiast linki)
- Reports advanced (per pipeline/produkt/region)

## Bezpieczeństwo

- Dane TYLKO lokalnie (IndexedDB w przeglądarce)
- Backup: Settings → Export wszystko (JSON) — zalecane raz w tygodniu
- Reset: Settings → "Wyczyść WSZYSTKO" lub DevTools → Application → IndexedDB → delete
- Po wyczyszczeniu cache przeglądarki — UTRATA WSZYSTKICH DANYCH (V0.3 cloud sync rozwiązuje)

## Co testować w V0.2 (5-10 min)

1. **Otwórz** http://localhost:8000/crm/
2. **Dark mode** (🌙 w topbarze)
3. **Kontakty** → wyszukaj `ottka` → kliknij → tab **Activities** → kliknij `📞 Telefon` → wpisz "Rozmowa o lodowisku 30x60" → Zapisz
4. Sprawdź tab **Deals** w tym samym modalu — pusto. Tab **Tasks** — pusto.
5. Zamknij modal. **Pipeline** → dropdown wybierz `🏒 Lodowiska` → `+ Nowy deal` → "Lodowisko Toruń 30x60", contactEmails `maciej.ottka@mosir.torun.pl`, value 280000, dueDate za 60 dni → tab **Dokumenty** → dodaj URL → tab **Activities** → email z notatką → Zapisz
6. Wróć do Kontaktów → kliknij Maciej Ottka → **Deals** tab — teraz pojawił się nowy deal
7. **Pipeline** → przeciągnij deal z `Qualified` do `Wizyta na obiekcie`
8. **Pipeline** → zmień dropdown na `🎾 Padel Raze` — inne stages, inne deals
9. **Kontakty** → ustaw filter `category: B2B` + `status: lead` → klik **+ Zapisz** w sidebarze → nazwa "B2B leads" → zobacz w sidebarze
10. **Kontakty** → zaznacz checkboxem 5 wierszy → kliknij `+ Tag` w bulk bar → "lodowiska-2026" → wszystkie 5 dostały tag
11. **Kontakty** → klik bezpośrednio w kolumnę `Category` → dropdown inline → zmień bez otwierania modala
12. **Reports** → zobacz 4 charts (jak nie ma deals to puste)
13. **Settings** → Custom fields → `+ Dodaj pole` → entity `deal`, name "Numer BZP", type `text` → wróć do Pipeline → edytuj deal → na dole jest pole "Numer BZP (custom)"
14. Klawiatura: `Ctrl+K` → focus search. `?` → help. `g r` → Reports. `g c` → Kontakty.

Daj znać co działa, co trzeba poprawić, co dodać do V0.3.
