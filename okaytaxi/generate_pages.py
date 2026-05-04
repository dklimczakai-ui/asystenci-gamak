#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate all Okay Taxi subpages."""
import os

BASE = r"C:\Users\klimc\Desktop\Asystenci\okaytaxi"

PHONE_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M6.62 10.79a15.05 15.05 0 0 0 6.59 6.59l2.2-2.2a1 1 0 0 1 1.01-.24c1.12.37 2.33.57 3.58.57a1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.46.57 3.58a1 1 0 0 1-.24 1.01l-2.2 2.2z"/></svg>'

LOGO = "https://okaytaxi.pl/wp-content/uploads/2021/07/okay_duze.png"
BANNER = "https://okaytaxi.pl/wp-content/uploads/2024/01/Baner-Okay-Taxi-2024-3-1390x782.png"
TEL_IMG = "https://okaytaxi.pl/wp-content/uploads/2024/01/tel-600x1288.png"
DSC1 = "https://okaytaxi.pl/wp-content/uploads/2021/08/DSC_0204-1390x782.jpg"

NAV_ITEMS = [
    ("/", "Start"),
    ("/o-nas/", "O nas"),
    ("/flota/", "Flota"),
    ("/cennik/", "Cennik"),
    ("/aplikacja/", "Aplikacja"),
    ("/okayka/", "Okayka"),
    ("/dla-niepelnosprawnych/", "Dostępność"),
]


def make_head(title, desc, canonical, og_img=None, robots="index, follow, max-image-preview:large"):
    if og_img is None:
        og_img = BANNER
    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="https://okaytaxi.pl{canonical}">
<meta name="geo.region" content="PL-SL"><meta name="geo.placename" content="Bielsko-Biała">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://okaytaxi.pl{canonical}">
<meta property="og:image" content="{og_img}">
<meta property="og:locale" content="pl_PL">
<meta property="og:site_name" content="Okay Taxi">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#c72227">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/style.css">
<link rel="icon" type="image/png" href="{LOGO}">
"""


def breadcrumb_ld(items):
    els = ",".join(
        f'{{"@type":"ListItem","position":{i},"name":"{n}","item":"https://okaytaxi.pl{u}"}}'
        for i, (n, u) in enumerate(items, 1)
    )
    return f'<script type="application/ld+json">{{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{els}]}}</script>'


def nav_html(active=""):
    desk = "".join(
        f'<a href="{u}"{"  class=active" if u == active else ""}>{n}</a>'
        for u, n in NAV_ITEMS
    )
    mob = "".join(
        f'<a href="{u}"{"  class=active" if u == active else ""}>{n}</a>'
        for u, n in NAV_ITEMS
    )
    return f"""<header class="header"><div class="container header-inner">
<a href="/" class="logo"><img src="{LOGO}" alt="Okay Taxi" width="44" height="44"></a>
<nav class="nav-desktop">{desk}<a href="tel:+48720535353" class="nav-cta">{PHONE_SVG}720 535 353</a></nav>
<button class="nav-toggle" aria-label="Menu"><span></span><span></span><span></span></button>
</div><nav class="nav-mobile">{mob}<a href="tel:+48720535353" class="nav-cta">Zadzwoń: 720 535 353</a></nav></header>"""


FOOTER = f"""<footer class="footer"><div class="container">
<div class="footer-grid">
<div class="footer-brand"><img src="{LOGO}" alt="Okay Taxi" width="140" height="140" loading="lazy"><p>Korporacja białoczerwonych taksówek w&nbsp;Bielsku-Białej &mdash; 24/7.</p></div>
<div><h4>Usługi</h4><div class="footer-links"><a href="/cennik/">Cennik</a><a href="/flota/">Flota</a><a href="/aplikacja/">Aplikacja</a><a href="/okayka/">Okayka</a><a href="/dla-niepelnosprawnych/">Dostępność</a><a href="/programy-bezgotowkowe/">Dla firm</a></div></div>
<div><h4>Miasta</h4><div class="footer-links"><a href="/okay-taxi-czechowice-dziedzice/">Czechowice-Dziedzice</a><a href="/okay-taxi-kozy/">Kozy</a><a href="/okay-taxi-szczyrk/">Szczyrk</a><a href="/okay-taxi-jasienica/">Jasienica</a><a href="/okay-taxi-cieszyn/">Cieszyn</a><a href="/okay-taxi-oswiecim/">Oświęcim</a><a href="/okay-taxi-wisla/">Wisła</a></div></div>
<div><h4>Kontakt</h4><div class="footer-contact"><a href="tel:+48720535353">+48 720 535 353</a><a href="mailto:marketing@okaytaxi.pl">marketing@okaytaxi.pl</a></div></div>
</div>
<div class="footer-bottom"><p>&copy; 2026 Okay Taxi. Wszelkie prawa zastrzeżone.</p><div class="footer-legal"><a href="/regulamin/">Regulamin</a><a href="/polityka-prywatnosci/">Polityka prywatności</a><a href="/rodo/">RODO</a></div></div>
</div></footer>
<div class="floating-cta"><a href="tel:+48720535353" aria-label="Zadzwoń">{PHONE_SVG}</a></div>
<script src="/js/script.js"></script>
</body></html>"""

CTA = """<section><div class="container"><div class="cta-banner reveal">
<h2>Potrzebujesz taxi? Zadzwoń!</h2>
<p>Nasi kierowcy są gotowi 24/7. Dojazd w&nbsp;kilka minut.</p>
<span class="phone-big"><a href="tel:+48720535353">720 535 353</a></span>
<a href="/aplikacja/" class="btn btn-white btn-lg">Pobierz aplikację</a>
</div></div></section>"""


def write_page(rel_path, content):
    path = os.path.join(BASE, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  OK: {rel_path}")


def page_header(breadcrumbs_html, h1, lead):
    return f"""<section class="page-header"><div class="container">
<nav class="breadcrumbs" style="padding:0 0 1rem">{breadcrumbs_html}</nav>
<h1>{h1}</h1>
<p class="lead">{lead}</p>
</div></section>"""


def bc_html(items):
    parts = []
    for name, url in items[:-1]:
        parts.append(f'<a href="{url}">{name}</a><span>/</span>')
    parts.append(f"<strong>{items[-1][0]}</strong>")
    return "".join(parts)


# ===================================================================
# CENNIK
# ===================================================================
def gen_cennik():
    body = page_header(
        bc_html([("Start", "/"), ("Cennik", "")]),
        'Cennik <span class="text-red">Okay Taxi</span>',
        "Transparentne ceny bez ukrytych opłat. Wiesz ile zapłacisz, zanim wsiądziesz.",
    )
    body += """
<section class="content-section"><div class="container">
<div class="section-header reveal"><span class="section-label">Taryfa miejska</span><h2>Przejazdy po Bielsku-Białej i&nbsp;okolicach</h2></div>
<table class="price-table reveal">
<tr><th>Usługa</th><th>Taryfa dzienna (6:00–22:00)</th><th>Taryfa nocna (22:00–6:00)</th></tr>
<tr><td>Opłata początkowa</td><td>7,00 PLN</td><td>10,50 PLN</td></tr>
<tr><td>Cena za 1&nbsp;km</td><td>3,50 PLN</td><td>5,25 PLN</td></tr>
<tr><td>Oczekiwanie (za godzinę)</td><td>40,00 PLN</td><td>60,00 PLN</td></tr>
<tr><td>Fotelik dziecięcy</td><td colspan="2">bezpłatnie</td></tr>
</table>
<p class="text-muted" style="margin-top:1rem;font-size:var(--font-size-xs)">Ceny orientacyjne. Dokładna kwota zależy od trasy i&nbsp;warunków drogowych.</p>

<div class="section-header reveal" style="margin-top:var(--space-xl)"><span class="section-label">Transfery lotniskowe</span><h2>Ceny transferów na&nbsp;lotniska</h2></div>
<table class="price-table reveal">
<tr><th>Trasa</th><th>Cena od</th><th>Odległość</th></tr>
<tr><td>Bielsko-Biała &rarr; Katowice-Pyrzowice</td><td>250&nbsp;PLN</td><td>~120&nbsp;km</td></tr>
<tr><td>Bielsko-Biała &rarr; Kraków-Balice</td><td>280&nbsp;PLN</td><td>~130&nbsp;km</td></tr>
<tr><td>Bielsko-Biała &rarr; Wiedeń-Schwechat</td><td>od 800&nbsp;PLN</td><td>~380&nbsp;km</td></tr>
</table>

<div class="section-header reveal" style="margin-top:var(--space-xl)"><span class="section-label">Popularne trasy</span><h2>Przykładowe ceny przejazdów</h2></div>
<table class="price-table reveal">
<tr><th>Trasa</th><th>Cena orientacyjna</th><th>Czas</th></tr>
<tr><td>Bielsko-Biała &rarr; Czechowice-Dziedzice</td><td>~55&nbsp;PLN</td><td>~20&nbsp;min</td></tr>
<tr><td>Bielsko-Biała &rarr; Szczyrk</td><td>~50&nbsp;PLN</td><td>~25&nbsp;min</td></tr>
<tr><td>Bielsko-Biała &rarr; Kozy</td><td>~35&nbsp;PLN</td><td>~12&nbsp;min</td></tr>
<tr><td>Bielsko-Biała &rarr; Cieszyn</td><td>~120&nbsp;PLN</td><td>~40&nbsp;min</td></tr>
<tr><td>Bielsko-Biała &rarr; Oświęcim</td><td>~130&nbsp;PLN</td><td>~45&nbsp;min</td></tr>
<tr><td>Bielsko-Biała &rarr; Wisła</td><td>~140&nbsp;PLN</td><td>~50&nbsp;min</td></tr>
</table>
<p class="text-muted" style="margin-top:1rem;font-size:var(--font-size-xs)">Dokładną wycenę uzyskasz telefonicznie: <a href="tel:+48720535353" style="color:var(--red)">720 535 353</a>.</p>
</div></section>"""
    body += CTA
    return (
        make_head(
            "Cennik Taxi — Okay Taxi Bielsko-Biała | Transparentne Ceny",
            "Cennik Okay Taxi — transparentne ceny przejazdów, transferów lotniskowych i tras długich. Brak ukrytych opłat.",
            "/cennik/",
        )
        + breadcrumb_ld([("Start", "/"), ("Cennik", "/cennik/")])
        + "</head><body>"
        + nav_html("/cennik/")
        + body
        + FOOTER
    )


# ===================================================================
# APLIKACJA
# ===================================================================
def gen_aplikacja():
    body = page_header(
        bc_html([("Start", "/"), ("Aplikacja", "")]),
        'Aplikacja <span class="text-red">Okay Taxi</span>',
        "Zamów taxi jednym kliknięciem. Śledź taksówkę na mapie, płać bez gotówki, oceniaj kierowcę.",
    )
    body += f"""
<section class="content-section"><div class="container">
<div class="two-col">
<div class="reveal">
<span class="section-label">Funkcje</span>
<h2>Wszystko w&nbsp;jednej aplikacji</h2>
<p>Aplikacja Okay Taxi daje Ci pełną kontrolę nad przejazdem. Zamawiaj taxi z&nbsp;dowolnego miejsca, śledź pojazd na mapie w&nbsp;czasie rzeczywistym i&nbsp;płać wygodnie — kartą, BLIK lub w&nbsp;aplikacji. Koniec z&nbsp;szukaniem gotówki czy czekaniem na resztę.</p>
<ul class="content-section">
<li>Zamawianie taxi jednym dotknięciem ekranu</li>
<li>Śledzenie taksówki na mapie w&nbsp;czasie rzeczywistym</li>
<li>Płatność kartą, BLIK lub bezgotówkowo</li>
<li>Historia wszystkich przejazdów i&nbsp;rachunki</li>
<li>Zapisane ulubione adresy — szybsze zamawianie</li>
<li>Ocena kierowcy po każdym kursie</li>
<li>Szacunkowa cena przejazdu przed zamówieniem</li>
<li>Powiadomienia push o&nbsp;statusie zamówienia</li>
</ul>
<div style="display:flex;gap:1rem;margin-top:1.5rem;flex-wrap:wrap">
<a href="tel:+48720535353" class="btn btn-primary">Zadzwoń: 720 535 353</a>
</div>
</div>
<div class="reveal" style="text-align:center">
<img src="{TEL_IMG}" alt="Aplikacja Okay Taxi na smartfonie" width="300" height="644" loading="lazy" decoding="async" style="max-width:280px;border-radius:24px;box-shadow:var(--shadow-xl)">
</div>
</div>
</div></section>

<section class="section-alt"><div class="container">
<div class="section-header center reveal"><span class="section-label">Jak to działa</span><h2>3&nbsp;kroki do&nbsp;przejazdu</h2></div>
<div class="grid-3">
<div class="card reveal reveal-delay-1"><div class="card-icon">1</div><h3>Pobierz aplikację</h3><p>Zainstaluj Okay Taxi na swoim telefonie — dostępna na Android i&nbsp;iOS. Rejestracja zajmuje minutę.</p></div>
<div class="card reveal reveal-delay-2"><div class="card-icon">2</div><h3>Podaj adres</h3><p>Wpisz dokąd jedziesz. Aplikacja pokaże szacunkową cenę i&nbsp;czas dojazdu taksówki.</p></div>
<div class="card reveal reveal-delay-3"><div class="card-icon">3</div><h3>Jedź!</h3><p>Śledź pojazd na mapie, wsiądź i&nbsp;jedź. Na końcu oceń kierowcę i&nbsp;zapłać wygodnie.</p></div>
</div>
</div></section>"""
    body += CTA
    return (
        make_head(
            "Aplikacja Okay Taxi — Zamów Taxi ze Smartfona | Bielsko-Biała",
            "Pobierz aplikację Okay Taxi. Zamawiaj taxi jednym kliknięciem, śledź taksówkę na mapie, płać kartą lub BLIK.",
            "/aplikacja/",
        )
        + breadcrumb_ld([("Start", "/"), ("Aplikacja", "/aplikacja/")])
        + "</head><body>"
        + nav_html("/aplikacja/")
        + body
        + FOOTER
    )


# ===================================================================
# OKAYKA
# ===================================================================
def gen_okayka():
    partners = [
        ("Al Capone", "al-capone", "Restauracja i pub"),
        ("Tajemnicza Piwnica", "tajemnicza-piwnica", "Restauracja"),
        ("2BE Club", "2be-club", "Klub rozrywkowy"),
        ("Barimed", "barimed", "Klinika medyczna"),
        ("Czarny Tech", "czarny-tech", "Firma technologiczna"),
        ("Grupa Tobi", "grupa-tobi", "Grupa biznesowa"),
        ("Sports Arena", "sports-arena", "Obiekt sportowy"),
        ("Eco Horizon", "eco-horizon", "Firma ekologiczna"),
        ("EcuSoft", "ecusoft", "Firma IT"),
        ("Magnum", "magnum", "Restauracja i bar"),
        ("Stek i Wino", "stek-i-wino", "Restauracja steakhouse"),
    ]
    partner_cards = ""
    for name, slug, desc in partners:
        partner_cards += f"""<a href="/partner-okayka/{slug}/" class="card reveal" style="text-decoration:none">
<h3>{name}</h3><p>{desc}</p><span style="color:var(--red);font-size:var(--font-size-sm);font-weight:600">Zobacz rabat &rarr;</span></a>\n"""

    body = page_header(
        bc_html([("Start", "/"), ("Okayka", "")]),
        'Program <span class="text-red">Okayka</span>',
        "Zbieraj punkty za każdy przejazd i&nbsp;wymieniaj na rabaty u&nbsp;naszych partnerów. Lojalność z&nbsp;Okay Taxi się opłaca.",
    )
    body += f"""
<section class="content-section"><div class="container">
<div class="section-header center reveal"><span class="section-label">Jak to działa</span><h2>3&nbsp;proste kroki</h2></div>
<div class="grid-3">
<div class="card reveal reveal-delay-1"><div class="card-icon">🚕</div><h3>Jedź z&nbsp;Okay Taxi</h3><p>Każdy przejazd białoczerwonymi taksówkami automatycznie nalicza punkty na Twoje konto Okayka. Nie musisz niczego aktywować.</p></div>
<div class="card reveal reveal-delay-2"><div class="card-icon">⭐</div><h3>Zbieraj punkty</h3><p>Punkty kumulują się na Twoim koncie. Im więcej jeździsz, tym szybciej rosną. Sprawdzaj saldo w&nbsp;aplikacji lub u&nbsp;kierowcy.</p></div>
<div class="card reveal reveal-delay-3"><div class="card-icon">🎁</div><h3>Korzystaj z&nbsp;rabatów</h3><p>Wymieniaj punkty na zniżki u&nbsp;partnerów Okayka — restauracje, hotele, sport, wellness i&nbsp;wiele więcej w&nbsp;całym regionie.</p></div>
</div>
</div></section>

<section class="section-alt"><div class="container">
<div class="section-header center reveal"><span class="section-label">Partnerzy</span><h2>Gdzie wykorzystasz punkty Okayka</h2>
<p class="section-desc">Nasi partnerzy to najlepsze lokale i&nbsp;firmy w&nbsp;Bielsku-Białej. Pokazuj kartę Okayka i&nbsp;korzystaj ze zniżek.</p></div>
<div class="features-grid">{partner_cards}</div>
<div class="text-center reveal" style="margin-top:var(--space-lg)"><a href="/partner-okayka/" class="btn btn-outline">Zobacz wszystkich partnerów</a></div>
</div></section>"""
    body += CTA
    return (
        make_head(
            "Program Okayka — Zbieraj Punkty za Przejazdy | Okay Taxi",
            "Program lojalnościowy Okayka — zbieraj punkty za przejazdy Okay Taxi i wymieniaj na rabaty w restauracjach, hotelach i obiektach sportowych.",
            "/okayka/",
        )
        + breadcrumb_ld([("Start", "/"), ("Okayka", "/okayka/")])
        + "</head><body>"
        + nav_html("/okayka/")
        + body
        + FOOTER
    )


# ===================================================================
# DLA NIEPELNOSPRAWNYCH
# ===================================================================
def gen_dostepnosc():
    body = page_header(
        bc_html([("Start", "/"), ("Dla niepełnosprawnych", "")]),
        'Taxi dla <span class="text-red">niepełnosprawnych</span>',
        "Okay Taxi zapewnia transport dla osób z&nbsp;niepełnosprawnościami. Przystosowane pojazdy, przeszkoleni kierowcy, pełna empatia.",
    )
    body += """
<section class="content-section"><div class="container">
<div class="two-col">
<div class="reveal">
<span class="section-label">Dostępność</span>
<h2>Transport dla każdego</h2>
<p>Wierzymy, że mobilność to prawo, nie przywilej. Dlatego Okay Taxi oferuje specjalnie przystosowane pojazdy i&nbsp;przeszkolonych kierowców, którzy pomogą osobom z&nbsp;niepełnosprawnościami bezpiecznie i&nbsp;komfortowo dotrzeć do celu.</p>
<p>Nasi kierowcy przechodzą szkolenia z&nbsp;zakresu pomocy osobom o&nbsp;ograniczonej mobilności — od osób na wózkach inwalidzkich, przez osoby niewidome, po seniorów potrzebujących dodatkowej asysty przy wsiadaniu i&nbsp;wysiadaniu.</p>
</div>
<div class="content-img reveal">
<img src=""" + f'"{BANNER}"' + """ alt="Okay Taxi — taxi dostępne dla osób z niepełnosprawnościami" width="1390" height="782" loading="lazy" decoding="async">
</div>
</div>
</div></section>

<section class="section-alt"><div class="container">
<div class="section-header center reveal"><span class="section-label">Co oferujemy</span><h2>Nasz standard dostępności</h2></div>
<div class="grid-3">
<div class="a11y-card reveal reveal-delay-1"><h3>♿ Pojazdy przystosowane</h3><p>Dysponujemy pojazdami z&nbsp;obniżonym progiem wejścia i&nbsp;przestrzenią na wózek inwalidzki. Zgłoś potrzebę przy zamawianiu — podstawimy odpowiedni pojazd.</p></div>
<div class="a11y-card reveal reveal-delay-2"><h3>🤝 Przeszkoleni kierowcy</h3><p>Nasi kierowcy wiedzą, jak pomóc przy wsiadaniu, złożyć wózek, asystować osobie niewidomej. Profesjonalnie i&nbsp;z&nbsp;empatią.</p></div>
<div class="a11y-card reveal reveal-delay-3"><h3>📞 Łatwe zamawianie</h3><p>Zamów telefonicznie pod <a href="tel:+48720535353" style="color:var(--red);font-weight:600">720 535 353</a> — poinformuj dyspozytora o&nbsp;potrzebach specjalnych, a&nbsp;dopasujemy pojazd i&nbsp;kierowcę.</p></div>
<div class="a11y-card reveal reveal-delay-1"><h3>🏥 Transfery medyczne</h3><p>Dowozimy na wizyty lekarskie, rehabilitację, badania. Kierowca poczeka i&nbsp;odwiezie z&nbsp;powrotem.</p></div>
<div class="a11y-card reveal reveal-delay-2"><h3>💳 Wygodna płatność</h3><p>Gotówka, karta, BLIK — wybierz co Ci wygodniej. Firmy i&nbsp;instytucje mogą korzystać z&nbsp;programów bezgotówkowych z&nbsp;fakturami zbiorczymi.</p></div>
<div class="a11y-card reveal reveal-delay-3"><h3>🕐 Rezerwacja z wyprzedzeniem</h3><p>Zaplanuj przejazd z&nbsp;wyprzedzeniem — gwarantujemy pojazd na wskazaną godzinę. Idealne przy wizytach lekarskich.</p></div>
</div>
</div></section>"""
    body += CTA
    return (
        make_head(
            "Taxi dla Niepełnosprawnych — Okay Taxi Bielsko-Biała | Dostępny Transport",
            "Okay Taxi dla osób z niepełnosprawnościami — przystosowane pojazdy, przeszkoleni kierowcy, pomoc przy wsiadaniu. Zamów: 720 535 353.",
            "/dla-niepelnosprawnych/",
        )
        + breadcrumb_ld([("Start", "/"), ("Dla niepełnosprawnych", "/dla-niepelnosprawnych/")])
        + "</head><body>"
        + nav_html("/dla-niepelnosprawnych/")
        + body
        + FOOTER
    )


# ===================================================================
# PROGRAMY BEZGOTOWKOWE
# ===================================================================
def gen_firmy():
    body = page_header(
        bc_html([("Start", "/"), ("Programy bezgotówkowe", "")]),
        'Programy <span class="text-red">bezgotówkowe</span> dla&nbsp;firm',
        "Rozliczenia firmowe, faktury zbiorcze, dedykowane konta. Uprość transport pracowników z&nbsp;Okay Taxi.",
    )
    body += """
<section class="content-section"><div class="container">
<div class="two-col">
<div class="reveal">
<span class="section-label">Dla biznesu</span>
<h2>Transport firmowy bez komplikacji</h2>
<p>Okay Taxi oferuje programy bezgotówkowe dla firm, instytucji i&nbsp;organizacji. Twoi pracownicy jeżdżą taksówkami, a&nbsp;Ty dostajesz jedną zbiorczą fakturę na koniec miesiąca. Koniec z&nbsp;delegacjami, rachunkami i&nbsp;rozliczaniem gotówki.</p>
<ul class="content-section">
<li>Konto firmowe z&nbsp;indywidualnym opiekunem</li>
<li>Faktury zbiorcze — miesięczne lub dwutygodniowe</li>
<li>Panel online z&nbsp;historią przejazdów pracowników</li>
<li>Limity kwotowe i&nbsp;godzinowe per pracownik</li>
<li>Raporty przejazdów w&nbsp;formacie CSV/PDF</li>
<li>Brak opłat za aktywację konta firmowego</li>
</ul>
<a href="mailto:marketing@okaytaxi.pl" class="btn btn-primary mt-md">Zapytaj o ofertę firmową</a>
</div>
<div class="content-img reveal">
<img src=""" + f'"{BANNER}"' + """ alt="Okay Taxi — programy firmowe i bezgotówkowe" width="1390" height="782" loading="lazy" decoding="async">
</div>
</div>
</div></section>"""
    body += CTA
    return (
        make_head(
            "Programy Bezgotówkowe dla Firm — Okay Taxi | Rozliczenia Firmowe",
            "Programy bezgotówkowe Okay Taxi dla firm — faktury zbiorcze, konta firmowe, raporty przejazdów. Uprość transport pracowników.",
            "/programy-bezgotowkowe/",
        )
        + breadcrumb_ld([("Start", "/"), ("Programy bezgotówkowe", "/programy-bezgotowkowe/")])
        + "</head><body>"
        + nav_html()
        + body
        + FOOTER
    )


# ===================================================================
# LOCATION PAGES
# ===================================================================
LOCATIONS = {
    "okay-taxi-kozy": {
        "city": "Kozy",
        "title": "Taxi Kozy — Okay Taxi | Zamów 720 535 353",
        "desc": "Taxi w Kozach — Okay Taxi. Szybki dojazd, transfery do Bielska-Białej i na lotnisko. Zadzwoń: 720 535 353.",
        "h1": 'Taxi <span class="text-red">Kozy</span>',
        "lead": "Zamawiasz taxi w Kozach? Okay Taxi dojedzie do Ciebie w kilka minut. Obsługujemy Kozy i okolice 24 godziny na dobę.",
        "content": """<p>Kozy to dynamicznie rozwijająca się gmina położona zaledwie 8&nbsp;km od centrum Bielska-Białej. Okay Taxi zapewnia szybki i&nbsp;komfortowy transport z&nbsp;Kóz do Bielska, na lotniska oraz w&nbsp;dowolne miejsce w&nbsp;regionie Podbeskidzia.</p>
<p>Nasi kierowcy znają Kozy jak własną kieszeń — od głównych ulic po osiedla i&nbsp;przysiółki. Niezależnie czy jedziesz do centrum Bielska na zakupy, do pracy, na dworzec kolejowy czy na lotnisko Katowice-Pyrzowice — z&nbsp;Okay Taxi dotrzesz na czas i&nbsp;w&nbsp;komforcie.</p>
<h3>Popularne trasy z&nbsp;Kóz</h3>
<ul class="content-section">
<li>Kozy &rarr; Centrum Bielska-Białej (~8&nbsp;km, ~12&nbsp;min)</li>
<li>Kozy &rarr; Galeria Sfera (~10&nbsp;km, ~15&nbsp;min)</li>
<li>Kozy &rarr; Dworzec PKP Bielsko-Biała (~9&nbsp;km, ~14&nbsp;min)</li>
<li>Kozy &rarr; Lotnisko Katowice-Pyrzowice (~115&nbsp;km, ~80&nbsp;min)</li>
<li>Kozy &rarr; Szczyrk (~20&nbsp;km, ~30&nbsp;min)</li>
</ul>""",
    },
    "okay-taxi-szczyrk": {
        "city": "Szczyrk",
        "title": "Taxi Szczyrk — Okay Taxi | Zamów 720 535 353",
        "desc": "Taxi w Szczyrku — transfery na stoki, do hoteli i z Bielska-Białej. Okay Taxi 24/7. Zadzwoń: 720 535 353.",
        "h1": 'Taxi <span class="text-red">Szczyrk</span>',
        "lead": "Taxi w Szczyrku — dojazd na stok, do hotelu, z dworca. Okay Taxi obsługuje Szczyrk codziennie, cały rok.",
        "content": """<p>Szczyrk to jedno z&nbsp;najpopularniejszych miejsc turystycznych na Podbeskidziu — zimą przyciąga narciarzy, latem turystów pieszych i&nbsp;rowerowych. Okay Taxi zapewnia komfortowy transport do i&nbsp;ze Szczyrku przez cały rok.</p>
<p>Dowozimy na stoki narciarskie Szczyrk Mountain Resort i&nbsp;COS, do hoteli, pensjonatów i&nbsp;apartamentów. Wracasz z&nbsp;nart zmęczony? Nie musisz prowadzić — zadzwoń, a&nbsp;przyjedziemy pod wyciąg.</p>
<h3>Popularne trasy</h3>
<ul class="content-section">
<li>Bielsko-Biała &rarr; Szczyrk centrum (~18&nbsp;km, ~25&nbsp;min)</li>
<li>Bielsko-Biała &rarr; Szczyrk Mountain Resort (~20&nbsp;km, ~30&nbsp;min)</li>
<li>Szczyrk &rarr; Lotnisko Katowice-Pyrzowice (~130&nbsp;km, ~90&nbsp;min)</li>
<li>Szczyrk &rarr; Wisła (~35&nbsp;km, ~45&nbsp;min)</li>
</ul>
<h3>Dlaczego Okay Taxi w&nbsp;Szczyrku?</h3>
<p>Nasi kierowcy znają górskie drogi i&nbsp;potrafią bezpiecznie prowadzić w&nbsp;zimowych warunkach. Pojazdy mają opony zimowe, a&nbsp;w&nbsp;razie potrzeby — łańcuchy. Nie ryzykuj jazdy po oblodzonych drogach — zaufaj profesjonalistom.</p>""",
    },
    "okay-taxi-jasienica": {
        "city": "Jasienica",
        "title": "Taxi Jasienica — Okay Taxi | Zamów 720 535 353",
        "desc": "Taxi w Jasienicy — szybki dojazd do Bielska-Białej i okolic. Okay Taxi 24/7. Zamów: 720 535 353.",
        "h1": 'Taxi <span class="text-red">Jasienica</span>',
        "lead": "Okay Taxi w Jasienicy — komfortowe przejazdy do Bielska-Białej, na lotniska i w okolice. Dostępni 24/7.",
        "content": """<p>Jasienica to gmina granicząca z&nbsp;Bielskiem-Białą, zamieszkała przez ponad 17&nbsp;tysięcy osób. Okay Taxi zapewnia szybki transport z&nbsp;Jasienicy do centrum Bielska, na dworzec, do galerii handlowych i&nbsp;na lotniska.</p>
<p>Obsługujemy wszystkie sołectwa gminy Jasienica — Jasienicę, Mazańcowice, Rudzicę, Łazy, Grodziec, Międzyrzecze i&nbsp;okolice. Dojazd taksówki trwa kilkanaście minut.</p>
<h3>Popularne trasy z&nbsp;Jasienicy</h3>
<ul class="content-section">
<li>Jasienica &rarr; Bielsko-Biała centrum (~10&nbsp;km, ~15&nbsp;min)</li>
<li>Jasienica &rarr; Czechowice-Dziedzice (~12&nbsp;km, ~18&nbsp;min)</li>
<li>Jasienica &rarr; Lotnisko Katowice-Pyrzowice (~110&nbsp;km, ~75&nbsp;min)</li>
</ul>""",
    },
    "okay-taxi-cieszyn": {
        "city": "Cieszyn",
        "title": "Taxi Cieszyn — Okay Taxi | Zamów 720 535 353",
        "desc": "Taxi w Cieszynie — przejazdy miejskie, transgraniczne do Českého Těšínu i transfery. Okay Taxi 24/7.",
        "h1": 'Taxi <span class="text-red">Cieszyn</span>',
        "lead": "Taxi w Cieszynie i okolicach. Przejazdy miejskie, transgraniczne do Českého Těšínu, transfery na lotniska.",
        "content": """<p>Cieszyn to historyczne miasto na polsko-czeskiej granicy, znane z&nbsp;pięknej starówki i&nbsp;mostu na Olzie łączącego Cieszyn z&nbsp;Českým Těšínem. Okay Taxi obsługuje Cieszyn i&nbsp;oferuje unikalne usługi transgraniczne.</p>
<p>Dowozimy turystów na cieszyńską starówkę, do Muzeum Śląska Cieszyńskiego, na dworzec PKP i&nbsp;autobusowy. Realizujemy też przejazdy transgraniczne — z&nbsp;polskiego Cieszyna do czeskiego i&nbsp;z&nbsp;powrotem.</p>
<h3>Popularne trasy</h3>
<ul class="content-section">
<li>Cieszyn &rarr; Český Těšín (centrum, ~3&nbsp;km, ~8&nbsp;min)</li>
<li>Cieszyn &rarr; Bielsko-Biała (~35&nbsp;km, ~40&nbsp;min)</li>
<li>Cieszyn &rarr; Lotnisko Katowice-Pyrzowice (~130&nbsp;km, ~90&nbsp;min)</li>
<li>Cieszyn &rarr; Ustroń (~10&nbsp;km, ~15&nbsp;min)</li>
<li>Cieszyn &rarr; Wisła (~25&nbsp;km, ~35&nbsp;min)</li>
</ul>""",
    },
    "okay-taxi-oswiecim": {
        "city": "Oświęcim",
        "title": "Taxi Oświęcim — Okay Taxi | Zamów 720 535 353",
        "desc": "Taxi w Oświęcimiu — transfery do Muzeum Auschwitz, na dworzec i lotniska. Okay Taxi 24/7. Tel. 720 535 353.",
        "h1": 'Taxi <span class="text-red">Oświęcim</span>',
        "lead": "Taxi w Oświęcimiu — transfery turystyczne, dojazdy do Muzeum Auschwitz-Birkenau, na dworzec i lotniska.",
        "content": """<p>Oświęcim jest jednym z&nbsp;najczęściej odwiedzanych miast w&nbsp;Polsce ze względu na Muzeum Auschwitz-Birkenau. Okay Taxi zapewnia profesjonalny transport dla turystów i&nbsp;mieszkańców Oświęcimia.</p>
<p>Dowozimy turystów z&nbsp;dworców kolejowych i&nbsp;autobusowych bezpośrednio pod Muzeum. Realizujemy też transfery z&nbsp;lotnisk Katowice-Pyrzowice i&nbsp;Kraków-Balice do Oświęcimia i&nbsp;z&nbsp;powrotem. Nasi kierowcy mówią po angielsku — bez problemu obsłużą zagranicznych gości.</p>
<h3>Popularne trasy</h3>
<ul class="content-section">
<li>Dworzec PKP Oświęcim &rarr; Muzeum Auschwitz (~3&nbsp;km, ~8&nbsp;min)</li>
<li>Oświęcim &rarr; Bielsko-Biała (~40&nbsp;km, ~45&nbsp;min)</li>
<li>Oświęcim &rarr; Kraków centrum (~65&nbsp;km, ~60&nbsp;min)</li>
<li>Oświęcim &rarr; Lotnisko Kraków-Balice (~60&nbsp;km, ~55&nbsp;min)</li>
<li>Oświęcim &rarr; Lotnisko Katowice-Pyrzowice (~75&nbsp;km, ~60&nbsp;min)</li>
</ul>""",
    },
    "okay-taxi-wisla": {
        "city": "Wisła",
        "title": "Taxi Wisła — Okay Taxi | Zamów 720 535 353",
        "desc": "Taxi w Wiśle — transfery turystyczne, dojazd na skocznie Malinka, do hoteli SPA. Okay Taxi 24/7.",
        "h1": 'Taxi <span class="text-red">Wisła</span>',
        "lead": "Taxi w Wiśle — skocznie, hotele, SPA, Beskidy. Okay Taxi dowiezie Cię bezpiecznie, o&nbsp;każdej porze.",
        "content": """<p>Wisła to uzdrowisko i&nbsp;kurort narciarski w&nbsp;sercu Beskidu Śląskiego. Okay Taxi obsługuje Wisłę przez cały rok — zimą dowozimy narciarzy na stoki, latem turystów na szlaki, a&nbsp;przez cały rok gości hotelowych i&nbsp;uczestników konferencji.</p>
<p>Dowozimy na skocznie im. Adama Małysza (Malinka), do Centrum Sportów Zimowych, hoteli SPA i&nbsp;pensjonatów. Realizujemy też transfery z&nbsp;lotnisk i&nbsp;dworców bezpośrednio do Wisły.</p>
<h3>Popularne trasy</h3>
<ul class="content-section">
<li>Wisła &rarr; Bielsko-Biała (~50&nbsp;km, ~50&nbsp;min)</li>
<li>Wisła &rarr; Cieszyn (~25&nbsp;km, ~35&nbsp;min)</li>
<li>Wisła &rarr; Ustroń (~10&nbsp;km, ~15&nbsp;min)</li>
<li>Wisła &rarr; Lotnisko Katowice-Pyrzowice (~150&nbsp;km, ~100&nbsp;min)</li>
</ul>
<h3>Dlaczego Okay Taxi w&nbsp;Wiśle?</h3>
<p>Górskie drogi wymagają doświadczenia. Nasi kierowcy jeżdżą po Beskidach od lat, a&nbsp;pojazdy są przygotowane na warunki zimowe. Dojedziemy bezpiecznie nawet gdy pada śnieg.</p>""",
    },
}


def gen_location(slug, data):
    body = page_header(
        bc_html([("Start", "/"), (f"Taxi {data['city']}", "")]),
        data["h1"],
        data["lead"],
    )
    body += f"""
<section class="content-section"><div class="container">
<div class="two-col">
<div class="reveal">
<span class="section-label">Okay Taxi {data['city']}</span>
<h2>Zamów taxi w&nbsp;{data['city']}</h2>
{data['content']}
<a href="tel:+48720535353" class="btn btn-primary mt-md">Zadzwoń: 720 535 353</a>
</div>
<div class="content-img reveal">
<img src="{BANNER}" alt="Okay Taxi {data['city']}" width="1390" height="782" loading="lazy" decoding="async">
</div>
</div>
</div></section>"""
    body += CTA
    return (
        make_head(data["title"], data["desc"], f"/{slug}/")
        + breadcrumb_ld([("Start", "/"), (f"Taxi {data['city']}", f"/{slug}/")])
        + "</head><body>"
        + nav_html()
        + body
        + FOOTER
    )


# ===================================================================
# LEGAL PAGES
# ===================================================================
def gen_legal(slug, title, h1, content, robots="noindex, follow"):
    body = page_header(
        bc_html([("Start", "/"), (h1, "")]),
        h1,
        "",
    )
    body += f'<section class="content-section"><div class="container"><div class="legal-content reveal">{content}</div></div></section>'
    return (
        make_head(title, f"{h1} — Okay Taxi Bielsko-Biała", f"/{slug}/", robots=robots)
        + breadcrumb_ld([("Start", "/"), (h1, f"/{slug}/")])
        + "</head><body>"
        + nav_html()
        + body
        + FOOTER
    )


REGULAMIN_CONTENT = """
<h2>1. Postanowienia ogólne</h2>
<p>Niniejszy regulamin określa zasady świadczenia usług przewozu osób przez Okay Taxi z&nbsp;siedzibą w&nbsp;Bielsku-Białej.</p>
<h2>2. Zamawianie przejazdu</h2>
<p>Przejazd można zamówić telefonicznie pod numerem <strong>720 535 353</strong>, przez aplikację mobilną Okay Taxi lub bezpośrednio u&nbsp;kierowcy na postoju. Zamówienie jest wiążące od momentu potwierdzenia przez dyspozytora.</p>
<h2>3. Realizacja przejazdu</h2>
<p>Kierowca zobowiązuje się do realizacji przejazdu najkrótszą trasą, chyba że pasażer wskaże inną. Opłata naliczana jest według taksometru lub ustalonej wcześniej stawki ryczałtowej (transfery).</p>
<h2>4. Płatności</h2>
<p>Akceptujemy gotówkę, karty płatnicze (Visa, Mastercard), płatności BLIK oraz płatności w&nbsp;aplikacji. Firmy korzystające z&nbsp;programów bezgotówkowych rozliczają się na podstawie faktur zbiorczych.</p>
<h2>5. Anulowanie zamówienia</h2>
<p>Pasażer może anulować zamówienie bez opłat do momentu przyjazdu taksówki. Po przyjeździe taksówki i&nbsp;braku pasażera może zostać naliczona opłata za dojazd.</p>
<h2>6. Reklamacje</h2>
<p>Reklamacje można składać mailowo na adres <a href="mailto:marketing@okaytaxi.pl">marketing@okaytaxi.pl</a> lub telefonicznie. Rozpatrujemy reklamacje w&nbsp;ciągu 14 dni roboczych.</p>
<h2>7. Odpowiedzialność</h2>
<p>Okay Taxi odpowiada za bezpieczeństwo pasażerów podczas przejazdu. Nie ponosimy odpowiedzialności za rzeczy pozostawione w&nbsp;pojeździe, choć dokładamy starań, aby je odnaleźć.</p>
<h2>8. Postanowienia końcowe</h2>
<p>Regulamin wchodzi w&nbsp;życie z&nbsp;dniem publikacji na stronie okaytaxi.pl. Okay Taxi zastrzega sobie prawo do zmian regulaminu.</p>
"""

POLITYKA_CONTENT = """
<h2>1. Administrator danych</h2>
<p>Administratorem Twoich danych osobowych jest Okay Taxi z&nbsp;siedzibą w&nbsp;Bielsku-Białej. Kontakt: <a href="mailto:marketing@okaytaxi.pl">marketing@okaytaxi.pl</a>.</p>
<h2>2. Jakie dane zbieramy</h2>
<p>Zbieramy dane niezbędne do realizacji usług przewozu: numer telefonu, adres odbioru, adres docelowy, historię przejazdów. W&nbsp;przypadku kont firmowych — dane firmowe potrzebne do wystawienia faktury.</p>
<h2>3. Cel przetwarzania</h2>
<p>Dane przetwarzamy w&nbsp;celu realizacji zamówień taxi, obsługi programu Okayka, rozliczeń finansowych, obsługi reklamacji oraz — za Twoją zgodą — w&nbsp;celach marketingowych.</p>
<h2>4. Pliki cookies</h2>
<p>Strona okaytaxi.pl używa plików cookies w&nbsp;celu analizy ruchu i&nbsp;personalizacji treści. Możesz zarządzać cookies w&nbsp;ustawieniach przeglądarki.</p>
<h2>5. Twoje prawa</h2>
<p>Masz prawo dostępu do swoich danych, ich sprostowania, usunięcia, ograniczenia przetwarzania oraz przenoszenia. Możesz też wnieść sprzeciw wobec przetwarzania i&nbsp;złożyć skargę do Prezesa UODO.</p>
<h2>6. Okres przechowywania</h2>
<p>Dane przechowujemy przez okres niezbędny do realizacji usług i&nbsp;wypełnienia obowiązków prawnych (np. przepisy podatkowe — 5 lat).</p>
"""

RODO_CONTENT = """
<h2>Informacja o przetwarzaniu danych osobowych (RODO)</h2>
<p>Zgodnie z&nbsp;art. 13 Rozporządzenia Parlamentu Europejskiego i&nbsp;Rady (UE) 2016/679 z&nbsp;dnia 27 kwietnia 2016&nbsp;r. (RODO) informujemy:</p>
<h3>Administrator</h3>
<p>Administratorem Twoich danych osobowych jest Okay Taxi z&nbsp;siedzibą w&nbsp;Bielsku-Białej. Kontakt: <a href="mailto:marketing@okaytaxi.pl">marketing@okaytaxi.pl</a>, tel. <a href="tel:+48720535353">720 535 353</a>.</p>
<h3>Podstawa prawna</h3>
<p>Przetwarzamy Twoje dane na podstawie: art. 6 ust. 1 lit. b RODO (wykonanie umowy), art. 6 ust. 1 lit. c RODO (obowiązek prawny), art. 6 ust. 1 lit. f RODO (prawnie uzasadniony interes) oraz art. 6 ust. 1 lit. a RODO (zgoda — marketing).</p>
<h3>Twoje prawa</h3>
<ul class="content-section">
<li>Prawo dostępu do danych (art. 15 RODO)</li>
<li>Prawo do sprostowania (art. 16 RODO)</li>
<li>Prawo do usunięcia — „prawo do bycia zapomnianym" (art. 17 RODO)</li>
<li>Prawo do ograniczenia przetwarzania (art. 18 RODO)</li>
<li>Prawo do przenoszenia danych (art. 20 RODO)</li>
<li>Prawo do sprzeciwu (art. 21 RODO)</li>
<li>Prawo do cofnięcia zgody (art. 7 ust. 3 RODO)</li>
<li>Prawo do wniesienia skargi do Prezesa UODO</li>
</ul>
"""

REKLAMACJA_CONTENT = """
<h2>Jak złożyć reklamację</h2>
<p>Jeśli coś poszło nie tak podczas przejazdu z&nbsp;Okay Taxi, chcemy o&nbsp;tym wiedzieć. Twoja opinia pomaga nam się poprawiać.</p>
<h3>Sposoby złożenia reklamacji</h3>
<ul class="content-section">
<li><strong>E-mail:</strong> <a href="mailto:marketing@okaytaxi.pl" style="color:var(--red)">marketing@okaytaxi.pl</a></li>
<li><strong>Telefon:</strong> <a href="tel:+48720535353" style="color:var(--red)">720 535 353</a></li>
<li><strong>Aplikacja:</strong> sekcja „Pomoc" w aplikacji Okay Taxi</li>
</ul>
<h3>Co powinno zawierać zgłoszenie</h3>
<ul class="content-section">
<li>Data i&nbsp;godzina przejazdu</li>
<li>Trasa (skąd — dokąd)</li>
<li>Numer taksówki lub imię kierowcy (jeśli pamiętasz)</li>
<li>Opis problemu</li>
<li>Twoje dane kontaktowe (imię, telefon lub e-mail)</li>
</ul>
<h3>Czas rozpatrzenia</h3>
<p>Reklamacje rozpatrujemy w&nbsp;ciągu <strong>14 dni roboczych</strong>. Odpowiedź otrzymasz na podany adres e-mail lub telefonicznie.</p>
"""


# ===================================================================
# PARTNER PAGES
# ===================================================================
PARTNERS = [
    ("al-capone", "Al Capone", "Restauracja i pub w Bielsku-Białej znana z włoskiej kuchni i wyjątkowej atmosfery. Jako partner Okayka oferuje zniżki na posiłki dla klientów Okay Taxi."),
    ("tajemnicza-piwnica", "Tajemnicza Piwnica", "Klimatyczna restauracja w podziemiach Bielska-Białej. Partner Okayka — okaż kartę i otrzymaj rabat na menu."),
    ("2be-club", "2BE Club", "Popularny klub rozrywkowy w Bielsku-Białej. Jako partner Okayka oferuje zniżki na wejścia i napoje dla posiadaczy karty."),
    ("barimed", "Barimed", "Klinika medyczna i wellness w Bielsku-Białej. Partner Okayka — specjalne ceny na zabiegi dla klientów Okay Taxi."),
    ("czarny-tech", "Czarny Tech", "Firma technologiczna z Bielska-Białej, partner programu Okayka. Zniżki na usługi IT i serwis sprzętu."),
    ("grupa-tobi", "Grupa Tobi", "Grupa biznesowa działająca w regionie Podbeskidzia. Partner Okayka wspierający lokalny rozwój i oferujący zniżki."),
    ("sports-arena", "Sports Arena", "Obiekt sportowy w Bielsku-Białej — siłownia, fitness, squash. Zniżki na karnety dla posiadaczy karty Okayka."),
    ("okay-taxi", "Okay Taxi", "Tak — sami też jesteśmy partnerem Okayka! Zbieraj punkty i wymieniaj na darmowe przejazdy białoczerwonymi taksówkami."),
    ("eco-horizon", "Eco Horizon", "Firma ekologiczna z Bielska-Białej. Partner Okayka oferujący zniżki na produkty eko i usługi zrównoważone."),
    ("ecusoft", "EcuSoft", "Firma IT specjalizująca się w oprogramowaniu. Partner Okayka — rabaty na usługi programistyczne i konsulting."),
    ("magnum", "Magnum", "Restauracja i bar w Bielsku-Białej. Jako partner Okayka oferuje zniżki na menu i napoje."),
    ("stek-i-wino", "Stek i Wino", "Restauracja steakhouse w Bielsku-Białej. Partner Okayka — okaż kartę lojalnościową i skorzystaj z rabatu na kolację."),
]


def gen_partner_index():
    cards = ""
    for slug, name, desc in PARTNERS:
        cards += f'<a href="/partner-okayka/{slug}/" class="location-card reveal"><div class="location-card-body"><h3>{name}</h3><p>{desc[:80]}...</p><span class="btn btn-outline" style="margin-top:.75rem">Zobacz szczegóły</span></div></a>\n'
    body = page_header(
        bc_html([("Start", "/"), ("Okayka", "/okayka/"), ("Partnerzy", "")]),
        'Partnerzy <span class="text-red">Okayka</span>',
        "Poznaj miejsca, w których wykorzystasz punkty z programu Okayka. Restauracje, sport, wellness i więcej.",
    )
    body += f'<section class="content-section"><div class="container"><div class="grid-3">{cards}</div></div></section>'
    body += CTA
    return (
        make_head("Partnerzy Okayka — Gdzie Wykorzystać Punkty | Okay Taxi", "Lista partnerów programu Okayka — restauracje, hotele, sport, wellness. Zbieraj punkty za przejazdy Okay Taxi.", "/partner-okayka/")
        + breadcrumb_ld([("Start", "/"), ("Okayka", "/okayka/"), ("Partnerzy", "/partner-okayka/")])
        + "</head><body>" + nav_html() + body + FOOTER
    )


def gen_partner_page(slug, name, desc):
    body = page_header(
        bc_html([("Start", "/"), ("Okayka", "/okayka/"), ("Partnerzy", "/partner-okayka/"), (name, "")]),
        f'{name} — Partner <span class="text-red">Okayka</span>',
        f"{name} to partner programu lojalnościowego Okayka. Zbieraj punkty za przejazdy Okay Taxi i korzystaj z rabatów.",
    )
    body += f"""<section class="content-section"><div class="container">
<div class="reveal" style="max-width:800px">
<h2>O partnerze</h2>
<p>{desc}</p>
<p>Aby skorzystać z rabatu, pokaż swoją kartę Okayka lub podaj numer konta Okayka. Rabat jest naliczany automatycznie. Im więcej punktów zbierzesz jeżdżąc z&nbsp;Okay Taxi, tym większe zniżki u&nbsp;partnerów.</p>
<h3>Jak zdobyć punkty?</h3>
<p>Każdy przejazd białoczerwonymi taksówkami Okay Taxi nalicza punkty na Twoje konto Okayka. Nie musisz niczego aktywować — punkty pojawiają się automatycznie.</p>
<div style="display:flex;gap:1rem;margin-top:1.5rem;flex-wrap:wrap">
<a href="/okayka/" class="btn btn-primary">Poznaj program Okayka</a>
<a href="/partner-okayka/" class="btn btn-outline">Wszyscy partnerzy</a>
</div>
</div>
</div></section>"""
    body += CTA
    return (
        make_head(f"{name} — Partner Okayka | Okay Taxi", f"{name} — partner programu Okayka. Zbieraj punkty za przejazdy Okay Taxi i korzystaj z rabatów w {name}.", f"/partner-okayka/{slug}/")
        + breadcrumb_ld([("Start", "/"), ("Okayka", "/okayka/"), ("Partnerzy", "/partner-okayka/"), (name, f"/partner-okayka/{slug}/")])
        + "</head><body>" + nav_html() + body + FOOTER
    )


# ===================================================================
# OTHER PAGES
# ===================================================================
def gen_simple_page(slug, title, desc, h1, lead, content, active=""):
    body = page_header(bc_html([("Start", "/"), (h1.replace('<span class="text-red">', "").replace("</span>", ""), "")]), h1, lead)
    body += f'<section class="content-section"><div class="container"><div class="reveal">{content}</div></div></section>'
    body += CTA
    return (
        make_head(title, desc, f"/{slug}/")
        + breadcrumb_ld([("Start", "/"), (h1.replace('<span class="text-red">', "").replace("</span>", ""), f"/{slug}/")])
        + "</head><body>" + nav_html(active) + body + FOOTER
    )


# ===================================================================
# GENERATE ALL
# ===================================================================
print("=== Generating pages ===")

# Cennik
write_page("cennik/index.html", gen_cennik())

# Aplikacja
write_page("aplikacja/index.html", gen_aplikacja())

# Okayka
write_page("okayka/index.html", gen_okayka())

# Dostepnosc
write_page("dla-niepelnosprawnych/index.html", gen_dostepnosc())

# Firmy
write_page("programy-bezgotowkowe/index.html", gen_firmy())

# Locations
for slug, data in LOCATIONS.items():
    write_page(f"{slug}/index.html", gen_location(slug, data))

# Legal
write_page("regulamin/index.html", gen_legal("regulamin", "Regulamin — Okay Taxi Bielsko-Biała", "Regulamin", REGULAMIN_CONTENT))
write_page("polityka-prywatnosci/index.html", gen_legal("polityka-prywatnosci", "Polityka Prywatności — Okay Taxi", "Polityka prywatności", POLITYKA_CONTENT))
write_page("rodo/index.html", gen_legal("rodo", "RODO — Okay Taxi | Ochrona Danych Osobowych", "RODO", RODO_CONTENT))
write_page("reklamacja/index.html", gen_legal("reklamacja", "Reklamacja — Okay Taxi Bielsko-Biała", "Reklamacja", REKLAMACJA_CONTENT, robots="index, follow"))

# Partners
write_page("partner-okayka/index.html", gen_partner_index())
for slug, name, desc in PARTNERS:
    write_page(f"partner-okayka/{slug}/index.html", gen_partner_page(slug, name, desc))

# Other simple pages
write_page("cennik-2/index.html", gen_simple_page("cennik-2", "Cennik Transferów — Okay Taxi | Trasy Długie", "Cennik transferów lotniskowych i tras długich Okay Taxi.", 'Cennik <span class="text-red">transferów</span>', "Szczegółowe ceny transferów na lotniska i tras międzymiastowych.", """
<p>Oprócz przejazdów miejskich oferujemy transfery na lotniska i trasy międzymiastowe w cenach ustalanych indywidualnie. Skontaktuj się z nami, aby uzyskać dokładną wycenę na Twoją trasę.</p>
<h3>Transfery lotniskowe</h3>
<p>Ceny transferów na lotniska zależą od dnia tygodnia, pory dnia i liczby pasażerów. Zadzwoń pod <a href="tel:+48720535353" style="color:var(--red)">720 535 353</a> po indywidualną wycenę.</p>
<p><a href="/cennik/" class="btn btn-outline mt-md">Zobacz pełny cennik</a></p>
"""))

write_page("program-okayka/index.html", gen_simple_page("program-okayka", "Program Lojalnościowy Okayka — Okay Taxi", "Szczegóły programu lojalnościowego Okayka — jak zbierać punkty i gdzie je wykorzystać.", 'Program <span class="text-red">Okayka</span>', "Szczegółowe informacje o programie lojalnościowym Okay Taxi.", """
<p>Program Okayka to nasz sposób na podziękowanie za lojalność. Za każdy przejazd z Okay Taxi zbierasz punkty, które wymieniasz na rabaty u naszych partnerów w Bielsku-Białej i okolicach.</p>
<p><a href="/okayka/" class="btn btn-primary mt-md">Poznaj partnerów Okayka</a></p>
"""))

write_page("ambasador/index.html", gen_simple_page("ambasador", "Ambasador Okay Taxi — Dołącz do Nas | Bielsko-Biała", "Zostań ambasadorem Okay Taxi. Dołącz do zespołu białoczerwonych taksówek w Bielsku-Białej.", 'Zostań <span class="text-red">ambasadorem</span>', "Dołącz do zespołu Okay Taxi — szukamy kierowców i ambasadorów marki.", """
<h2>Dlaczego warto dołączyć?</h2>
<ul class="content-section">
<li>Elastyczne godziny pracy — sam decydujesz kiedy jeździsz</li>
<li>Atrakcyjne warunki finansowe</li>
<li>Wsparcie techniczne i marketingowe</li>
<li>Dostęp do aplikacji z zamówieniami 24/7</li>
<li>Przynależność do rozpoznawalnej marki</li>
</ul>
<h2>Wymagania</h2>
<ul class="content-section">
<li>Prawo jazdy kat. B minimum 3 lata</li>
<li>Aktualna licencja taxi</li>
<li>Pojazd spełniający standardy korporacji</li>
<li>Zaświadczenie o niekaralności</li>
<li>Badania lekarskie dla kierowców</li>
</ul>
<p>Zainteresowany? Napisz na <a href="mailto:marketing@okaytaxi.pl" style="color:var(--red)">marketing@okaytaxi.pl</a> lub zadzwoń <a href="tel:+48720535353" style="color:var(--red)">720 535 353</a>.</p>
"""))

write_page("reklama-na-tablety/index.html", gen_simple_page("reklama-na-tablety", "Reklama na Tabletach w Taxi — Okay Taxi | Reklama w Taksówkach", "Reklama na tabletach w taksówkach Okay Taxi — dotrzyj do pasażerów. Targetowana reklama w pojazdach.", 'Reklama na <span class="text-red">tabletach</span>', "Dotrzyj do pasażerów Okay Taxi — reklama na tabletach w taksówkach.", """
<h2>Reklama, która dociera</h2>
<p>Tablety w taksówkach Okay Taxi to unikalna przestrzeń reklamowa. Pasażer spędza w taksówce średnio 15-20 minut — to czas, w którym Twoja reklama ma jego pełną uwagę.</p>
<h3>Co oferujemy</h3>
<ul class="content-section">
<li>Reklamy wideo i graficzne na tabletach w pojazdach</li>
<li>Targetowanie po trasach i godzinach</li>
<li>Raporty wyświetleń i zasięgu</li>
<li>Elastyczne pakiety — od tygodnia do roku</li>
</ul>
<p>Zainteresowany? Napisz: <a href="mailto:marketing@okaytaxi.pl" style="color:var(--red)">marketing@okaytaxi.pl</a></p>
"""))

write_page("reklama-na-tabletach/index.html", gen_simple_page("reklama-na-tabletach", "Reklama na Tabletach — Okay Taxi Bielsko-Biała", "Reklama na tabletach w taksówkach Okay Taxi Bielsko-Biała.", 'Reklama na <span class="text-red">tabletach</span>', "Reklama na tabletach w taksówkach Okay Taxi.", '<p>Szczegółowe informacje o reklamie na tabletach znajdziesz na stronie <a href="/reklama-na-tablety/" class="btn btn-primary">Reklama na tabletach</a>.</p>'))

write_page("reklama-na-szybie/index.html", gen_simple_page("reklama-na-szybie", "Reklama na Szybie Taxi — Okay Taxi | Reklama Zewnętrzna", "Reklama na szybach taksówek Okay Taxi — widoczna reklama w ruchu miejskim Bielska-Białej.", 'Reklama na <span class="text-red">szybie</span>', "Reklama zewnętrzna na szybach białoczerwonych taksówek Okay Taxi.", """
<h2>Twoja reklama w ruchu miejskim</h2>
<p>Białoczerwone taksówki Okay Taxi jeżdżą po Bielsku-Białej i okolicach codziennie, 24 godziny na dobę. Reklama na szybach naszych pojazdów to mobilny billboard, który dociera do tysięcy osób dziennie.</p>
<h3>Zalety reklamy na szybie</h3>
<ul class="content-section">
<li>Widoczność w całym regionie Podbeskidzia</li>
<li>Trwała folia z nadrukiem UV</li>
<li>Codziennie tysiące odsłon w ruchu miejskim</li>
<li>Pakiety 1, 3, 6 i 12 miesięcy</li>
</ul>
<p>Zapytaj o ofertę: <a href="mailto:marketing@okaytaxi.pl" style="color:var(--red)">marketing@okaytaxi.pl</a></p>
"""))

write_page("towar/index.html", gen_simple_page("towar", "Sklep Okay Taxi — Gadżety i Odzież | Bielsko-Biała", "Sklep Okay Taxi — bluzy, kurtki, koszulki i gadżety z logo białoczerwonych taksówek.", 'Sklep <span class="text-red">Okay Taxi</span>', "Gadżety i odzież firmowa z logo Okay Taxi. Białoczerwone bluzy, kurtki i akcesoria.", """
<h2>Nasza kolekcja</h2>
<p>Chcesz nosić białoczerwone barwy Okay Taxi? W naszym sklepie znajdziesz bluzy, kurtki, koszulki polo i inne gadżety z logo korporacji.</p>
<div class="grid-3" style="margin-top:var(--space-lg)">
<div class="card"><img src="https://okaytaxi.pl/wp-content/uploads/2021/10/Bluza-meska-1-560x747.jpg" alt="Bluza męska Okay Taxi" loading="lazy" width="560" height="747" style="border-radius:12px;margin-bottom:1rem"><h3>Bluza męska</h3><p>Ciepła bluza z logo Okay Taxi. Idealna na co dzień.</p></div>
<div class="card"><img src="https://okaytaxi.pl/wp-content/uploads/2021/10/Bluza-unisex-1-560x747.jpg" alt="Bluza unisex Okay Taxi" loading="lazy" width="560" height="747" style="border-radius:12px;margin-bottom:1rem"><h3>Bluza unisex</h3><p>Uniwersalny krój, wygodna na każdą okazję.</p></div>
<div class="card"><img src="https://okaytaxi.pl/wp-content/uploads/2021/10/Damska-Koszulka-Polo-Kr.-Rekaw-1-1-560x747.jpg" alt="Koszulka polo damska" loading="lazy" width="560" height="747" style="border-radius:12px;margin-bottom:1rem"><h3>Koszulka polo damska</h3><p>Elegancka koszulka polo z krótkim rękawem.</p></div>
</div>
<p class="mt-lg">Zainteresowany zakupem? Skontaktuj się: <a href="mailto:marketing@okaytaxi.pl" style="color:var(--red)">marketing@okaytaxi.pl</a></p>
"""))

write_page("konkurs-test/index.html", gen_simple_page("konkurs-test", "Konkurs Okay Taxi — Wygraj Darmowe Przejazdy!", "Konkurs Okay Taxi — weź udział i wygraj darmowe przejazdy białoczerwonymi taksówkami.", 'Konkurs <span class="text-red">Okay Taxi</span>', "Weź udział w konkursie i wygraj darmowe przejazdy!", """
<p>Szczegóły aktualnych konkursów ogłaszamy na naszych profilach w mediach społecznościowych. Śledź nas, żeby nie przegapić kolejnej szansy na darmowe przejazdy!</p>
<p>Kontakt w sprawie konkursów: <a href="mailto:marketing@okaytaxi.pl" style="color:var(--red)">marketing@okaytaxi.pl</a></p>
"""))

print("\\n=== ALL DONE ===")
