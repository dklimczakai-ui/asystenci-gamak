# 📚 INSTRUKCJA PO WARSZTACIE W5
## Konfiguracja pełnego COO w Twoim projekcie

---

## 🎯 CO ZYSKUJESZ

Po W5 masz:
- **COO.md** - Twój brutalnie szczery partner egzekucji (charakter Logan Roy)
- **decyzje.md** - Baza decyzji (automatyczne wykrywanie i zapis)
- **15 zadań** - Konkretne rzeczy do robienia z COO
- **Checklisty** - Prowadzenie przez budowę biznesu krok po kroku

---

## 📂 STRUKTURA PLIKÓW

```
Twój-Projekt/
├── CLAUDE.md           ← zaktualizuj (patrz niżej)
├── COO.md              ← NOWY z W5
├── decyzje.md  ← NOWY z W5 (template)
├── profil.md           ← Twój profil (z W1-W4)
├── persona.md          ← Twój klient (z W1-W4)
├── oferta.md           ← Twoja oferta (z W1-W4)
├── plan.md             ← Twój plan (z W1-W4)
└── CHECKLISTY/         ← opcjonalnie, dla zaawansowanych
    ├── CHECKLISTA_PRODUKT_CYFROWY.md
    ├── CHECKLISTA_USLUGA_B2B.md
    └── [inne checklisty]
```

---

## 🔧 KROK 1: Skopiuj pliki

### A) COO.md
Skopiuj plik `COO.md` z materiałów W5 do swojego projektu.

### B) decyzje.md
Skopiuj template `decyzje.md` i zmień nazwę na `decyzje.md`.

### C) Checklisty (opcjonalnie)
Jeśli chcesz używać funkcji checklist, skopiuj odpowiednie pliki do folderu `CHECKLISTY/`.

---

## 🔧 KROK 2: Zaktualizuj CLAUDE.md

Dodaj do sekcji "Pliki projektu" lub "Kontekst":

```markdown
## 🤖 ASYSTENCI

### @coo - Chief Operating Officer
Plik: COO.md
Kiedy: planowanie, budowa z checklistą, przegląd sesji
Charakter: Logan Roy (twardy ale wspierający)

Komendy:
- @coo → uruchamia COO
- "plan tygodnia" / "plan dnia" → planowanie
- "użyj checklisty [TYP]" → budowa z checklistą
- "zapisz decyzję" → formatuje wpis do bazy
- "podsumuj" → przegląd sesji

### Baza decyzji
Plik: decyzje.md
- COO automatycznie wykrywa decyzje w rozmowie
- Na końcu sesji proponuje zapis ważnych ustaleń
- Przeglądaj co tydzień i archiwizuj nieaktualne
```

---

## 🔧 KROK 3: Test

### Sprawdź czy działa:

1. **Uruchom COO:**
   ```
   @coo
   ```
   Powinno pokazać menu (3 opcje)

2. **Przetestuj planowanie:**
   ```
   Plan dnia. Energia: 7.
   ```

3. **Przetestuj checklistę:**
   ```
   Użyj checklisty B2B. Jestem na etapie walidacji pomysłu.
   ```

4. **Przetestuj wykrywanie decyzji:**
   ```
   Postanowiłem że cena kursu to 997 PLN.
   ```
   COO powinien zaproponować zapis

---

## 💡 NOWE KOMENDY

| Komenda | Co robi |
|---------|---------|
| `@coo` | Uruchamia COO, pokazuje menu |
| `plan tygodnia` | Planowanie tygodnia z kontekstem celów |
| `plan dnia` | Planowanie dnia (pyta o energię) |
| `użyj checklisty [TYP]` | Ładuje checklistę, prowadzi przez fazę |
| `zapisz decyzję` | Formatuje decyzję do bazy |
| `pokaż decyzje` | Wyświetla aktywne decyzje |
| `podsumuj` | Podsumowanie sesji + propozycja zapisów |
| `ogarnij plan` | Porządkuje plan.md |
| `co mnie blokuje` | Diagnoza + opcje odblokowania |
| `health check` | Sprawdza stan plików |
| `daj opcje` | Generuje 3-5 opcji rozwiązania z ocenami |
| `energia [1-10]` | Ustawia tryb (brutal/standard/stop) |

---

## 📋 TYPY CHECKLIST

| Typ | Komenda | Dla kogo |
|-----|---------|----------|
| Produkt cyfrowy | `użyj checklisty CYFROWY` | Kursy, ebooki, membership |
| Usługa B2B | `użyj checklisty B2B` | Konsulting, agencja, freelance |
| SaaS | `użyj checklisty SAAS` | Software as a Service |
| Usługi B2C | `użyj checklisty B2C` | Usługi dla konsumentów |
| E-commerce | `użyj checklisty ECOMMERCE` | Sklepy online |
| Warsztaty | `użyj checklisty WARSZTATY` | Eventy, szkolenia |

---

## 🔄 PRZEPŁYW PRACY Z COO

### Typowy tydzień:

**Poniedziałek (20 min):**
```
@coo
Plan tygodnia. [dołącz profil.md i plan.md]
```

**Codziennie (10 min):**
```
Plan dnia. Energia: [1-10].
```

**W trakcie pracy:**
```
Użyj checklisty [TYP]. Jestem na etapie [X].
```

**Koniec sesji (5-10 min):**
```
Podsumuj.
```

**Piątek (15 min):**
```
Review tygodnia. Jak mi poszło?
```

---

## ⚠️ WAŻNE

### COO NIE ładuje checklist automatycznie!
Musisz powiedzieć "użyj checklisty [TYP]" żeby COO zaczął z nią pracować.

### Baza decyzji wymaga przeglądu
Co tydzień przejrzyj `decyzje.md` i przenieś nieaktualne do ARCHIWUM.

### Pliki profil/persona/oferta/plan są wymagane
COO czyta te pliki żeby dać Ci spersonalizowane rady. Bez nich = ogólniki.

---

## 🚀 SZYBKI START

1. Skopiuj `COO.md` i `decyzje.md` do projektu
2. Zaktualizuj `CLAUDE.md` (dodaj sekcję @coo)
3. Uruchom: `@coo`
4. Wybierz: `1` (planowanie)
5. Pracuj!

---

## 📞 POMOC

Problemy? Pytania?
- Sprawdź czy pliki są w projekcie
- Sprawdź czy CLAUDE.md jest zaktualizowany
- Napisz na grupie AIBL

---

*Materiały z Warsztatu W5 - AI Biznes Lab*
