# A1 + A2 — walkthrough dla Daniela (R1 follow-up)

**Data:** 2026-05-05
**Cel:** dwie pozycje pending wymagające logowania w UI (CT nie ma dostępu): audyt logów FTP CyberFolks + audyt OAuth GitHub.
**Czas łączny:** ~10-15 min.
**Krytyczność:** A2 wpływa na decyzję RODO (jeśli OAuth znaleziony — podnosi ryzyko realne, zalecane zgłoszenie). Patrz `2026-05-05_RODO_decision.md`.

---

## A1 — Audyt logów FTP CyberFolks (5 min)

### Co sprawdzasz
Czy w okresie ekspozycji **2026-05-04 (rano push) → 2026-05-05 04:30 (rotacja hasła)** ktoś inny niż Ty próbował zalogować się przez FTP na user `xkhvbgqqku` używając hasła `<REDACTED_FTP_PWD_INCIDENT_2026-05-05>` które wyciekło.

### Krok po kroku

1. **Zaloguj się do panelu CyberFolks**
   - URL: https://panel.cyber-folks.pl/
   - Login: Twój standardowy email konta CF
   - Hasło: aktualne hasło panelu (NIE FTP — panel jest osobny)

2. **Znajdź sekcję logów / aktywności konta**
   - W menu szukaj: `Logi`, `Statystyki`, `Aktywność`, `Historia logowań` lub `Bezpieczeństwo`
   - Zwykle pod ikoną tarczy / oka / wykresu
   - **Jeśli nie znajdujesz** → kliknij `Pomoc / Kontakt` i napisz support: "Proszę o eksport logów FTP user `xkhvbgqqku` z okresu 2026-05-04 00:00 → 2026-05-05 06:00 UTC w celu audytu bezpieczeństwa"

3. **Przefiltruj logi**
   - Filtr: usługa = **FTP** (nie HTTP, nie email)
   - Zakres dat: **2026-05-04 00:00 → 2026-05-05 06:00** (UTC lub czas polski — sprawdź panel)
   - User: `xkhvbgqqku`

4. **Co szukasz w logach (pattern match)**
   ```
   ┌──────────────────────────────────────────────┬────────────┐
   │ Wpis logu                                    │ Werdykt    │
   ├──────────────────────────────────────────────┼────────────┤
   │ Login successful — IP Twoje (213.x / 89.x PL)│ ✅ OK Daniel│
   │ Login successful — IP zagraniczne / VPN      │ 🔴 ALARM   │
   │ Login failed — IP Twoje, brute force         │ ⚠️ WARN    │
   │ Login failed — IP zewnętrzne, > 3 próby      │ 🔴 ALARM   │
   │ Login successful — IP nieznane, 1 próba      │ 🔴 ALARM   │
   │ Brak żadnych zapisów                          │ ✅ OK      │
   └──────────────────────────────────────────────┴────────────┘
   ```

5. **Twoje IP** — sprawdź teraz: https://www.whatismyip.com/
   - Zwykle Twoje IP zaczyna się na `89.` lub `213.` (Polska, Orange/Play/T-Mobile/UPC)
   - Zapisz IP do porównania

6. **Wynik audytu — wpisz do `costsec/audits/2026-05-05_A1_audyt_ftp_cf.md`**

   **Szablon:**
   ```markdown
   # A1 — Audyt logów FTP CyberFolks (R1 incident follow-up)

   **Data audytu:** 2026-05-05
   **Wykonał:** Daniel
   **Okres sprawdzony:** 2026-05-04 00:00 → 2026-05-05 06:00 (UTC)
   **User:** xkhvbgqqku
   **Usługa:** FTP

   ## Wyniki

   - Liczba prób logowania: <X>
   - Liczba udanych: <Y>
   - Liczba nieudanych: <Z>
   - IP udane logowania: <lista, z geolokalizacją>
   - IP nieudane logowania: <lista>

   ## Werdykt

   - [ ] CZYSTE — wszystkie udane logowania = IP Daniela
   - [ ] PODEJRZANE — co najmniej 1 udane logowanie z IP zewnętrznego/nieznanego
   - [ ] BRAK LOGÓW — panel CF nie udostępnia, zgłoszenie do supportu w toku

   ## Konsekwencje
   - CZYSTE → R1 incident pełen close, RODO Art. 33 = NIE zgłaszamy (wzmocnienie rekomendacji)
   - PODEJRZANE → eskalacja: zmiana hasła ponownie, audyt całego konta CF, RODO Art. 33 = ZGŁASZAMY
   - BRAK LOGÓW → support follow-up, bezpieczna domniemanie "czyste" jeśli nie ma sygnału przeciwnego
   ```

7. **Wpis do `decyzje.md`** (root):
   ```
   ### 2026-05-05 — A1 audyt FTP CF — wynik: <CZYSTE / PODEJRZANE>
   Patrz `costsec/audits/2026-05-05_A1_audyt_ftp_cf.md`.
   ```

---

## A2 — Audyt OAuth tokens GitHub (3 min)

### Co sprawdzasz
Czy ktoś / jakaś aplikacja ma OAuth token z scope `repo` (czytanie + pisanie wszystkich Twoich repo, w tym PRIVATE `dklimczakai-ui/asystenci-gamak`) — i czy nie pojawił się nowy w okresie ekspozycji.

### Krok po kroku

1. **Zaloguj się na GitHub**
   - URL: https://github.com/login
   - Login: `dklimczakai-ui` (konto utworzone 2026-05-04)
   - MFA: Authenticator app (jak zwykle)

2. **Otwórz Authorized OAuth Apps**
   - URL bezpośredni: https://github.com/settings/applications
   - Lub: prawy górny avatar → Settings → Applications → **Authorized OAuth Apps**

3. **Sprawdź każdą aplikację z listy**

   Dla KAŻDEJ aplikacji w sekcji "Authorized OAuth Apps":
   - Kliknij nazwę aplikacji
   - Sprawdź **scope/permissions** — szukaj słów: `repo`, `read:repo`, `write:repo`, `admin:repo_hook`
   - Sprawdź **last used** — kiedy ostatnio aplikacja była użyta
   - Sprawdź **created** — kiedy autoryzowana

4. **Klasyfikacja**

   ```
   ┌──────────────────────────────────────────────┬────────────┐
   │ Aplikacja                                    │ Werdykt    │
   ├──────────────────────────────────────────────┼────────────┤
   │ GitHub CLI (`gh`)                             │ ✅ OK      │
   │ Visual Studio Code / GitHub Codespaces        │ ✅ OK      │
   │ Vercel / Netlify (jeśli używasz)              │ ✅ OK      │
   │ Aplikacja nieznana, autoryzowana wczoraj/dziś│ 🔴 REVOKE  │
   │ Aplikacja nieznana, scope `repo`             │ 🔴 REVOKE  │
   │ Aplikacja użyta po 2026-05-04 a Ty nie       │ 🔴 ALARM   │
   │   pamiętasz autoryzacji                      │            │
   └──────────────────────────────────────────────┴────────────┘
   ```

5. **Sprawdź też 2 dodatkowe sekcje:**
   - **Personal Access Tokens** (https://github.com/settings/tokens)
     - Czy są tokeny których nie tworzyłeś?
     - Tokeny z scope `repo` aktywne w okresie 2026-05-04 → 05-05?
   - **Fine-grained tokens** (https://github.com/settings/tokens?type=beta)
     - To samo — jakie istnieją, czy je rozpoznajesz?
   - **SSH keys** (https://github.com/settings/keys)
     - Jeden klucz `id_ed25519_github` od 2026-05-04 — tylko Twój. Inne = ALARM.

6. **Jeśli znajdziesz coś podejrzanego:**
   - Kliknij **Revoke** (Authorized Apps) lub **Delete** (PAT)
   - Skopiuj nazwę aplikacji + datę autoryzacji do raportu A2
   - **Po revoke wszystkich podejrzanych:** zmień hasło GitHub + włącz/sprawdź MFA (już masz)

7. **Wynik audytu — wpisz do `costsec/audits/2026-05-05_A2_audyt_oauth_gh.md`**

   **Szablon:**
   ```markdown
   # A2 — Audyt OAuth GitHub (R1 incident follow-up)

   **Data audytu:** 2026-05-05
   **Wykonał:** Daniel
   **Konto:** dklimczakai-ui

   ## Authorized OAuth Apps (sekcja: github.com/settings/applications)

   | App | Scope | Created | Last used | Werdykt |
   |---|---|---|---|---|
   | <nazwa1> | <scope> | <data> | <data> | OK / REVOKED |
   | <nazwa2> | <scope> | <data> | <data> | OK / REVOKED |

   ## Personal Access Tokens (github.com/settings/tokens)

   | Token name | Scope | Created | Last used | Werdykt |
   |---|---|---|---|---|
   | <nazwa> | <scope> | <data> | <data> | OK / DELETED |

   ## SSH Keys (github.com/settings/keys)

   | Key | Type | Added | Werdykt |
   |---|---|---|---|
   | id_ed25519_github | ed25519 | 2026-05-04 | OK Daniel |

   ## Werdykt globalny

   - [ ] CZYSTE — żadnej podejrzanej aplikacji/tokenu/klucza
   - [ ] PODEJRZANE — N pozycji revoked/deleted, lista wyżej
   ```

8. **Wpis do `decyzje.md`** (root):
   ```
   ### 2026-05-05 — A2 audyt OAuth GH — wynik: <CZYSTE / PODEJRZANE>
   Patrz `costsec/audits/2026-05-05_A2_audyt_oauth_gh.md`.
   ```

---

## Wpływ na RODO Art. 33

Po wykonaniu A1 + A2:

| A1 | A2 | RODO Art. 33 — rekomendacja CTO |
|---|---|---|
| CZYSTE | CZYSTE | **NIE zgłaszać** (wzmocnienie rekomendacji z `2026-05-05_RODO_decision.md`) |
| CZYSTE | PODEJRZANE | **ZGŁOSIĆ** — OAuth z scope `repo` w okresie ekspozycji = ryzyko realne |
| PODEJRZANE | CZYSTE | **ZGŁOSIĆ** — udane logowanie zewnętrzne FTP = potencjalne pobranie repo lub innych zasobów |
| PODEJRZANE | PODEJRZANE | **ZGŁOSIĆ + eskalacja** — pełen incident response, audit konta GitHub + AWS + CF |
| BRAK LOGÓW (A1) | CZYSTE | **NIE zgłaszać** (default + brak sygnału przeciwnego) |
| BRAK LOGÓW (A1) | PODEJRZANE | **ZGŁOSIĆ** (zaufaj sygnałowi z A2) |

Decyzję wpisz w `decyzje.md` zgodnie z szablonem z `2026-05-05_RODO_decision.md` § 8.

---

## Deadlines

```
┌─────────────────────────┬──────────────────┐
│ Akcja                   │ Deadline         │
├─────────────────────────┼──────────────────┤
│ A1 (FTP audyt)          │ 2026-05-07 22:00 │
│ A2 (OAuth audyt)        │ 2026-05-07 22:00 │
│ Decyzja RODO Art. 33    │ 2026-05-07 22:00 │
│ (zgłaszam / nie)        │                  │
└─────────────────────────┴──────────────────┘
```

Jeśli A1 lub A2 ujawni problem **PO** deadline — Art. 33 ust. 1 mówi "bez zbędnej zwłoki", więc zgłaszamy z opóźnieniem + wyjaśnieniem dlaczego (audit dodatkowy ujawnił po 72h).

---

**Plik utworzony:** 2026-05-05 (CTO yolo session)
**Następna akcja:** Daniel logowanie do paneli (~10-15 min).
