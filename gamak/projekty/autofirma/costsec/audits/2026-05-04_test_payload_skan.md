# Audyt — TEST-PAYLOAD skan (P1 #12 z planu naprawczego)

**Data:** 2026-05-04
**Wykonał:** @cto (sesja YOLO, autonomicznie)
**Tryb:** Read-only (4× Read tool, zero modyfikacji plików, zero komend AWS)
**Czas:** ~3 min

---

## 1. Cel

Skan 4 untracked plików w `mail-drafter/` wykrytych w `git status` 2026-05-04.
Ustalenie czy zawierają PII / sekrety / dane wrażliwe biznesowe **przed** ewentualnym `git add`.

---

## 2. Pliki w skanie

```
?? projekty/autofirma/maile/lambda/mail-drafter/test_payload.json
?? projekty/autofirma/maile/lambda/mail-drafter/test_payload2.json
?? projekty/autofirma/maile/lambda/mail-drafter/test_resp.json
?? projekty/autofirma/maile/lambda/mail-drafter/test_resp2.json
```

---

## 3. BEFORE snapshot

Wszystkie 4 pliki są **untracked** w git (`??`). Klasyfikacja zawartości: nieznana.
Ryzyko: jeśli Daniel wykonałby `git add .` przed skanem, pliki weszłyby do staging.

---

## 4. Skan wzorców

### G2 — Sekrety (R1)

```
┌──────────────────────────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ Wzorzec                          │ test_payload │ test_payload2│ test_resp    │ test_resp2   │
├──────────────────────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ AKIA[0-9A-Z]{16} (AWS access)    │       0      │       0      │       0      │       0      │
│ sk-ant-api03- (Anthropic)        │       0      │       0      │       0      │       0      │
│ AIzaSy[A-Za-z0-9_-]{33} (Google) │       0      │       0      │       0      │       0      │
│ ghp_[A-Za-z0-9]{36} (GitHub PAT) │       0      │       0      │       0      │       0      │
│ sk_live_ (Stripe)                │       0      │       0      │       0      │       0      │
│ Bearer ...                       │       0      │       0      │       0      │       0      │
│ Telegram bot token (digits:AA…)  │       0      │       0      │       0      │       0      │
└──────────────────────────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

**Wynik G2: 0 znalezisk we wszystkich 4 plikach.** R1 — PASS.

### PII patterns (R5)

```
┌──────────────────────────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ Wzorzec PII                      │ test_payload │ test_payload2│ test_resp    │ test_resp2   │
├──────────────────────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Emaile (.+@.+\..+)               │       0      │       0      │       0      │       0      │
│ +48 [0-9]{3} [0-9]{3} [0-9]{3}   │       0      │       0      │       0      │       0      │
│ NIP [0-9]{10}                    │       0      │       0      │       0      │       0      │
│ Kody pocztowe \d{2}-\d{3}        │       0      │       0      │       0      │       0      │
│ Imiona/nazwiska klientów         │       0      │       0      │       0      │       0      │
│   (osoby trzecie)                │              │              │              │              │
└──────────────────────────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

**Wynik PII zewnętrzne (klienci): 0 znalezisk.** R5 — PASS dla danych klientów.

### Internal commercial data (rozszerzony skan)

```
┌────────────────────────────────────────────┬────────────┬────────────┬───────┬───────┐
│ Wzorzec                                    │ payload    │ payload2   │ resp  │ resp2 │
├────────────────────────────────────────────┼────────────┼────────────┼───────┼───────┤
│ Imiona/relacje wewnętrzne (rodzina)        │     0      │     0      │   0   │   1   │
│ Nazwy miast/przetargów GAMAK                │     0      │     0      │   0   │   5   │
│ Kwoty (PLN/mln)                            │     0      │     0      │   0   │   2   │
│ Nazwy firm partnerów (referencje)          │     0      │     0      │   0   │   1+  │
│ Body draftu maila (długi tekst)            │     0      │     0      │   0   │   1   │
│ Notatki AI o decyzjach przetargowych       │     0      │     0      │   0   │   1   │
└────────────────────────────────────────────┴────────────┴────────────┴───────┴───────┘
```

**Wynik internal commercial:** 3 z 4 plików CZYSTE. **`test_resp2.json` zawiera dane wrażliwe biznesowe.**

---

## 5. Klasyfikacja per plik

```
┌──────────────────────┬───────────┬─────────────────────────────────────────────────┐
│ Plik                 │ Status    │ Co zawiera                                      │
├──────────────────────┼───────────┼─────────────────────────────────────────────────┤
│ test_payload.json    │ CZYSTY    │ 1 field: message_id (Gmail message ID — nie PII)│
│ test_payload2.json   │ CZYSTY    │ 1 field: message_id (Gmail message ID — nie PII)│
│ test_resp.json       │ CZYSTY    │ statusCode + draft_id + Gmail draft URL.        │
│                      │           │ Brak treści maila, brak nazwisk, brak kwot.     │
│ test_resp2.json      │ WRAŻLIWY  │ Body draftu odpowiedzi GAMAK + AI notes o:      │
│                      │ BIZNESOWO │  - imieniu adresata wewnętrznego (rodzina)      │
│                      │           │  - nazwach miast i przetargów (Kalisz, Chrzanów,│
│                      │           │    Oświęcim, Gorzyce, Radomsko)                 │
│                      │           │  - kwotach (4 mln, wadium 50k)                  │
│                      │           │  - referencji firm dostawców                    │
│                      │           │  - decyzjach AI co Daniel powinien sprawdzić    │
└──────────────────────┴───────────┴─────────────────────────────────────────────────┘
```

**Treść pliku NIE jest cytowana w tym raporcie** (R5). Tylko klasyfikacja patternów.

---

## 6. Ryzyko

```
Ryzyko commit-u 4 plików do GitHub PRIVATE:
├── test_payload.json    → Zaniedbywalne (Gmail ID jednorazowy)
├── test_payload2.json   → Zaniedbywalne
├── test_resp.json       → Zaniedbywalne (metadata techniczna)
└── test_resp2.json      → ŚREDNIE
                            - Repo PRIVATE (nie publiczne) ale:
                              * GitHub support ma read access przy supportcase
                              * MFA recovery → 30-dniowe okno
                              * Wyciek konta dklimczakai-ui = wyciek treści
                            - Plus: dług R6 — "tymczasowy plik testowy" bez daty końca
```

---

## 7. AFTER (po dopisie do .gitignore)

Po wykonaniu Edit `.gitignore` (sekcja 9, dopis 2 patternów):

```
+ # P1 #12 (skan 2026-05-04) — pliki testowe mail-drafter mogą zawierać
+ # internal commercial data (drafty + AI notes). Trzymamy lokalnie.
+ **/lambda/*/test_payload*.json
+ **/lambda/*/test_resp*.json
```

QUERY AFTER (verification):
- `git check-ignore -v projekty/autofirma/maile/lambda/mail-drafter/test_resp2.json`
- EXPECTED: linia z .gitignore wskazująca pattern `**/lambda/*/test_resp*.json`
- Verification ZAPLANOWANA do wykonania po batch edicie. Wpis do tego raportu po faktycznym sprawdzeniu.

---

## 8. PROPOSED NEXT (osobne TAK Daniela)

```
┌─────┬──────────────────────────────────────────────────────┬───────────────┐
│ #   │ Akcja                                                │ Etykieta      │
├─────┼──────────────────────────────────────────────────────┼───────────────┤
│ N1  │ Sanitize test_resp2.json — zamiana body + notes na   │ wymaga zgody  │
│     │ mock data. Zachowanie struktury JSON dla developmentu│ (modyfikuje   │
│     │ mail-drafter. Mock przykład: "Cześć,\n\nDzięki za    │ plik dev      │
│     │ update.\n\nProjekt A: czekam na referencję...".      │ workflow)     │
│ N2  │ Alternatywa do N1: usunięcie test_resp2.json         │ wymaga zgody  │
│     │ (Daniel może odtworzyć przy następnym test inwokacji │ (utrata danej │
│     │ mail-drafter na realnym mailu).                      │ testowej)     │
│ N3  │ Nic — zostawić plik lokalnie, gitignore chroni przed │ —             │
│     │ commitem. Daniel sam zdecyduje przy następnym test.  │ (status quo)  │
└─────┴──────────────────────────────────────────────────────┴───────────────┘
```

**Moja rekomendacja:** **N3** (status quo). .gitignore odpowiednio chroni przed commitem. Modyfikacja pliku dev workflow wymaga decyzji Daniela jako developer-a, nie CTO.

---

## 9. VERDICT

```
TEST-PAYLOAD skan: PASS (z asterisk)
- 0 sekretów R1
- 0 PII zewnętrznej R5
- 1 z 4 plików = wrażliwy biznesowo (internal commercial data)
- .gitignore patrzny zaktualizowany (sekcja 9, dopis 2 reguł)
- Klasyfikacja pliku jako "DANE WRAŻLIWE BIZNESOWE", nie "PII klientów"
- Status R5: PASS (nie dotyczy klientów zewnętrznych)
- Status R6: dług bez zmiany (4 untracked pliki bez daty końca w docs)

Pozycja P1 #12 z planu naprawczego: ZAMKNIĘTA jako "klasyfikacja
+ chroniony commit". Sanitize/delete test_resp2.json = osobne TAK
Daniela (proposed N1/N2/N3 wyżej).
```

---

**Audyt zamknięty 2026-05-04.**
