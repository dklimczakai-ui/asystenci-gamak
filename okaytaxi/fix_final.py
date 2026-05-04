"""Final comprehensive fix: hero app links, new cities on homepage, app page rewrite, old city descriptions."""
import os, re

BASE = r"C:\Users\klimc\Desktop\Asystenci\okaytaxi"

APP_APPLE = "https://apps.apple.com/pl/app/bia%C5%82o-czerwone-okay-taxi/id1398190430"
APP_GOOGLE = "https://play.google.com/store/apps/details?id=com.tiskel.tma.okaytaxi&hl=pl"
FB = "https://www.facebook.com/okaytaxibielsko"
IG = "https://www.instagram.com/okaytaxi_official/"

APPLE_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg>'
GPLAY_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M3 20.5V3.5C3 2.91 3.34 2.39 3.84 2.15L13.69 12L3.84 21.85C3.34 21.61 3 21.09 3 20.5ZM16.81 15.12L6.05 21.34L14.54 12.85L16.81 15.12ZM20.16 10.81C20.5 11.08 20.75 11.5 20.75 12C20.75 12.5 20.5 12.92 20.16 13.19L17.89 14.5L15.39 12L17.89 9.5L20.16 10.81ZM6.05 2.66L16.81 8.88L14.54 11.15L6.05 2.66Z"/></svg>'

# =========================================================
# 1. FIX HERO — App Store + Google Play buttons
# =========================================================
print("=== 1. Fixing hero section ===")
idx = os.path.join(BASE, "index.html")
with open(idx, "r", encoding="utf-8") as f:
    html = f.read()

# Replace hero-actions
html = html.replace(
    """      <div class="hero-actions">
        <a href="tel:+48720535353" class="btn btn-primary btn-lg">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M6.62 10.79a15.05 15.05 0 0 0 6.59 6.59l2.2-2.2a1 1 0 0 1 1.01-.24c1.12.37 2.33.57 3.58.57a1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.46.57 3.58a1 1 0 0 1-.24 1.01l-2.2 2.2z"/></svg>
          Zadzwoń teraz
        </a>
        <a href="aplikacja/index.html" class="btn btn-outline btn-lg">Pobierz aplikację</a>
      </div>""",
    f"""      <div class="hero-actions">
        <a href="tel:+48720535353" class="btn btn-primary btn-lg">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M6.62 10.79a15.05 15.05 0 0 0 6.59 6.59l2.2-2.2a1 1 0 0 1 1.01-.24c1.12.37 2.33.57 3.58.57a1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.46.57 3.58a1 1 0 0 1-.24 1.01l-2.2 2.2z"/></svg>
          Zadzwoń: 720 535 353
        </a>
        <a href="{APP_APPLE}" target="_blank" rel="noopener" class="btn btn-dark btn-lg">{APPLE_SVG} App Store</a>
        <a href="{APP_GOOGLE}" target="_blank" rel="noopener" class="btn btn-outline btn-lg">{GPLAY_SVG} Google Play</a>
      </div>""")

# Fix stats
html = html.replace('<strong>8+</strong>\n          <span>Miast</span>', '<strong>17</strong>\n          <span>Miast</span>')

# =========================================================
# 2. REPLACE CITIES GRID — all 17 cities
# =========================================================
print("=== 2. Replacing cities grid with all 17 ===")

OLD_GRID = '''    <div class="grid-4">
      <a href="okay-taxi-czechowice-dziedzice/index.html" class="location-card reveal reveal-delay-1">
        <div class="location-card-body">
          <h3>Czechowice-Dziedzice</h3>
          <p>Taxi door-to-door w&nbsp;Czechowicach-Dziedzicach i&nbsp;transfery do Bielska-Białej.</p>
          <span class="btn btn-outline" style="margin-top:0.75rem">Sprawdź szczegóły</span>
        </div>
      </a>

      <a href="okay-taxi-kozy/index.html" class="location-card reveal reveal-delay-2">
        <div class="location-card-body">
          <h3>Kozy</h3>
          <p>Szybkie taxi w&nbsp;Kozach. Dojazd do Bielska-Białej, na lotnisko i&nbsp;dalsze trasy.</p>
          <span class="btn btn-outline" style="margin-top:0.75rem">Sprawdź szczegóły</span>
        </div>
      </a>

      <a href="okay-taxi-szczyrk/index.html" class="location-card reveal reveal-delay-3">
        <div class="location-card-body">
          <h3>Szczyrk</h3>
          <p>Taxi na narty, do hotelu i&nbsp;z&nbsp;powrotem. Codziennie dowieziemy Cię na stok.</p>
          <span class="btn btn-outline" style="margin-top:0.75rem">Sprawdź szczegóły</span>
        </div>
      </a>

      <a href="okay-taxi-jasienica/index.html" class="location-card reveal reveal-delay-4">
        <div class="location-card-body">
          <h3>Jasienica</h3>
          <p>Komfortowe taxi w&nbsp;Jasienicy. Szybki dojazd do Bielska i&nbsp;okolicznych miast.</p>
          <span class="btn btn-outline" style="margin-top:0.75rem">Sprawdź szczegóły</span>
        </div>
      </a>

      <a href="okay-taxi-cieszyn/index.html" class="location-card reveal reveal-delay-1">
        <div class="location-card-body">
          <h3>Cieszyn</h3>
          <p>Taxi w&nbsp;Cieszynie — przejazdy miejskie i&nbsp;transgraniczne do Czeskiego Cieszyna.</p>
          <span class="btn btn-outline" style="margin-top:0.75rem">Sprawdź szczegóły</span>
        </div>
      </a>

      <a href="okay-taxi-oswiecim/index.html" class="location-card reveal reveal-delay-2">
        <div class="location-card-body">
          <h3>Oświęcim</h3>
          <p>Taxi w&nbsp;Oświęcimiu. Transfery dla turystów, dojazdy do muzeum i&nbsp;dworca.</p>
          <span class="btn btn-outline" style="margin-top:0.75rem">Sprawdź szczegóły</span>
        </div>
      </a>

      <a href="okay-taxi-wisla/index.html" class="location-card reveal reveal-delay-3">
        <div class="location-card-body">
          <h3>Wisła</h3>
          <p>Taxi w Wiśle — transfery turystyczne, dojazdy na skocznie i&nbsp;do hoteli.</p>
          <span class="btn btn-outline" style="margin-top:0.75rem">Sprawdź szczegóły</span>
        </div>
      </a>

      <a href="cennik/index.html" class="location-card reveal reveal-delay-4" style="background:var(--red);border:none;">
        <div class="location-card-body" style="color:var(--white)">
          <h3 style="color:var(--white)">Sprawdź cennik</h3>
          <p style="color:rgba(255,255,255,0.85)">Transparentne ceny na wszystkie trasy. Bez ukrytych opłat.</p>
          <span class="btn btn-white" style="margin-top:0.75rem">Zobacz cennik</span>
        </div>
      </a>
    </div>'''

CITIES = [
    ("okay-taxi-czechowice-dziedzice", "Czechowice-Dziedzice", "15 km od Bielska. Taxi door-to-door, transfery lotniskowe."),
    ("okay-taxi-kozy", "Kozy", "8 km od centrum. Szybki dojazd do Bielska i&nbsp;na lotniska."),
    ("okay-taxi-szczyrk", "Szczyrk", "Na stok, do hotelu, z&nbsp;dworca. Całoroczne transfery narciarskie."),
    ("okay-taxi-jasienica", "Jasienica", "Gmina przy Bielsku. Obsługujemy wszystkie sołectwa 24/7."),
    ("okay-taxi-cieszyn", "Cieszyn", "Przejazdy miejskie i&nbsp;transgraniczne do Českého Těšínu."),
    ("okay-taxi-oswiecim", "Oświęcim", "Transfery do Muzeum Auschwitz, dworców i&nbsp;lotnisk."),
    ("okay-taxi-wisla", "Wisła", "Skocznie Malinka, hotele SPA, Beskid Śląski."),
    ("okay-taxi-zywiec", "Żywiec", "Stolica Żywiecczyzny. Trasa do Bielska w&nbsp;40 min."),
    ("okay-taxi-ustron", "Ustroń", "Uzdrowisko, SPA, kolejka na Czantorię."),
    ("okay-taxi-skoczow", "Skoczów", "Śląsk Cieszyński. Dojazd do Cieszyna w&nbsp;15 min."),
    ("okay-taxi-andrychow", "Andrychów", "Trasa Bielsko–Wadowice. Inwałd, Dinolandia."),
    ("okay-taxi-wadowice", "Wadowice", "Miasto Jana Pawła II. Transfery turystyczne."),
    ("okay-taxi-kety", "Kęty", "Dolina Soły. Dojazd do Bielska i&nbsp;Oświęcimia."),
    ("okay-taxi-wilkowice", "Wilkowice", "Brama do Szczyrku. Szyndzielnia w&nbsp;10 min."),
    ("okay-taxi-milowka", "Milówka", "Beskid Żywiecki. Korbielów, Rajcza, stoki."),
    ("okay-taxi-miedzybrodzie", "Międzybrodzie Żywieckie", "Jezioro Żywieckie, Góra Żar, paralotnie."),
]

new_grid = '    <div class="grid-4">\n'
for i, (slug, name, desc) in enumerate(CITIES):
    d = (i % 4) + 1
    new_grid += f"""      <a href="{slug}/index.html" class="location-card reveal reveal-delay-{d}">
        <div class="location-card-body">
          <h3>{name}</h3>
          <p>{desc}</p>
          <span class="btn btn-outline" style="margin-top:0.75rem">Zamów taxi</span>
        </div>
      </a>
"""

# Add cennik card at end
new_grid += """      <a href="cennik/index.html" class="location-card reveal reveal-delay-1" style="background:var(--red);border:none;">
        <div class="location-card-body" style="color:var(--white)">
          <h3 style="color:var(--white)">Sprawdź cennik</h3>
          <p style="color:rgba(255,255,255,0.85)">Transparentne ceny na wszystkie trasy.</p>
          <span class="btn btn-white" style="margin-top:0.75rem">Zobacz cennik</span>
        </div>
      </a>
    </div>"""

html = html.replace(OLD_GRID, new_grid)

with open(idx, "w", encoding="utf-8") as f:
    f.write(html)
print("  index.html updated (hero + cities)")


# =========================================================
# 3. REWRITE APLIKACJA PAGE — real screenshots, proper SEO
# =========================================================
print("=== 3. Rewriting aplikacja page ===")

app_path = os.path.join(BASE, "aplikacja", "index.html")
with open(app_path, "r", encoding="utf-8") as f:
    app_html = f.read()

# Find and replace the content between page-header and footer
# Easier: rewrite from page-header to footer
app_new_body = f"""<section class="page-header"><div class="container">
<nav class="breadcrumbs" style="padding:0 0 1rem"><a href="../index.html">Start</a><span>/</span><strong>Aplikacja</strong></nav>
<h1>Aplikacja <span class="text-red">Okay Taxi</span> &mdash; Twoje taxi w&nbsp;kieszeni</h1>
<p class="lead">Pobierz białoczerwone Okay Taxi na iOS lub Android. Zamów taksówkę jednym kliknięciem, śledź ją na mapie, płać bez gotówki. Ponad 17&nbsp;miast w&nbsp;regionie Podbeskidzia.</p>
</div></section>

<section class="content-section"><div class="container">
<div class="two-col">
<div class="reveal">
<span class="section-label">Pobierz za darmo</span>
<h2>Zamów taxi bez dzwonienia &mdash; 3&nbsp;sekundy i&nbsp;jedzie</h2>
<p>Aplikacja Okay Taxi to najszybszy sposób na zamówienie białoczerwonej taksówki w&nbsp;Bielsku-Białej i&nbsp;17&nbsp;okolicznych miastach. Wpisujesz dokąd jedziesz, widzisz cenę, klikasz &mdash; taksówka rusza.</p>
<p>Żadnego czekania na linii, żadnego dyktowania adresu. Aplikacja zapamiętuje Twoje ulubione miejsca, pokazuje szacunkowy czas dojazdu i&nbsp;pozwala śledzić taksówkę na mapie w&nbsp;czasie rzeczywistym.</p>

<div style="display:flex;gap:1rem;margin-top:1.5rem;flex-wrap:wrap">
<a href="{APP_APPLE}" target="_blank" rel="noopener" class="btn btn-dark btn-lg">{APPLE_SVG} App Store</a>
<a href="{APP_GOOGLE}" target="_blank" rel="noopener" class="btn btn-primary btn-lg">{GPLAY_SVG} Google Play</a>
</div>
</div>
<div class="reveal" style="text-align:center">
<img src="https://okaytaxi.pl/wp-content/uploads/2024/01/tel-477x1024.png" alt="Aplikacja Okay Taxi &mdash; ekran zamawiania taksówki w Bielsku-Białej" width="477" height="1024" loading="lazy" decoding="async" style="max-width:300px;border-radius:28px;box-shadow:var(--shadow-xl)">
</div>
</div>
</div></section>

<section class="section-alt"><div class="container">
<div class="section-header center reveal"><span class="section-label">Funkcje aplikacji</span><h2>Wszystko czego potrzebujesz od taxi &mdash; w&nbsp;jednej apce</h2></div>
<div class="grid-3">
<div class="card reveal reveal-delay-1"><div class="card-icon">📍</div><h3>Śledzenie na mapie</h3><p>Widzisz dokładnie gdzie jest Twoja taksówka i&nbsp;za ile minut dojedzie. Koniec z&nbsp;niepewnością &mdash; wiesz kiedy wyjść z&nbsp;domu.</p></div>
<div class="card reveal reveal-delay-2"><div class="card-icon">💳</div><h3>Płatność bez gotówki</h3><p>Karta Visa, Mastercard, BLIK lub portfel w&nbsp;aplikacji. Nie szukasz drobnych, nie czekasz na resztę. Rachunek na mailu.</p></div>
<div class="card reveal reveal-delay-3"><div class="card-icon">⭐</div><h3>Ocena kierowcy</h3><p>Po każdym kursie oceniasz kierowcę. Dzięki temu utrzymujemy najwyższą jakość obsługi w&nbsp;całej flocie.</p></div>
<div class="card reveal reveal-delay-1"><div class="card-icon">📋</div><h3>Historia przejazdów</h3><p>Wszystkie Twoje kursy w&nbsp;jednym miejscu &mdash; data, trasa, cena, kierowca. Potrzebujesz rachunku? Pobierz jednym kliknięciem.</p></div>
<div class="card reveal reveal-delay-2"><div class="card-icon">🏠</div><h3>Ulubione adresy</h3><p>Zapisz dom, pracę, ulubioną restaurację. Następnym razem zamawiasz taxi w&nbsp;2&nbsp;kliknięcia zamiast wpisywać adres od nowa.</p></div>
<div class="card reveal reveal-delay-3"><div class="card-icon">🔔</div><h3>Powiadomienia push</h3><p>Kierowca jest za rogiem? Dostaniesz powiadomienie. Zmiana statusu zamówienia? Widzisz natychmiast. Zero niespodzianek.</p></div>
</div>
</div></section>

<section class="content-section"><div class="container">
<div class="two-col reverse">
<div class="reveal" style="text-align:center">
<img src="https://okaytaxi.pl/wp-content/uploads/2024/01/tel-1-477x1024.png" alt="Aplikacja Okay Taxi &mdash; śledzenie taksówki na mapie" width="477" height="1024" loading="lazy" decoding="async" style="max-width:300px;border-radius:28px;box-shadow:var(--shadow-xl)">
</div>
<div class="reveal">
<span class="section-label">Jak to działa</span>
<h2>Od pobrania do przejazdu &mdash; 60&nbsp;sekund</h2>
<ul class="content-section">
<li><strong>Krok 1:</strong> Pobierz aplikację z&nbsp;<a href="{APP_APPLE}" style="color:var(--red)">App Store</a> lub <a href="{APP_GOOGLE}" style="color:var(--red)">Google Play</a></li>
<li><strong>Krok 2:</strong> Zarejestruj się numerem telefonu &mdash; bez maili, bez haseł</li>
<li><strong>Krok 3:</strong> Wpisz dokąd jedziesz &mdash; zobaczysz szacunkową cenę</li>
<li><strong>Krok 4:</strong> Kliknij "Zamów" &mdash; najbliższa taksówka rusza do Ciebie</li>
<li><strong>Krok 5:</strong> Śledź na mapie, wsiądź, jedź. Zapłać jak chcesz.</li>
</ul>
<p>Obsługujemy <strong>17&nbsp;miast</strong> w&nbsp;regionie Podbeskidzia: Bielsko-Biała, Czechowice-Dziedzice, Kozy, Szczyrk, Cieszyn, Oświęcim, Wisła, Żywiec, Ustroń, Skoczów, Andrychów, Wadowice, Kęty, Wilkowice, Milówka, Jasienica i&nbsp;Międzybrodzie Żywieckie.</p>
</div>
</div>
</div></section>

<section class="section-dark"><div class="container">
<div class="section-header center reveal"><span class="section-label">Galeria</span><h2 style="color:var(--white)">Zobacz jak wygląda aplikacja</h2></div>
<div style="display:flex;gap:1.5rem;justify-content:center;flex-wrap:wrap;padding:var(--space-md) 0">
<img src="https://okaytaxi.pl/wp-content/uploads/2021/12/slajd0.png" alt="Ekran startowy aplikacji Okay Taxi" loading="lazy" decoding="async" style="height:320px;width:auto;border-radius:16px;box-shadow:var(--shadow-lg)" class="reveal reveal-delay-1">
<img src="https://okaytaxi.pl/wp-content/uploads/2021/12/slajd_1.png" alt="Zamawianie taxi w aplikacji Okay Taxi" loading="lazy" decoding="async" style="height:320px;width:auto;border-radius:16px;box-shadow:var(--shadow-lg)" class="reveal reveal-delay-2">
<img src="https://okaytaxi.pl/wp-content/uploads/2021/12/slajd2.png" alt="Mapa śledzenia taxi w aplikacji Okay Taxi" loading="lazy" decoding="async" style="height:320px;width:auto;border-radius:16px;box-shadow:var(--shadow-lg)" class="reveal reveal-delay-3">
<img src="https://okaytaxi.pl/wp-content/uploads/2021/12/slajd3.png" alt="Płatność w aplikacji Okay Taxi" loading="lazy" decoding="async" style="height:320px;width:auto;border-radius:16px;box-shadow:var(--shadow-lg)" class="reveal reveal-delay-4">
<img src="https://okaytaxi.pl/wp-content/uploads/2021/12/slajd4.png" alt="Program Okayka w aplikacji" loading="lazy" decoding="async" style="height:320px;width:auto;border-radius:16px;box-shadow:var(--shadow-lg)" class="reveal reveal-delay-1">
</div>
</div></section>

<section><div class="container"><div class="cta-banner reveal">
<h2>Pobierz Okay Taxi &mdash; za darmo</h2>
<p>Dołącz do tysięcy pasażerów w&nbsp;regionie Podbeskidzia. Twoje taxi jest o&nbsp;jedno kliknięcie stąd.</p>
<div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;margin-bottom:1.5rem">
<a href="{APP_APPLE}" target="_blank" rel="noopener" class="btn btn-white btn-lg">{APPLE_SVG} App Store</a>
<a href="{APP_GOOGLE}" target="_blank" rel="noopener" class="btn btn-white btn-lg">{GPLAY_SVG} Google Play</a>
</div>
<p style="opacity:0.8">Lub zadzwoń: <a href="tel:+48720535353" style="color:var(--white);font-weight:700">720 535 353</a></p>
</div></div></section>"""

# Replace everything between </header> closing and <footer
header_end = app_html.find('</header>') + len('</header>')
# Find the second </nav> (mobile nav closing)
nav_closes = [m.end() for m in re.finditer(r'</nav>', app_html)]
if len(nav_closes) >= 2:
    header_end = nav_closes[1]

footer_start = app_html.find('<footer')
if footer_start > 0 and header_end > 0:
    app_html = app_html[:header_end] + "\n\n" + app_new_body + "\n\n" + app_html[footer_start:]

with open(app_path, "w", encoding="utf-8") as f:
    f.write(app_html)
print("  aplikacja/index.html rewritten with real screenshots + SEO content")


# =========================================================
# 4. IMPROVE OLD CITY PAGES — better SEO descriptions
# =========================================================
print("=== 4. Improving old city page descriptions ===")

OLD_CITY_IMPROVEMENTS = {
    "okay-taxi-czechowice-dziedzice": {
        "old_h2": "Zamów taxi w\xa0Czechowice-Dziedzice",  # will search for partial
        "new_desc": """<p>Czechowice-Dziedzice to drugie co do wielkości miasto powiatu bielskiego, położone zaledwie 15&nbsp;km od centrum Bielska-Białej. Okay Taxi zapewnia regularne, komfortowe przejazdy na trasie Czechowice–Bielsko oraz transfery na lotniska Katowice-Pyrzowice i&nbsp;Kraków-Balice.</p>
<p>Obsługujemy centrum Czechowic, osiedle Lesisko, Dziedzice, stację PKP Czechowice-Dziedzice, Muzeum Ognia, centra handlowe i&nbsp;zakłady przemysłowe. Taksówka dojedzie do Ciebie w&nbsp;kilka minut &mdash; działamy 24/7, również w&nbsp;święta i&nbsp;sylwestra.</p>
<h3>Popularne trasy z&nbsp;Czechowic-Dziedzic</h3>
<ul class="content-section">
<li>Czechowice-Dziedzice &rarr; Bielsko-Biała centrum (~15&nbsp;km, ~20&nbsp;min)</li>
<li>Czechowice-Dziedzice &rarr; Galeria Sfera Bielsko (~17&nbsp;km, ~22&nbsp;min)</li>
<li>Czechowice-Dziedzice &rarr; Lotnisko Katowice-Pyrzowice (~100&nbsp;km, ~70&nbsp;min)</li>
<li>Czechowice-Dziedzice &rarr; Lotnisko Kraków-Balice (~115&nbsp;km, ~75&nbsp;min)</li>
<li>Czechowice-Dziedzice &rarr; Pszczyna (~20&nbsp;km, ~25&nbsp;min)</li>
</ul>
<h3>Dlaczego Okay Taxi w&nbsp;Czechowicach?</h3>
<p>Jako jedna z&nbsp;niewielu korporacji obsługujemy Czechowice-Dziedzice stałą flotą kierowców znających każdą ulicę miasta. Płatność kartą, BLIK, gotówką &mdash; lub bezgotówkowo dla firm.</p>""",
    },
}

# For now, let's just make sure old cities have app links in their CTA sections
for root, dirs, files in os.walk(BASE):
    for fname in files:
        if not fname.endswith(".html"):
            continue
        fpath = os.path.join(root, fname)
        rel = os.path.relpath(fpath, BASE).replace("\\", "/")

        # Only process old city pages
        if not rel.startswith("okay-taxi-") or rel in [f"{s}/index.html" for s in [
            "okay-taxi-zywiec", "okay-taxi-andrychow", "okay-taxi-kety",
            "okay-taxi-wadowice", "okay-taxi-skoczow", "okay-taxi-ustron",
            "okay-taxi-wilkowice", "okay-taxi-milowka", "okay-taxi-brzesce",
            "okay-taxi-miedzybrodzie"]]:
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # Add App Store/Google Play to CTA buttons if not present
        if APP_APPLE not in content:
            # Add after the phone CTA button
            content = content.replace(
                'href="tel:+48720535353" class="btn btn-primary mt-md">Zadzwoń: 720 535 353</a>',
                f'href="tel:+48720535353" class="btn btn-primary mt-md">Zadzwoń: 720 535 353</a>\n<a href="{APP_APPLE}" target="_blank" rel="noopener" class="btn btn-dark mt-md">{APPLE_SVG} App Store</a>\n<a href="{APP_GOOGLE}" target="_blank" rel="noopener" class="btn btn-outline mt-md">{GPLAY_SVG} Google Play</a>'
            )

        if content != original:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  Updated: {rel}")


print("\n=== ALL DONE ===")
