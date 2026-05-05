# COSTSEC — Cost Security DNA

Układ odpornościowy firmy GAMAK. Warstwa pozioma w AUTOFIRMA — pilnuje kosztów, bezpieczeństwa, sekretów, danych klientów, zgód właściciela i historii zmian dla wszystkich systemów (`maile/`, przyszłe `social/`, `przetargi/`, `reklamy/`, `finanse/`, `leady/`, `raporty/`).

## Czym COSTSEC NIE jest

- Nie jest kolejnym systemem z roadmapy AUTOFIRMA (jak `maile/`).
- Nie ma backendu, Lambd, handlerów, testów, skryptów. Na ten moment to dokumentacja, zasady i rytuały.
- Nie zastępuje `.claude/rules/cloud_safety.md` ani `.claude/rules/credential-protection.md` — wskazuje na nie i egzekwuje ich stosowanie.

## Po co istnieje

Każdy nowy system AUTOFIRMA wnosi: koszty cloud, klucze API, dane osobowe klientów, automatyczne akcje. Bez warstwy pilnującej całości — chaos: rachunek $400 niezauważony, wyciek klucza, automatyzacja działa bez zgody Daniela.

COSTSEC odpowiada na 6 pytań przed dodaniem cokolwiek do produkcji:

1. **Koszt** — ile to będzie kosztować w skali miesiąca? Mam Budget Alert?
2. **Sekrety** — gdzie są klucze? Czy poza repo? Czy mają retention/rotation?
3. **Bezpieczeństwo** — czy spełnia security defaults z `cloud_safety.md` sekcja I?
4. **Dane klientów** — czy przetwarzam PII? RODO? Encryption at rest?
5. **Zgoda właściciela** — Daniel zatwierdził? Mam to zapisane?
6. **Historia** — czy zmiana jest w CHANGELOG/audits/? Jak zrobić rollback?

## Mapa plików

| Plik | Zawartość |
|------|-----------|
| `docs/CLOUD_SAFETY.md` | Pointer + streszczenie `.claude/rules/cloud_safety.md` |
| `docs/ZASADY.md` | 5 zasad startowych COSTSEC (R1–R5) |
| `docs/SYSTEMY.md` | Rejestr systemów AUTOFIRMA z atrybutami: koszt, klucze, zgody, status |
| `docs/RYTUALY.md` | Cykliczne audyty (daily/weekly/monthly) — co, kiedy, dowód |
| `docs/GITHUB.md` | Polityka repo, pre-commit safety check |
| `docs/CHANGELOG.md` | Historia zmian dokumentacji COSTSEC |
| `audits/` | Raporty audytowe (`YYYY-MM-DD_<obszar>_<system>.md`) |

## Powiązania z `.claude/rules/`

- `.claude/rules/cloud_safety.md` — reguła systemowa, źródło prawdy dla operacji cloud (sekcje A–J). COSTSEC wskazuje, kiedy ją czytać i egzekwować.
- `.claude/rules/credential-protection.md` — reguła R1, sekrety nigdy nie wchodzą do repo/chatu/logów. COSTSEC trzyma rejestr "co gdzie żyje" w `docs/SYSTEMY.md`.

Reguły nie są kopiowane do COSTSEC. Zostają tam, gdzie są.

## Status

- **Wersja:** v0.1 (2026-05-04) — inicjalizacja
- **Tryb:** dokumentacja, zasady, rytuały. Bez kodu, bez automatyzacji.
- **Kolejny krok:** pierwszy realny audyt po pierwszym pełnym tygodniu używania (rytuał weekly z `RYTUALY.md`).

## Jak dodać nowy system do AUTOFIRMA z udziałem COSTSEC

1. Utwórz folder `gamak/projekty/autofirma/<nazwa>/`
2. Wypełnij wpis w `costsec/docs/SYSTEMY.md` (status: PLANOWANIE)
3. Przed pierwszym deployem cloud → przeczytaj `.claude/rules/cloud_safety.md` (sekcje B + I)
4. Po pierwszym tygodniu produkcji → audyt zapisany w `costsec/audits/`
5. Aktualizuj `costsec/docs/CHANGELOG.md` przy każdej zmianie reguł

Build it, run it. Ale najpierw — czy stać Cię na to, czy bezpieczne, czy zgodzony.
