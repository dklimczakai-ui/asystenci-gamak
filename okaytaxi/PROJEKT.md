# PROJEKT: okaytaxi.pl — przebudowa strony

**Klient:** Okay Taxi Sp. z o.o. — Bielsko-Biała
**Realizacja:** 12-13.04.2026
**Wycena finalna:** **5 000 zł netto** (6 150 zł brutto) — po researchu rynkowym

---

## CO ZOSTAŁO WYKONANE

### Podstrony (12 × custom, napisane od zera)

| # | Podstrona | URL | Kluczowe elementy |
|---|-----------|-----|-------------------|
| 1 | Strona główna | `/` | Hero, 6 usług, dlaczego my, aplikacja, 8 partnerów, CTA, FAQ, SEO content |
| 2 | O nas | `/o-nas/` | Historia (22 lata VIP, 2018), 6 wartości, flota 100+, galeria 8 zdjęć, statystyki dark |
| 3 | Flota | `/flota/` | 111 pojazdów, 4 ikony wyposażenia, galeria 13 modeli (Toyota/Hyundai/Škoda/Mercedes...), bezpieczeństwo |
| 4 | Cennik | `/cennik/` | 4 zakładki (Bielsko / Miasta / Lotniska / Dodatkowe), 12 kart cenowych, taryfy z godzinami |
| 5 | Aplikacja | `/aplikacja/` | Dark hero, 3 statystyki (11 297 pobrań, 4,1/5, 31%), film YouTube + film Facebook Reels, 9 funkcji |
| 6 | Praca | `/praca/` | 3 formy (Partner/Kierowca u partnera/Wynajem), formularz rekrutacyjny z JS warunkową logiką miast |
| 7 | Programy bezgotówkowe | `/programy-bezgotowkowe/` | 3 zakładki (Firmy/Senior/Dziecko), 8 partnerów, grafiki tematyczne |
| 8 | Reklama na szybie | `/reklama-na-szybie/` | Mobilny billboard, 6 zalet, dark sekcja "ograniczona dostępność", 4 kroki |
| 9 | Dla niepełnosprawnych | `/dla-niepelnosprawnych/` | Opis programu, 3 punkty zabezpieczenia (6 min), galeria 5 zdjęć pojazdu z rampą, program 1% |
| 10 | Regulamin | `/regulamin/` | 10 paragrafów + Załącznik RODO, dane spółki (KRS/NIP/REGON) |
| 11 | Polityka prywatności | `/polityka-prywatnosci/` | 17 paragrafów, 14 definicji, 4 rodzaje cookies, partnerzy zewnętrzni |
| 12 | RODO | `/rodo/` | Skrócona informacja RODO, 7 praw użytkownika, box kontaktowy |

### Technologia

- **CSS:** 2500+ linii (glassmorphism, mesh gradients, animacje spring)
- **HTML:** 12 plików × 200-700 linii = ~6000 linii
- **JS:** script.js (counters, smooth scroll, tabs, nav, reveal) + cookie banner
- **Responsywny:** 3 breakpointy (1024px, 768px, 600px)

### SEO / LEO / GEO

- **Meta tagi LEO:** subject, classification, topic, summary na każdej stronie
- **Schema.org JSON-LD:** 30+ schem na całym serwisie:
  - TaxiService, Organization, AboutPage, WebPage
  - Service + OfferCatalog (programy, cennik)
  - FAQPage (∑ ~80 pytań)
  - MobileApplication (aplikacja)
  - VideoObject (YouTube)
  - JobPosting (praca)
  - ItemList (marki floty)
  - BreadcrumbList (na każdej stronie)
  - SpeakableSpecification
  - PriceSpecification
- **OpenGraph + Twitter Cards** — pełne na każdej stronie
- **geo.position + geo.region + ICBM** — Bielsko-Biała, 49.8224;19.0584
- **SEO content block** — naturalny tekst na dole każdej strony dla AI Overviews

### RODO Compliance

- **Baner cookies** (slide-up od dołu) na wszystkich 32 plikach HTML
- **4 opcje granularne:** niezbędne, analityczne, marketingowe, funkcjonalne
- **3 główne przyciski równej wielkości** (brak dark patterns)
- **localStorage** pod kluczem `okaytaxi_cookie_consent_v1`
- **Link "Ustawienia cookies"** w footerze — reset zgody
- **Pełny wielojęzyczny baner** dostępny i responsywny

### Formularze

- **Formularz rekrutacyjny** `/praca/`:
  - 12 pól (miasto, forma, imię, nazwisko, email, telefon, kod, data urodzenia, prawo jazdy, firma tak/nie, auto tak/nie, uwagi, RODO)
  - JS warunkowy ("Kierowca u partnera" tylko dla Cieszyn)
  - Dropdown miast (4 prawdziwe z oryginału)
  - mailto action → marketing@okaytaxi.pl

### Media / zasoby

- **8 logotypów partnerów** — usunięcie białego tła (sharp.js + custom algorytm)
- **5 zdjęć niepełnosprawnych** — pobrane z oryginalnego serwera
- **13 zdjęć floty** — pobrane + dodane do galerii
- **8 zdjęć galerii O nas** — pobrane + używane na stronie
- **Embed YouTube** (Tg4oEYKELhw) + **embed Facebook Reels** (767637814281305)
- **Grafika dzieci + senior** — oficjalne z serwera WP

### Cleanup

- Usunięto nieaktualne: folder `ambasador` (przeniesiony na `praca`), `okayka`, `partner-okayka`, `program-okayka`, `towar`, `reklama-na-tablety`, `reklama-na-tabletach`
- Wszystkie wzmianki "Okayka" usunięte ze stron i JSON-LD
- "Dostępność" usunięta z menu głównego
- Sklep usunięty
- Synchronizacja footera w 32 plikach (jeden spójny)

### Prawdziwe dane firmy

- **Okay Taxi Sp. z o.o.**
- ul. Wincentego Witosa 170, 43-300 Bielsko-Biała
- KRS: 0000735790 · NIP: 9372713505 · REGON: 380471943
- Kapitał zakładowy: 5 000 zł
- Rok założenia: **1 czerwca 2018** (22 lata doświadczenia VIP wcześniej)
- **111 pojazdów** w flocie
- **17 miast Podbeskidzia** obsługiwanych
- Partnerzy: Galeria Sfera, Teatr Polski, Casinos Poland, Hotel Cubus
- Eventy: 90'Festival, Miss Polski, Miss Polonia, FashionPhilosophy
- Email: biuro@okaytaxi.pl (RODO) / marketing@okaytaxi.pl (ogólny)
- Tel: 720 53 53 53

---

## WYCENA

### Research rynkowy (PL 2026)

| Segment | Zakres | Widełki |
|---------|--------|---------|
| Freelancer szablon WP | 3-5 podstron, bez SEO | 1 500 – 3 500 zł |
| Freelancer samodzielny | 5-8 podstron, podstawowe SEO | 4 000 – 8 000 zł |
| **Freelancer PRO** | **10-15 podstron, custom, SEO, RODO** | **8 000 – 18 000 zł** |
| Mała agencja | 12 podstron, projekt, copy, PM | 15 000 – 35 000 zł |
| Agencja interaktywna | Pełny pakiet + UX + CMS | 25 000 – 80 000 zł |

### Początkowa rekomendacja CSO

- Starter: 9 000 zł netto
- **Recommended: 12 500 zł netto**
- Premium: 18 000 zł netto

### Decyzja klienta (właściciel projektu)

**5 000 zł netto** (6 150 zł brutto)

**Uzasadnienie decyzji:**
- Pierwsza komercyjna strona — priorytet to zdobyć referencję + case study
- Klient lokalny (znajomy biznes) — cena przyjacielska
- Budowa portfolio → kolejny klient pójdzie za pełną stawkę 12-15 tys.
- Niskie koszty własne (godziny spędzone przy AI-assisted workflow)

**Realna wartość rynkowa tego projektu:** 10 000 – 15 000 zł netto.
**Sprzedaż poniżej wartości:** o ~50-60%. Świadoma decyzja.

---

## NAUKA Z PROJEKTU

### Co zadziałało
- WordPress WP JSON API + curl do pobierania realnej treści z oryginału
- Skrypty Node.js do masowych zmian w 32 plikach (cookie banner injection, footer sync, link rename)
- Sharp.js do usuwania białych teł z logotypów
- Embed Facebook Reels jako pionowy iframe (potem poziomy)

### Co następnym razem
- **Research klienta ZANIM zaczniesz robić** — w tym projekcie 3x przepisywałem zawartość bo najpierw "wymyślałem" dane zamiast wyciągać prawdziwe (rok 2021 vs 2018, 8 miast vs 17, wymyślone formy współpracy)
- **Formspree lub Web3Forms** — mailto formularze są słabe, warto od razu zintegrować
- **Deploy na statyczny hosting** (Netlify/Vercel) — bez WordPress'a prosto z folderu
- **Lighthouse audit** przed wdrożeniem
- **Cena minimum 9 000 zł netto** — nawet przy "przyjacielskim" case study

---

## NASTĘPNE KROKI

- [ ] Wystaw fakturę: 5 000 zł netto / 6 150 zł brutto
- [ ] Deploy na serwer klienta (opcjonalnie: Netlify free tier dla testu)
- [ ] Google Search Console: zgłoś stronę + submit sitemap
- [ ] Google Business Profile: aktualizuj link strony
- [ ] Formspree: jeśli klient chce działający formularz → konfiguracja (+500 zł)
- [ ] 17 podstron miast (Andrychów, Brzesce, Cieszyn, Czechowice-Dziedzice, Jasienica, Kęty, Kozy, Międzybrodzie, Milówka, Oświęcim, Skoczów, Szczyrk, Ustroń, Wadowice, Wilkowice, Wisła, Żywiec) — istnieją jako szablony, do przerobienia w kolejnym etapie
- [ ] Case study do portfolio (przed/po screeny)
- [ ] Referencję pisemną od klienta

---

*Ostatnia aktualizacja: 13.04.2026*
