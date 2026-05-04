#!/usr/bin/env python3
"""
Okay Taxi — Comprehensive Upgrade
CEO orchestration: @cmo (SEO/LEO/GEO content) + @cto (technical)

1. Add App Store + Google Play links
2. Add Facebook + Instagram socials
3. Add 10+ new city pages with SEO/LEO/GEO content
4. Rewrite homepage meta + descriptions for SEO/LEO/GEO
5. Update footer, header, sitemap
"""
import os
import re

BASE = r"C:\Users\klimc\Desktop\Asystenci\okaytaxi"

LOGO = "https://okaytaxi.pl/wp-content/uploads/2021/07/okay_duze.png"
BANNER = "https://okaytaxi.pl/wp-content/uploads/2024/01/Baner-Okay-Taxi-2024-3-1390x782.png"
TEL_IMG = "https://okaytaxi.pl/wp-content/uploads/2024/01/tel-600x1288.png"

APP_APPLE = "https://apps.apple.com/pl/app/bia%C5%82o-czerwone-okay-taxi/id1398190430"
APP_GOOGLE = "https://play.google.com/store/apps/details?id=com.tiskel.tma.okaytaxi&hl=pl"
FB_URL = "https://www.facebook.com/okaytaxibielsko"
IG_URL = "https://www.instagram.com/okaytaxi_official/"

PHONE_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M6.62 10.79a15.05 15.05 0 0 0 6.59 6.59l2.2-2.2a1 1 0 0 1 1.01-.24c1.12.37 2.33.57 3.58.57a1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.46.57 3.58a1 1 0 0 1-.24 1.01l-2.2 2.2z"/></svg>'

# =============================================
# SOCIAL ICONS SVG
# =============================================
FB_SVG = '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg>'
IG_SVG = '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><rect x="2" y="2" width="20" height="20" rx="5" ry="5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="17.5" cy="6.5" r="1.5"/></svg>'
APPLE_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg>'
GPLAY_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M3 20.5V3.5C3 2.91 3.34 2.39 3.84 2.15L13.69 12L3.84 21.85C3.34 21.61 3 21.09 3 20.5ZM16.81 15.12L6.05 21.34L14.54 12.85L16.81 15.12ZM20.16 10.81C20.5 11.08 20.75 11.5 20.75 12C20.75 12.5 20.5 12.92 20.16 13.19L17.89 14.5L15.39 12L17.89 9.5L20.16 10.81ZM6.05 2.66L16.81 8.88L14.54 11.15L6.05 2.66Z"/></svg>'


# =============================================
# NEW CITIES DATA (@cmo SEO/LEO/GEO content)
# =============================================
NEW_CITIES = {
    "okay-taxi-zywiec": {
        "city": "Żywiec",
        "title": "Taxi Żywiec — Okay Taxi | Transfer i Przejazdy 720 535 353",
        "desc": "Zamów taxi w Żywcu. Okay Taxi — szybki dojazd, transfery na lotniska, przejazdy do Bielska-Białej i okolic. Dostępni 24/7. Zadzwoń: 720 535 353.",
        "h1": "Taxi Żywiec — zamów białoczerwone taxi 24/7",
        "lead": "Okay Taxi w Żywcu. Komfortowe przejazdy, transfery lotniskowe i kursy do Bielska-Białej. Płatność kartą, BLIK, gotówką.",
        "content": """<p>Żywiec, stolica Żywiecczyzny i&nbsp;jedno z&nbsp;najważniejszych miast Beskidu Żywieckiego, oddalony jest od Bielska-Białej o&nbsp;ok. 35&nbsp;km. Okay Taxi zapewnia regularne przejazdy na trasie Żywiec–Bielsko-Biała oraz transfery na lotniska Katowice-Pyrzowice i&nbsp;Kraków-Balice.</p>
<p>Dowozimy pasażerów do Dworca PKP Żywiec, Starego Browaru, Parku Miejskiego, szpitala i&nbsp;firm w&nbsp;strefie przemysłowej. Obsługujemy też turystów jadących w&nbsp;Beskid Żywiecki — Pilsko, Babia Góra, Korbielów.</p>
<h3>Popularne trasy z&nbsp;Żywca</h3>
<ul class="content-section">
<li>Żywiec → Bielsko-Biała centrum (~35&nbsp;km, ~40&nbsp;min)</li>
<li>Żywiec → Lotnisko Katowice-Pyrzowice (~140&nbsp;km, ~100&nbsp;min)</li>
<li>Żywiec → Lotnisko Kraków-Balice (~110&nbsp;km, ~80&nbsp;min)</li>
<li>Żywiec → Korbielów / Pilsko (~25&nbsp;km, ~30&nbsp;min)</li>
<li>Żywiec → Wisła (~45&nbsp;km, ~50&nbsp;min)</li>
</ul>
<h3>Dlaczego Okay Taxi w&nbsp;Żywcu?</h3>
<p>Jesteśmy jedną z&nbsp;niewielu korporacji obsługujących regularnie trasę Żywiec–Bielsko. Nasi kierowcy znają lokalne drogi, objazdy i&nbsp;najszybsze trasy przez Łodygowice i&nbsp;Buczkowice. Samochody wyposażone w&nbsp;klimatyzację, USB i&nbsp;terminal płatniczy.</p>""",
    },
    "okay-taxi-andrychow": {
        "city": "Andrychów",
        "title": "Taxi Andrychów — Okay Taxi | Przejazdy i Transfery 720 535 353",
        "desc": "Taxi w Andrychowie — Okay Taxi dowiezie Cię do Bielska-Białej, na lotnisko i w Beskidy. Zamów: 720 535 353. Dostępni 24/7.",
        "h1": "Taxi Andrychów — Okay Taxi dowiezie Cię wszędzie",
        "lead": "Zamów taxi w Andrychowie. Przejazdy do Bielska, Wadowic, na lotniska. Klimatyzacja, USB, płatność kartą i&nbsp;BLIK.",
        "content": """<p>Andrychów leży na trasie Bielsko-Biała–Wadowice, ok. 20&nbsp;km od centrum Bielska. Okay Taxi obsługuje Andrychów codziennie — dowozimy do pracy, na dworzec, do galerii i&nbsp;na lotniska.</p>
<p>Obsługujemy też pobliskie Inwałd (Park Miniatur, Dinolandia) — idealne taxi dla rodzin z&nbsp;dziećmi. Foteliki dziecięce na życzenie, bezpłatnie.</p>
<h3>Popularne trasy z&nbsp;Andrychowa</h3>
<ul class="content-section">
<li>Andrychów → Bielsko-Biała (~20&nbsp;km, ~25&nbsp;min)</li>
<li>Andrychów → Wadowice (~15&nbsp;km, ~20&nbsp;min)</li>
<li>Andrychów → Inwałd (~5&nbsp;km, ~8&nbsp;min)</li>
<li>Andrychów → Lotnisko Kraków-Balice (~80&nbsp;km, ~65&nbsp;min)</li>
<li>Andrychów → Kęty (~10&nbsp;km, ~15&nbsp;min)</li>
</ul>""",
    },
    "okay-taxi-kety": {
        "city": "Kęty",
        "title": "Taxi Kęty — Okay Taxi | Zamów Przejazd 720 535 353",
        "desc": "Taxi w Kętach. Okay Taxi — przejazdy do Bielska-Białej, Oświęcimia, na lotniska. Dostępni 24/7. Tel. 720 535 353.",
        "h1": "Taxi Kęty — szybki dojazd, uczciwe ceny",
        "lead": "Okay Taxi obsługuje Kęty i&nbsp;okolice. Dojazd w&nbsp;kilka minut, transfery lotniskowe, płatność kartą.",
        "content": """<p>Kęty to miasto powiatowe w&nbsp;dolinie Soły, ok. 25&nbsp;km od Bielska-Białej. Okay Taxi zapewnia komfortowy transport z&nbsp;Kęt do Bielska, Oświęcimia, Andrychowa i&nbsp;na lotniska.</p>
<h3>Popularne trasy</h3>
<ul class="content-section">
<li>Kęty → Bielsko-Biała (~25&nbsp;km, ~30&nbsp;min)</li>
<li>Kęty → Oświęcim (~15&nbsp;km, ~20&nbsp;min)</li>
<li>Kęty → Andrychów (~10&nbsp;km, ~15&nbsp;min)</li>
<li>Kęty → Lotnisko Katowice-Pyrzowice (~90&nbsp;km, ~70&nbsp;min)</li>
</ul>""",
    },
    "okay-taxi-wadowice": {
        "city": "Wadowice",
        "title": "Taxi Wadowice — Okay Taxi | Zamów Transfer 720 535 353",
        "desc": "Taxi w Wadowicach — miasto papieża Jana Pawła II. Okay Taxi dowiezie turystów, mieszkańców i na lotniska. 720 535 353.",
        "h1": "Taxi Wadowice — przejazdy i&nbsp;transfery turystyczne",
        "lead": "Zamów taxi w&nbsp;Wadowicach. Przejazdy turystyczne, transfery na lotniska, dojazd do Bielska-Białej.",
        "content": """<p>Wadowice — miasto rodzinne Jana Pawła II — przyciąga turystów z&nbsp;całego świata. Okay Taxi oferuje transfery z&nbsp;lotnisk i&nbsp;dworców bezpośrednio do Wadowic oraz przejazdy po mieście i&nbsp;okolicach.</p>
<p>Dowozimy turystów do Bazyliki, Muzeum Dom Rodzinny Ojca Świętego i&nbsp;słynnej cukierni z&nbsp;kremówkami. Realizujemy też transfery do Kalwarii Zebrzydowskiej (15&nbsp;km) i&nbsp;Sanktuarium w&nbsp;Kalwarii.</p>
<h3>Popularne trasy</h3>
<ul class="content-section">
<li>Wadowice → Bielsko-Biała (~35&nbsp;km, ~35&nbsp;min)</li>
<li>Wadowice → Kalwaria Zebrzydowska (~15&nbsp;km, ~20&nbsp;min)</li>
<li>Wadowice → Kraków centrum (~50&nbsp;km, ~50&nbsp;min)</li>
<li>Wadowice → Lotnisko Kraków-Balice (~55&nbsp;km, ~50&nbsp;min)</li>
</ul>""",
    },
    "okay-taxi-skoczow": {
        "city": "Skoczów",
        "title": "Taxi Skoczów — Okay Taxi | Zamów 720 535 353",
        "desc": "Taxi w Skoczowie — Okay Taxi. Przejazdy do Cieszyna, Bielska-Białej, na lotniska. 24/7. Tel. 720 535 353.",
        "h1": "Taxi Skoczów — miasto Gustawa Morcinka",
        "lead": "Okay Taxi w&nbsp;Skoczowie. Szybkie przejazdy do Cieszyna, Ustronia, Bielska-Białej i&nbsp;na lotniska.",
        "content": """<p>Skoczów, urokliwe miasto na Śląsku Cieszyńskim, leży ok. 25&nbsp;km od Bielska-Białej. Okay Taxi obsługuje Skoczów i&nbsp;okolice — Pogórze, Pierściec, Harbutowice.</p>
<h3>Popularne trasy</h3>
<ul class="content-section">
<li>Skoczów → Bielsko-Biała (~25&nbsp;km, ~30&nbsp;min)</li>
<li>Skoczów → Cieszyn (~10&nbsp;km, ~15&nbsp;min)</li>
<li>Skoczów → Ustroń (~8&nbsp;km, ~12&nbsp;min)</li>
<li>Skoczów → Wisła (~20&nbsp;km, ~25&nbsp;min)</li>
</ul>""",
    },
    "okay-taxi-ustron": {
        "city": "Ustroń",
        "title": "Taxi Ustroń — Okay Taxi | Transfer do Uzdrowiska 720 535 353",
        "desc": "Taxi w Ustroniu — transfery do uzdrowiska, hoteli SPA, na Czantorię. Okay Taxi 24/7. Zadzwoń: 720 535 353.",
        "h1": "Taxi Ustroń — uzdrowisko, SPA, Czantoria",
        "lead": "Okay Taxi w&nbsp;Ustroniu. Transfery do sanatoriów, hoteli SPA, na kolejkę na Czantorię i&nbsp;z&nbsp;powrotem.",
        "content": """<p>Ustroń to popularne uzdrowisko w&nbsp;Beskidzie Śląskim, znane z&nbsp;sanatoriów, hoteli SPA i&nbsp;kolejki gondolowej na Czantorię. Okay Taxi dowozi kuracjuszy, turystów i&nbsp;uczestników konferencji.</p>
<h3>Popularne trasy</h3>
<ul class="content-section">
<li>Ustroń → Wisła (~10&nbsp;km, ~15&nbsp;min)</li>
<li>Ustroń → Cieszyn (~15&nbsp;km, ~20&nbsp;min)</li>
<li>Ustroń → Bielsko-Biała (~30&nbsp;km, ~35&nbsp;min)</li>
<li>Ustroń → Lotnisko Katowice-Pyrzowice (~140&nbsp;km, ~100&nbsp;min)</li>
</ul>""",
    },
    "okay-taxi-wilkowice": {
        "city": "Wilkowice",
        "title": "Taxi Wilkowice — Okay Taxi | Zamów 720 535 353",
        "desc": "Taxi w Wilkowicach — Okay Taxi. Dojazd do Bielska, Szczyrku, na Szyndzielnię. 24/7.",
        "h1": "Taxi Wilkowice — brama do Szczyrku",
        "lead": "Okay Taxi w&nbsp;Wilkowicach i&nbsp;Bystrej. Dojazd do Bielska-Białej, na Szyndzielnię, do Szczyrku.",
        "content": """<p>Wilkowice i&nbsp;sąsiednia Bystra leżą u&nbsp;podnóża Szyndzielni, na trasie Bielsko-Biała–Szczyrk. Okay Taxi obsługuje te miejscowości codziennie.</p>
<h3>Popularne trasy</h3>
<ul class="content-section">
<li>Wilkowice → Bielsko-Biała (~10&nbsp;km, ~15&nbsp;min)</li>
<li>Wilkowice → Szczyrk (~10&nbsp;km, ~15&nbsp;min)</li>
<li>Wilkowice → Szyndzielnia (kolej) (~5&nbsp;km, ~10&nbsp;min)</li>
</ul>""",
    },
    "okay-taxi-milowka": {
        "city": "Milówka",
        "title": "Taxi Milówka — Okay Taxi | Przejazdy Beskid Żywiecki 720 535 353",
        "desc": "Taxi w Milówce. Okay Taxi — dojazd do stoków, Korbielowa, Rajczy. Transfery z lotnisk. 720 535 353.",
        "h1": "Taxi Milówka — Beskid Żywiecki na wyciągnięcie ręki",
        "lead": "Okay Taxi w&nbsp;Milówce. Przejazdy do Korbielowa, Rajczy, Żywca i&nbsp;na lotniska.",
        "content": """<p>Milówka to gmina w&nbsp;sercu Beskidu Żywieckiego, blisko Korbielowa i&nbsp;tras narciarskich. Okay Taxi obsługuje Milówkę, Kamesznicę, Rajczę i&nbsp;Korbielów.</p>
<h3>Popularne trasy</h3>
<ul class="content-section">
<li>Milówka → Żywiec (~15&nbsp;km, ~20&nbsp;min)</li>
<li>Milówka → Korbielów (~10&nbsp;km, ~15&nbsp;min)</li>
<li>Milówka → Bielsko-Biała (~50&nbsp;km, ~55&nbsp;min)</li>
<li>Milówka → Rajcza (~5&nbsp;km, ~8&nbsp;min)</li>
</ul>""",
    },
    "okay-taxi-brzesce": {
        "city": "Brzeźce",
        "title": "Taxi Brzeźce / Buczkowice — Okay Taxi | 720 535 353",
        "desc": "Taxi Brzeźce i Buczkowice koło Szczyrku. Okay Taxi — szybki dojazd do Bielska-Białej i na stoki. 720 535 353.",
        "h1": "Taxi Brzeźce i&nbsp;Buczkowice",
        "lead": "Okay Taxi w&nbsp;Brzeźcach i&nbsp;Buczkowicach. Dojazd do Szczyrku, Bielska-Białej i&nbsp;dalej.",
        "content": """<p>Brzeźce i&nbsp;Buczkowice to gminy między Bielskiem-Białą a&nbsp;Szczyrkiem. Okay Taxi zapewnia szybki transport — dojazd do centrum Bielska w&nbsp;10 minut, na stoki Szczyrku w&nbsp;15.</p>
<h3>Popularne trasy</h3>
<ul class="content-section">
<li>Brzeźce → Bielsko-Biała (~8&nbsp;km, ~12&nbsp;min)</li>
<li>Brzeźce → Szczyrk (~12&nbsp;km, ~18&nbsp;min)</li>
<li>Buczkowice → Żywiec (~25&nbsp;km, ~30&nbsp;min)</li>
</ul>""",
    },
    "okay-taxi-miedzybrodzie": {
        "city": "Międzybrodzie Żywieckie",
        "title": "Taxi Międzybrodzie Żywieckie — Okay Taxi | 720 535 353",
        "desc": "Taxi Międzybrodzie Żywieckie — Okay Taxi. Dojazd nad Jezioro Żywieckie, Górę Żar, do Żywca. 720 535 353.",
        "h1": "Taxi Międzybrodzie Żywieckie — Jezioro Żywieckie i&nbsp;Góra Żar",
        "lead": "Okay Taxi w&nbsp;Międzybrodziu. Transfery nad Jezioro Żywieckie, na Górę Żar, do Żywca i&nbsp;Bielska.",
        "content": """<p>Międzybrodzie Żywieckie to popularny ośrodek turystyczny nad Jeziorem Żywieckim, znany z&nbsp;Góry Żar i&nbsp;paralotni. Okay Taxi dowozi turystów z&nbsp;Bielska, Żywca i&nbsp;lotnisk.</p>
<h3>Popularne trasy</h3>
<ul class="content-section">
<li>Międzybrodzie → Żywiec (~15&nbsp;km, ~20&nbsp;min)</li>
<li>Międzybrodzie → Bielsko-Biała (~25&nbsp;km, ~30&nbsp;min)</li>
<li>Międzybrodzie → Góra Żar (start paralotni) (~3&nbsp;km, ~8&nbsp;min)</li>
</ul>""",
    },
}


def make_head(title, desc, canonical, og_img=None):
    if og_img is None:
        og_img = BANNER
    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="https://okaytaxi.pl/{canonical}/">
<meta name="geo.region" content="PL-SL"><meta name="geo.placename" content="Bielsko-Biała">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://okaytaxi.pl/{canonical}/">
<meta property="og:image" content="{og_img}">
<meta property="og:locale" content="pl_PL"><meta property="og:site_name" content="Okay Taxi">
<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#c72227">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../css/style.css">
<link rel="icon" type="image/png" href="{LOGO}">
<script type="application/ld+json">{{"@context":"https://schema.org","@graph":[
{{"@type":"TaxiService","name":"Okay Taxi {data['city']}","telephone":"+48720535353","areaServed":{{"@type":"City","name":"{data['city']}"}},
"url":"https://okaytaxi.pl/{slug}/"}},
{{"@type":"BreadcrumbList","itemListElement":[
{{"@type":"ListItem","position":1,"name":"Start","item":"https://okaytaxi.pl/"}},
{{"@type":"ListItem","position":2,"name":"Taxi {data['city']}","item":"https://okaytaxi.pl/{slug}/"}}
]}},
{{"@type":"FAQPage","mainEntity":[
{{"@type":"Question","name":"Jak zamówić taxi w {data['city']}?","acceptedAnswer":{{"@type":"Answer","text":"Zadzwoń pod 720 535 353 lub pobierz aplikację Okay Taxi. Taksówka dojedzie w kilka minut."}}}},
{{"@type":"Question","name":"Ile kosztuje taxi z {data['city']} do Bielska-Białej?","acceptedAnswer":{{"@type":"Answer","text":"Cena zależy od trasy i pory dnia. Zadzwoń po dokładną wycenę: 720 535 353. Cennik dostępny na okaytaxi.pl/cennik/"}}}}
]}}
]}}</script>
</head>"""


def nav_html():
    return f"""<header class="header"><div class="container header-inner">
<a href="../index.html" class="logo"><img src="{LOGO}" alt="Okay Taxi" width="44" height="44"></a>
<nav class="nav-desktop">
<a href="../index.html">Start</a><a href="../o-nas/index.html">O nas</a><a href="../flota/index.html">Flota</a><a href="../cennik/index.html">Cennik</a><a href="../aplikacja/index.html">Aplikacja</a><a href="../okayka/index.html">Okayka</a><a href="../dla-niepelnosprawnych/index.html">Dostępność</a>
<a href="tel:+48720535353" class="nav-cta">{PHONE_SVG}720 535 353</a>
</nav>
<button class="nav-toggle" aria-label="Menu"><span></span><span></span><span></span></button>
</div><nav class="nav-mobile">
<a href="../index.html">Start</a><a href="../o-nas/index.html">O nas</a><a href="../flota/index.html">Flota</a><a href="../cennik/index.html">Cennik</a><a href="../aplikacja/index.html">Aplikacja</a><a href="../okayka/index.html">Okayka</a><a href="../dla-niepelnosprawnych/index.html">Dostępność</a>
<a href="tel:+48720535353" class="nav-cta">Zadzwoń: 720 535 353</a>
</nav></header>"""


def footer_html():
    return f"""<footer class="footer"><div class="container">
<div class="footer-grid">
<div class="footer-brand"><img src="{LOGO}" alt="Okay Taxi" width="140" height="140" loading="lazy">
<p>Korporacja białoczerwonych taksówek w&nbsp;Bielsku-Białej &mdash; 24/7.</p>
<div style="display:flex;gap:1rem;margin-top:1rem">
<a href="{FB_URL}" target="_blank" rel="noopener" aria-label="Facebook" style="color:rgba(255,255,255,0.7)">{FB_SVG}</a>
<a href="{IG_URL}" target="_blank" rel="noopener" aria-label="Instagram" style="color:rgba(255,255,255,0.7)">{IG_SVG}</a>
</div>
<div style="display:flex;gap:0.75rem;margin-top:1rem">
<a href="{APP_APPLE}" target="_blank" rel="noopener" class="btn btn-outline" style="padding:0.4rem 0.8rem;font-size:0.75rem;border-color:rgba(255,255,255,0.3);color:rgba(255,255,255,0.7)">{APPLE_SVG} App Store</a>
<a href="{APP_GOOGLE}" target="_blank" rel="noopener" class="btn btn-outline" style="padding:0.4rem 0.8rem;font-size:0.75rem;border-color:rgba(255,255,255,0.3);color:rgba(255,255,255,0.7)">{GPLAY_SVG} Google Play</a>
</div>
</div>
<div><h4>Usługi</h4><div class="footer-links"><a href="../cennik/index.html">Cennik</a><a href="../flota/index.html">Flota</a><a href="../aplikacja/index.html">Aplikacja</a><a href="../okayka/index.html">Okayka</a><a href="../dla-niepelnosprawnych/index.html">Dostępność</a><a href="../programy-bezgotowkowe/index.html">Dla firm</a></div></div>
<div><h4>Miasta</h4><div class="footer-links"><a href="../okay-taxi-czechowice-dziedzice/index.html">Czechowice-Dziedzice</a><a href="../okay-taxi-kozy/index.html">Kozy</a><a href="../okay-taxi-szczyrk/index.html">Szczyrk</a><a href="../okay-taxi-cieszyn/index.html">Cieszyn</a><a href="../okay-taxi-zywiec/index.html">Żywiec</a><a href="../okay-taxi-wadowice/index.html">Wadowice</a><a href="../okay-taxi-ustron/index.html">Ustroń</a><a href="../okay-taxi-wisla/index.html">Wisła</a></div></div>
<div><h4>Kontakt</h4><div class="footer-contact"><a href="tel:+48720535353">+48 720 535 353</a><a href="mailto:marketing@okaytaxi.pl">marketing@okaytaxi.pl</a></div></div>
</div>
<div class="footer-bottom"><p>&copy; 2026 Okay Taxi. Wszelkie prawa zastrzeżone.</p><div class="footer-legal"><a href="../regulamin/index.html">Regulamin</a><a href="../polityka-prywatnosci/index.html">Polityka prywatności</a><a href="../rodo/index.html">RODO</a></div></div>
</div></footer>
<div class="floating-cta"><a href="tel:+48720535353" aria-label="Zadzwoń">{PHONE_SVG}</a></div>
<script src="../js/script.js"></script>
</body></html>"""


def gen_city_page(slug, data):
    head = make_head(data["title"], data["desc"], slug, BANNER)
    return f"""{head}
<body>
{nav_html()}

<section class="page-header"><div class="container">
<nav class="breadcrumbs" style="padding:0 0 1rem"><a href="../index.html">Start</a><span>/</span><strong>Taxi {data['city']}</strong></nav>
<h1>{data['h1']}</h1>
<p class="lead">{data['lead']}</p>
</div></section>

<section class="content-section"><div class="container">
<div class="two-col">
<div class="reveal">
<span class="section-label">Okay Taxi {data['city']}</span>
<h2>Zamów taxi w&nbsp;mieście {data['city']}</h2>
{data['content']}
<div style="display:flex;gap:1rem;flex-wrap:wrap;margin-top:1.5rem">
<a href="tel:+48720535353" class="btn btn-primary">Zadzwoń: 720 535 353</a>
<a href="{APP_APPLE}" target="_blank" rel="noopener" class="btn btn-outline">{APPLE_SVG} App Store</a>
<a href="{APP_GOOGLE}" target="_blank" rel="noopener" class="btn btn-outline">{GPLAY_SVG} Google Play</a>
</div>
</div>
<div class="content-img reveal"><img src="{BANNER}" alt="Okay Taxi {data['city']}" width="1390" height="782" loading="lazy" decoding="async"></div>
</div>
</div></section>

<section class="section-alt"><div class="container">
<div class="section-header center reveal"><span class="section-label">FAQ</span><h2>Pytania o&nbsp;taxi w&nbsp;mieście {data['city']}</h2></div>
<div class="faq-list">
<details class="faq-item reveal"><summary>Jak zamówić taxi w&nbsp;{data['city']}?</summary><div class="faq-answer"><p>Zadzwoń pod <strong>720 535 353</strong> lub pobierz aplikację Okay Taxi (<a href="{APP_APPLE}" style="color:var(--red)">App Store</a> / <a href="{APP_GOOGLE}" style="color:var(--red)">Google Play</a>). Taksówka dojedzie w&nbsp;kilka minut. Działamy 24/7.</p></div></details>
<details class="faq-item reveal"><summary>Ile kosztuje taxi z&nbsp;{data['city']} do Bielska-Białej?</summary><div class="faq-answer"><p>Cena zależy od trasy i&nbsp;pory dnia. Sprawdź <a href="../cennik/index.html" style="color:var(--red)">cennik</a> lub zadzwoń po wycenę: <a href="tel:+48720535353" style="color:var(--red)">720 535 353</a>.</p></div></details>
<details class="faq-item reveal"><summary>Czy Okay Taxi oferuje transfery na lotnisko z&nbsp;{data['city']}?</summary><div class="faq-answer"><p>Tak — realizujemy transfery na lotniska Katowice-Pyrzowice, Kraków-Balice i&nbsp;Wiedeń-Schwechat. Cena ustalana indywidualnie, monitorujemy opóźnienia lotów.</p></div></details>
<details class="faq-item reveal"><summary>Jakie formy płatności akceptujecie?</summary><div class="faq-answer"><p>Gotówka, karta (Visa/Mastercard), BLIK, płatność w&nbsp;aplikacji. Firmy mogą korzystać z&nbsp;<a href="../programy-bezgotowkowe/index.html" style="color:var(--red)">programów bezgotówkowych</a>.</p></div></details>
</div>
</div></section>

<section><div class="container"><div class="cta-banner reveal">
<h2>Zamów taxi w&nbsp;{data['city']} teraz</h2>
<p>Białoczerwone taksówki Okay Taxi czekają. Zadzwoń lub pobierz aplikację.</p>
<span class="phone-big"><a href="tel:+48720535353">720 535 353</a></span>
<div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap">
<a href="{APP_APPLE}" target="_blank" rel="noopener" class="btn btn-white">{APPLE_SVG} App Store</a>
<a href="{APP_GOOGLE}" target="_blank" rel="noopener" class="btn btn-white">{GPLAY_SVG} Google Play</a>
</div>
</div></div></section>

{footer_html()}"""


# =============================================
# STEP 1: Generate new city pages
# =============================================
print("=== Generating new city pages ===")
for slug, data in NEW_CITIES.items():
    path = os.path.join(BASE, slug, "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(gen_city_page(slug, data))
    print(f"  Created: {slug}/index.html")


# =============================================
# STEP 2: Add socials + app links to ALL existing pages
# =============================================
print("\n=== Adding socials + app links to existing pages ===")

# Social links HTML for footer
SOCIAL_BLOCK = f"""<div style="display:flex;gap:1rem;margin-top:1rem">
<a href="{FB_URL}" target="_blank" rel="noopener" aria-label="Facebook" style="color:rgba(255,255,255,0.7)">{FB_SVG}</a>
<a href="{IG_URL}" target="_blank" rel="noopener" aria-label="Instagram" style="color:rgba(255,255,255,0.7)">{IG_SVG}</a>
</div>
<div style="display:flex;gap:0.75rem;margin-top:1rem">
<a href="{APP_APPLE}" target="_blank" rel="noopener" class="btn btn-outline" style="padding:0.4rem 0.8rem;font-size:0.75rem;border-color:rgba(255,255,255,0.3);color:rgba(255,255,255,0.7)">{APPLE_SVG} App Store</a>
<a href="{APP_GOOGLE}" target="_blank" rel="noopener" class="btn btn-outline" style="padding:0.4rem 0.8rem;font-size:0.75rem;border-color:rgba(255,255,255,0.3);color:rgba(255,255,255,0.7)">{GPLAY_SVG} Google Play</a>
</div>"""

count = 0
for root, dirs, files in os.walk(BASE):
    for fname in files:
        if not fname.endswith(".html"):
            continue
        fpath = os.path.join(root, fname)
        # Skip new city pages (already have socials)
        rel = os.path.relpath(fpath, BASE)
        if any(rel.startswith(s) for s in NEW_CITIES.keys()):
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # Add social block after footer-brand paragraph (if not already present)
        if FB_URL not in content and "footer-brand" in content:
            # Find the closing </p> after footer-brand
            pattern = r'(class="footer-brand".*?</p>)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                content = content[:match.end()] + "\n" + SOCIAL_BLOCK + "\n" + content[match.end():]

        # Add app links to "Pobierz aplikację" buttons
        if APP_APPLE not in content:
            # Replace generic "Pobierz aplikację" link with app store links
            content = content.replace(
                'href="aplikacja/index.html" class="btn btn-outline btn-lg">Pobierz aplikację</a>',
                f'href="{APP_APPLE}" target="_blank" rel="noopener" class="btn btn-outline btn-lg">{APPLE_SVG} App Store</a>\n<a href="{APP_GOOGLE}" target="_blank" rel="noopener" class="btn btn-outline btn-lg">{GPLAY_SVG} Google Play</a>'
            )
            content = content.replace(
                'href="../aplikacja/index.html" class="btn btn-outline btn-lg">Pobierz aplikację</a>',
                f'href="{APP_APPLE}" target="_blank" rel="noopener" class="btn btn-outline btn-lg">{APPLE_SVG} App Store</a>\n<a href="{APP_GOOGLE}" target="_blank" rel="noopener" class="btn btn-outline btn-lg">{GPLAY_SVG} Google Play</a>'
            )

        if content != original:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            count += 1
            print(f"  Updated: {rel}")

print(f"\n  {count} existing files updated")


# =============================================
# STEP 3: Update sitemap with new cities
# =============================================
print("\n=== Updating sitemap ===")
sitemap_additions = ""
for slug in NEW_CITIES:
    sitemap_additions += f'  <url><loc>https://okaytaxi.pl/{slug}/</loc><priority>0.8</priority><changefreq>monthly</changefreq></url>\n'

sitemap_path = os.path.join(BASE, "sitemap.xml")
with open(sitemap_path, "r", encoding="utf-8") as f:
    sitemap = f.read()

sitemap = sitemap.replace("</urlset>", f"  <!-- New cities -->\n{sitemap_additions}</urlset>")
with open(sitemap_path, "w", encoding="utf-8") as f:
    f.write(sitemap)
print("  sitemap.xml updated")


# =============================================
# STEP 4: Update llms.txt with new cities
# =============================================
print("\n=== Updating llms.txt ===")
llms_path = os.path.join(BASE, "llms.txt")
with open(llms_path, "r", encoding="utf-8") as f:
    llms = f.read()

old_cities = "Bielsko-Biała, Czechowice-Dziedzice, Kozy, Szczyrk, Jasienica, Cieszyn, Oświęcim, Wisła"
new_cities_str = "Bielsko-Biała, Czechowice-Dziedzice, Kozy, Szczyrk, Jasienica, Cieszyn, Oświęcim, Wisła, Żywiec, Andrychów, Kęty, Wadowice, Skoczów, Ustroń, Wilkowice, Milówka, Brzeźce, Międzybrodzie Żywieckie"
llms = llms.replace(old_cities, new_cities_str)

# Add app links
if "App Store" not in llms:
    llms += f"""
## Aplikacja mobilna

- App Store (iOS): {APP_APPLE}
- Google Play (Android): {APP_GOOGLE}

## Social media

- Facebook: {FB_URL}
- Instagram: {IG_URL}
"""

with open(llms_path, "w", encoding="utf-8") as f:
    f.write(llms)
print("  llms.txt updated")


print("\n=== ALL DONE ===")
print(f"  New city pages: {len(NEW_CITIES)}")
print(f"  Existing pages updated: {count}")
print(f"  Total city pages: 7 + {len(NEW_CITIES)} = {7 + len(NEW_CITIES)}")
