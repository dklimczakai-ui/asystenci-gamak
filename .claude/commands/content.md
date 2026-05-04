# Content Machine - Generowanie treści

Argumenty: $ARGUMENTS

## KONTEKST
Przeczytaj pliki projektu (beauty lub gamak - zależnie od kontekstu):
- `dane/profil.md` - kim jest user
- `dane/persona.md` - do kogo pisze
- `dane/oferta.md` - co sprzedaje
- `dane/ghost.md` (jeśli istnieje) - styl pisania

## ZASADY CONTENTU (BEZWZGLĘDNE)
1. **JĘZYK:** Cały tekst PO POLSKU z poprawnymi znakami (ą,ć,ę,ł,ń,ó,ś,ź,ż)
2. **TON:** Marketing-friendly, zero żargonu technicznego, proste zdania
3. **GRAFIKI:**
   - Facebook: 1200x630px
   - Instagram feed: 1080x1080px
   - Instagram Stories/Reels: 1080x1920px
   - LinkedIn: 1200x627px
4. **IMAGE PROMPTY:** Tekst na grafikach ZAWSZE po polsku
5. **STYL:** Zgodny z ghost.md (jeśli istnieje)

## WORKFLOW
1. Zapytaj usera o temat/platformę (lub weź z $ARGUMENTS)
2. Wygeneruj post gotowy do publikacji
3. Dołącz image prompt z poprawnym aspect ratio
4. Dołącz 3-5 hashtagów (po polsku jeśli to ma sens)

## WALIDACJA PRZED DOSTARCZENIEM
Przed pokazaniem usera sprawdź:
- [ ] Cały tekst po polsku?
- [ ] Polskie znaki poprawne?
- [ ] Image prompt ma poprawny aspect ratio?
- [ ] Ton marketingowy, nie techniczny?
- [ ] Zgodny z profilem stylu?
- [ ] CTA na końcu?

## FORMAT ODPOWIEDZI
```
📱 [PLATFORMA] | [TEMAT]

[Treść posta]

---
🎨 IMAGE PROMPT: [prompt po polsku, aspect ratio]
#️⃣ HASHTAGI: [lista]
📅 SUGEROWANY CZAS: [dzień, godzina]
```
