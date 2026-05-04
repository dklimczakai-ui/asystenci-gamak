"""Replace 3 images on homepage + increase logo size attrs in all HTML files."""
import os, re

BASE = r"C:\Users\klimc\Desktop\Asystenci\okaytaxi"

# =========================================================
# 1. Homepage — replace 3 images
# =========================================================
print("=== 1. Homepage images ===")
idx = os.path.join(BASE, "index.html")
with open(idx, "r", encoding="utf-8") as f:
    html = f.read()

# HERO image — replace the phone mockup with hero taxi photo
html = html.replace(
    '<img src="https://okaytaxi.pl/wp-content/uploads/2024/01/tel-600x1288.png" alt="Aplikacja Okay Taxi na smartfonie — zamów taksówkę w Bielsku-Białej" class="hero-phone" width="300" height="644" loading="eager">',
    '<img src="zdj/ok taxi hero.png" alt="Białoczerwona taksówka Okay Taxi z pasażerką — zamów taxi w Bielsku-Białej" width="600" height="300" loading="eager" style="max-width:520px;border-radius:0;box-shadow:none">'
)

# "Białoczerwone taksówki którym zaufasz" section — replace banner
html = html.replace(
    '<img src="https://okaytaxi.pl/wp-content/uploads/2024/01/Baner-Okay-Taxi-2024-3-1390x782.png" alt="Biało-czerwone taksówki Okay Taxi w Bielsku-Białej" width="1390" height="782" loading="lazy" decoding="async">',
    '<img src="zdj/ok taki.png" alt="Dwie białoczerwone taksówki Okay Taxi Škoda Superb — flota w Bielsku-Białej" width="1200" height="600" loading="lazy" decoding="async">'
)

# "Zamów taxi jednym kliknięciem" section — replace phone mockup with real app screenshot
html = html.replace(
    '<img src="https://okaytaxi.pl/wp-content/uploads/2024/01/tel-1-600x1288.png" alt="Aplikacja Okay Taxi — zamawianie taxi przez smartfon" width="300" height="644" loading="lazy" decoding="async" style="max-width:280px;margin:0 auto;border-radius:24px;box-shadow:var(--shadow-xl)">',
    '<img src="zdj/aplikacja.png" alt="Aplikacja Okay Taxi — ekran zamawiania przejazdu z mapą i ceną 114 zł" width="300" height="600" loading="lazy" decoding="async" style="max-width:280px;margin:0 auto;border-radius:28px;box-shadow:var(--shadow-xl)">'
)

with open(idx, "w", encoding="utf-8") as f:
    f.write(html)
print("  index.html — 3 images replaced")

# =========================================================
# 2. Increase logo size attributes in ALL HTML files
# =========================================================
print("\n=== 2. Logo size increase in all HTML ===")
count = 0
for root, dirs, files in os.walk(BASE):
    for fname in files:
        if not fname.endswith(".html"):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # Header logo: width="44" height="44" -> width="64" height="64"
        content = content.replace(
            'alt="Okay Taxi" width="44" height="44"',
            'alt="Okay Taxi" width="64" height="64"'
        )
        content = content.replace(
            'alt="Okay Taxi logo" width="44" height="44"',
            'alt="Okay Taxi logo" width="64" height="64"'
        )

        if content != original:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            count += 1

print(f"  {count} files — logo attrs updated")

# =========================================================
# 3. Also fix hero-phone CSS class issue (no longer a phone)
# =========================================================
print("\n=== 3. CSS hero-phone fix ===")
css_path = os.path.join(BASE, "css", "style.css")
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

# The hero-phone class had max-width:280px and border-radius:32px
# Now it's a full car image, so we remove the phone-specific constraints
css = css.replace(
    """.hero-phone {
  max-width: 280px !important;
  border-radius: 32px !important;
  box-shadow: var(--shadow-xl);
}""",
    """.hero-phone {
  max-width: 520px !important;
  border-radius: 16px !important;
  box-shadow: none;
}"""
)

with open(css_path, "w", encoding="utf-8") as f:
    f.write(css)
print("  style.css — hero-phone class updated")

print("\n=== DONE ===")
