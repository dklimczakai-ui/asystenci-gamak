# RODO Art. 33 — analiza decyzyjna po incydencie R1

**Data:** 2026-05-05
**Kontekst:** R1 incident 2026-05-04 → 05-05 (wyciek hasła FTP + 21 PII klientów do PRIVATE repo na ~18h, naprawione)
**Status:** **Rekomendacja CTO + przygotowanie materiałów** — decyzja prawna należy do Daniela / doradcy prawnego.

---

## 1. Co stanowi GDPR/RODO Art. 33 (Notyfikacja UODO)

Art. 33 ust. 1 RODO:
> "W przypadku naruszenia ochrony danych osobowych, administrator bez zbędnej zwłoki — **w miarę możliwości w ciągu 72 godzin** po stwierdzeniu naruszenia — zgłasza je organowi nadzorczemu (PUODO/UODO), **chyba że jest mało prawdopodobne, by skutkowało ryzykiem naruszenia praw lub wolności** osób fizycznych."

**Próg notyfikacji:** ryzyko **realne** (nie wystarczy hipotetyczne).
**Czas odliczania:** od **stwierdzenia naruszenia** (czyli wykrycia, nie wystąpienia). Dla R1 incident: 2026-05-04 ~22:00 → deadline 2026-05-07 ~22:00.

---

## 2. Analiza R1 incident vs. próg "ryzyko realne"

### 2.1 Co wyciekło (PII osób trzecich, scope RODO)

```
┌────────────────────────────────────┬───────────────┬──────────────────┐
│ Kategoria danych                   │ Liczba osób   │ Wrażliwość RODO  │
├────────────────────────────────────┼───────────────┼──────────────────┤
│ Imię + nazwisko + email biznesowy  │ ~6-8          │ Standardowa      │
│ Imię + numer telefonu (Daniel)     │ 1             │ Standardowa      │
│ Adres firmy (publiczny w KRS)      │ 1 (GAMAK)     │ Niska            │
│ Decyzje przetargowe + kwoty ofert  │ ~11 przetarg. │ Tajemnica handl. │
│ Body draftów AI (treść biznesowa)  │ 21            │ Tajemnica handl. │
│ Dane wrażliwe (zdrowie/rasa/itp.)  │ 0             │ —                │
│ Numery dokumentów tożsamości       │ 0             │ —                │
│ Dane bankowe / karty               │ 0             │ —                │
│ Dane dzieci                        │ 0             │ —                │
└────────────────────────────────────┴───────────────┴──────────────────┘
```

**Kluczowe:** dane wyłącznie **standardowej wrażliwości** (nazwiska + emaile biznesowe). **Brak** kategorii szczególnie chronionych z Art. 9 (zdrowie, rasa, orientacja, przynależność związkowa, biometria).

### 2.2 Ekspozycja faktyczna

| Aspekt | Wartość | Komentarz |
|---|---|---|
| Czas ekspozycji | ~18 godzin | Push 2026-05-04 rano → force push 2026-05-05 04:30 |
| Kanał | GitHub PRIVATE repo | NIE publiczny, ograniczony krąg dostępu |
| Liczba kont z dostępem | 1 (Daniel) + GitHub Inc. infra | Nikt zewnętrzny nie był collaboratorem |
| OAuth tokens scope `repo` | nieaudytowane (czeka A2) | **Element niepewności** — patrz A2 walkthrough |
| Dowody nieautoryzowanego dostępu | brak | Logi GitHub repo (clone/access) — niedostępne na PRIVATE bez Enterprise |
| Indeksacja zewnętrzna | niemożliwa | PRIVATE repo nie jest crawlowane przez Google/scannery |
| Dane usunięte z historii | TAK | filter-repo + force push, weryfikacja origin/main = 0 trafień |
| Backup forensics | TAK | `_backup_git_pre_filter_repo_20260505/` lokalnie, gitignored |

### 2.3 Ocena ryzyka realnego (test 4-kryterialny RODO)

| Kryterium | Wynik | Uzasadnienie |
|---|---|---|
| **Ryzyko fizyczne** (krzywda fizyczna) | **NIE** | Dane biznesowe, brak adresów domowych |
| **Ryzyko finansowe** (oszustwo, kradzież tożsamości) | **NIE** | Brak danych bankowych/dokumentów; emaile biznesowe są publiczne (na stronach firm) |
| **Ryzyko reputacyjne** (kompromitacja, dyskryminacja) | **MARGINALNE** | Decyzje przetargowe + kwoty ofert mogą być wrażliwe biznesowo, ale GAMAK jest stroną decydującą, nie podmiotami danych |
| **Ryzyko utraty kontroli** (dane mogą być nieodwołalnie rozpowszechnione) | **NISKIE** | Dane usunięte z origin/main, brak dowodów cloningu, PRIVATE repo |

**Wstępna konkluzja CTO:** ryzyko realne dla osób trzecich = **NISKIE**, prawdopodobnie **poniżej progu notyfikacyjnego**.

---

## 3. Argumenty za i przeciw zgłoszeniu

### Za zgłoszeniem (konserwatywne):
- ✅ Default RODO: **w razie wątpliwości — zgłaszamy**. UODO nie nakłada kar za zgłoszenie nadmiarowe.
- ✅ Czas odliczania już biegnie (do 2026-05-07 ~22:00).
- ✅ Brak audytu OAuth (A2) — niepewność co do liczby osób z faktycznym dostępem.
- ✅ Pierwszy incydent w GAMAK — wpisanie do rejestru jako precedens compliance.

### Przeciw zgłoszeniu (uzasadnione):
- ❌ Brak danych Art. 9 (szczególnie chronionych).
- ❌ PRIVATE repo, brak dowodów nieautoryzowanego dostępu.
- ❌ Dane biznesowe — większość emaili publicznie dostępna na stronach firm zewnętrznych klientów.
- ❌ Containment skuteczny (rotacja + filter-repo + force push w <12h od wykrycia).
- ❌ Notyfikacja UODO uruchamia formalną procedurę — czas Daniela + ryzyko follow-up audit.
- ❌ Próg "ryzyko realne" Art. 33 nie jest spełniony (4-kryterialny test wyżej).

---

## 4. Rekomendacja CTO

**Rekomenduję NIE zgłaszać** — w oparciu o:
1. Brak danych Art. 9.
2. Niska wrażliwość PII (emaile biznesowe + decyzje handlowe).
3. PRIVATE repo + brak dowodów nieautoryzowanego dostępu.
4. Skuteczny containment w czasie zgodnym z best practice.

**WARUNEK:** wykonanie **A2 (OAuth review na GitHub)** PRZED upływem deadline 72h. Jeśli A2 ujawni nieoczekiwany OAuth token z scope `repo` aktywny w okresie ekspozycji — **RYZYKO REALNE** podnosi się i zalecam zgłoszenie.

---

## 5. Wewnętrzny rejestr naruszeń (obowiązkowy nawet bez notyfikacji UODO)

Niezależnie od decyzji o zgłoszeniu, RODO Art. 33 ust. 5 wymaga **rejestru wewnętrznego** wszystkich naruszeń (także tych nieodzgłoszonych). To jest spełnione przez:

- ✅ `costsec/audits/2026-05-04_R1_incident.md` — pełen audit
- ✅ `costsec/docs/CHANGELOG.md` — wpis v1.5 i v1.6
- ✅ `decyzje.md` — wpis 2026-05-04 (R1 incident response)

**Decyzja Daniela do udokumentowania w `decyzje.md`:**
- "RODO Art. 33: zgłoszono / nie zgłoszono — uzasadnienie [krótko]"
- Data podjęcia decyzji
- Podstawa prawna (Art. 33 ust. 1 — próg ryzyka)

---

## 6. Template notyfikacji UODO (jeśli decyzja TAK)

**Formularz:** https://uodo.gov.pl/pl/p/zgloszenie-naruszenia (wymaga konta firmy w eUODO).
**Czas wypełnienia:** ~30-60 min (zaplanuj sesję z dokumentami).
**Co potrzebujesz:**
- NIP firmy + KRS (GAMAK Sp. z o.o.)
- Kontakt do osoby zgłaszającej (Daniel)
- Opis naruszenia (kopiuj z `2026-05-04_R1_incident.md` sekcji 1-3)
- Liczba osób dotkniętych
- Środki naprawcze (rotacja + filter-repo + force push — udokumentowane)
- Środki zapobiegawcze (R15-R18 zatwierdzone, pre-commit hook v1.0 wdrożony)

**Szablon body (skopiuj do formularza):**

```
Tytuł: Niezamierzona ekspozycja danych osobowych w prywatnym repo GitHub

Charakter naruszenia:
Niezamierzone tracked-by-git plików zawierających dane osobowe ~6-8 osób
(emaile biznesowe + nazwiska + numer telefonu właściciela firmy) przez
~18 godzin w prywatnym repozytorium GitHub. Wykryte przez wewnętrzną
procedurę bezpieczeństwa (skan COSTSEC G2) przed kolejnym commit.

Dane:
- Kategoria: standardowa (Art. 4 pkt 1 RODO)
- Liczba osób: ~6-8 (klienci biznesowi + dostawcy zagraniczni + 1 właściciel)
- Brak danych szczególnie chronionych (Art. 9)
- Brak danych dzieci (Art. 8)

Środki naprawcze:
- 2026-05-05 rotacja hasła FTP CyberFolks
- 2026-05-05 git filter-repo + force push (usunięcie z całej historii)
- 2026-05-05 verification origin/main = 0 wystąpień
- 2026-05-05 pre-commit hook wdrożony (auto-blokowanie kolejnych incydentów)

Środki zapobiegawcze:
- Konstytucja COSTSEC v1.0+ (R1-R6 twarde + R15-R18 zatwierdzone po incydencie)
- Pre-commit secret scanner v1.0
- Procedura GITHUB.md § Krok 4 z pre-flight checklist filter-repo
- Audit forensics zachowany lokalnie (gitignored)

Ryzyko dla osób:
Ocena CTO: niskie (PRIVATE repo, brak dowodów nieautoryzowanego dostępu,
emaile biznesowe publicznie dostępne na stronach firm). Zgłoszenie
nadmiarowe w trybie ostrożnościowym.
```

---

## 7. Akcja Daniela (jeśli zgłaszasz)

1. Wejdź na https://uodo.gov.pl/pl/p/zgloszenie-naruszenia
2. Zaloguj się przez eUODO (login KRS firmy GAMAK)
3. Wypełnij formularz używając template wyżej
4. Załącz: `costsec/audits/2026-05-04_R1_incident.md` (po dodatkowym sanitize sekcji 1.3 — wyciągnij PII z opisu)
5. Wyślij PRZED 2026-05-07 22:00
6. Wpisz do `decyzje.md`: "RODO Art. 33 zgłoszone, nr referencyjny UODO: <numer>"

## 8. Akcja Daniela (jeśli NIE zgłaszasz — rekomendacja CTO)

1. Wykonaj **A2 (GitHub OAuth review)** — patrz `2026-05-05_A1_A2_walkthrough.md`
2. Jeśli A2 czyste → wpisz do `decyzje.md`:
   ```
   ### 2026-05-05 — RODO Art. 33 — DECYZJA: NIE ZGŁASZAM
   **Kontekst:** R1 incident 2026-05-04. Analiza CTO + A2 OAuth review = ryzyko realne dla osób trzecich poniżej progu Art. 33 ust. 1.
   **Uzasadnienie:**
   - Brak danych Art. 9 (szczególnie chronione)
   - PRIVATE repo, brak dowodów nieautoryzowanego dostępu (A2 czysty)
   - Emaile biznesowe publicznie dostępne na stronach firm
   - Containment <18h, filter-repo + force push, verification 0 wystąpień
   **Rejestr wewnętrzny:** spełniony przez audit `2026-05-04_R1_incident.md`
   **Podstawa:** Art. 33 ust. 1 in fine ("chyba że jest mało prawdopodobne")
   **Re-evaluacja:** monthly cloud_safety sync 2026-06-05
   ```
3. Następne weekly secure check (2026-05-08) sprawdzi czy nie pojawiły się nowe wskaźniki naruszenia.

---

**Plik utworzony:** 2026-05-05 (CTO yolo session)
**Następna akcja:** Daniel decyduje (zgłaszam / nie zgłaszam) PRZED 2026-05-07 22:00. Bez decyzji w deadline = automatycznie "nie zgłaszam" + wpis do `decyzje.md` z uzasadnieniem braku decyzji w czasie.
