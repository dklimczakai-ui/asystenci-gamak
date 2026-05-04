# AUTOFIRMA

Autonomiczny szkielet firmy GAMAK — kontener na systemy, które same się rozkręcają.
Cel: każdy podsystem to osobny "pracownik 24/7" robiący nudną, powtarzalną robotę bez Daniela.

## Dlaczego kontener, a nie pojedynczy projekt

Automatyzacja firmy to nie jedna integracja, tylko portfel systemów (mail, social, finanse, reklamy, przetargi).
Każdy ma własną logikę, własne klucze API, własny harmonogram, własne metryki.
Trzymanie ich w jednym folderze = chaos. AUTOFIRMA jest namespace'm: jeden katalog na rodzinę systemów,
każdy podfolder to autonomiczny moduł z własnym README, kodem i deployem.

## Pierwszy system: MAILE (ten tydzień)

Inteligentna obsługa 4 skrzynek Gmail (gamak, biuro, daniel86, ai) — auto-segregacja, drafty odpowiedzi
w stylu Ghosta, ekstrakcja kontaktów do CRM, alerty na pilne wątki. Folder: `maile/`.

## Roadmapa kolejnych systemów (kandydaci, kolejność zależna od ROI)

- **social/** — auto-publikacja postów na FB/IG dla marek (Gamak, Pure Tech, Padel Raze, Venze)
- **przetargi/** — skanowanie biznes-polska.pl + oferty-biznesowe.pl, alerty na pasujące ogłoszenia JST
- **reklamy/** — codzienny raport z kampanii Meta/Google na Telegram + alerty budżetowe
- **finanse/** — auto-fakturowanie iFirma/Fakturownia, tracking kosztów subskrypcji, alerty cashflow
- **leady/** — pipeline formularz → CRM → mail powitalny → follow-up po 3 dniach
- **raporty/** — poniedziałkowy brief biznesowy o 6:00 na Telegram (sprzedaż, przetargi, kalendarz)

Każdy system dochodzi gdy poprzedni działa stabilnie ≥2 tygodnie. Build it, run it.
