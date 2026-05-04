"""Fix all internal links to work with file:/// protocol and add partner logos."""
import os
import re

BASE = r"C:\Users\klimc\Desktop\Asystenci\okaytaxi"

# Partner logos with their image URLs from wp-content/uploads
PARTNER_LOGOS_HTML = """
<!-- Partnerzy Okayka — loga w stylu gamak.eu -->
<section class="section-alt" id="partnerzy">
<div class="container">
<div class="section-header center reveal">
<span class="section-label">Partnerzy Okayka</span>
<h2>Zaufali nam</h2>
<p class="section-desc">Zbieraj punkty za przejazdy Okay Taxi i&nbsp;korzystaj z&nbsp;rabatów u&nbsp;naszych partnerów.</p>
</div>
<div class="logos-grid reveal">
<a href="{pfx}partner-okayka/barimed/index.html" title="Barimed"><img src="https://okaytaxi.pl/wp-content/uploads/2021/08/Barimed_podstawowy@2x-300x300.png" alt="Barimed — partner Okayka" width="120" height="120" loading="lazy" decoding="async"></a>
<a href="{pfx}partner-okayka/eco-horizon/index.html" title="Eco Horizon"><img src="https://okaytaxi.pl/wp-content/uploads/2021/08/Eco-horizon-300x300.jpg" alt="Eco Horizon — partner Okayka" width="120" height="120" loading="lazy" decoding="async"></a>
<a href="{pfx}partner-okayka/ecusoft/index.html" title="EcuSoft"><img src="https://okaytaxi.pl/wp-content/uploads/2021/09/ecusoft_logoR_2-300x300.png" alt="EcuSoft — partner Okayka" width="120" height="120" loading="lazy" decoding="async"></a>
<a href="{pfx}partner-okayka/2be-club/index.html" title="2BE Club"><img src="https://okaytaxi.pl/wp-content/uploads/2021/10/2be-300x300.jpg" alt="2BE Club — partner Okayka" width="120" height="120" loading="lazy" decoding="async"></a>
<a href="{pfx}partner-okayka/sports-arena/index.html" title="Sports Arena"><img src="https://okaytaxi.pl/wp-content/uploads/2021/08/215338898_375022654331889_1463690656319699277_n-300x300.jpg" alt="Sports Arena — partner Okayka" width="120" height="120" loading="lazy" decoding="async"></a>
<a href="{pfx}partner-okayka/al-capone/index.html" title="Al Capone"><img src="https://okaytaxi.pl/wp-content/uploads/2021/08/222560285_383984693435685_8126693780151981263_n-300x300.jpg" alt="Al Capone — partner Okayka" width="120" height="120" loading="lazy" decoding="async"></a>
<a href="{pfx}partner-okayka/stek-i-wino/index.html" title="Stek i Wino"><img src="https://okaytaxi.pl/wp-content/uploads/2021/08/233663853_517682642648454_5569740505533794322_n-300x300.jpg" alt="Stek i Wino — partner Okayka" width="120" height="120" loading="lazy" decoding="async"></a>
<a href="{pfx}partner-okayka/magnum/index.html" title="Magnum"><img src="https://okaytaxi.pl/wp-content/uploads/2021/08/237446803_403315848169236_7822426788490659224_n-300x300.jpg" alt="Magnum — partner Okayka" width="120" height="120" loading="lazy" decoding="async"></a>
<a href="{pfx}partner-okayka/czarny-tech/index.html" title="Czarny Tech"><img src="https://okaytaxi.pl/wp-content/uploads/2021/08/8bfe87071488a1c5-150x150.png" alt="Czarny Tech — partner Okayka" width="120" height="120" loading="lazy" decoding="async"></a>
<a href="{pfx}partner-okayka/grupa-tobi/index.html" title="Grupa Tobi"><img src="https://okaytaxi.pl/wp-content/uploads/2021/08/20faf959a6f4dc29-150x150.png" alt="Grupa Tobi — partner Okayka" width="120" height="120" loading="lazy" decoding="async"></a>
<a href="{pfx}partner-okayka/tajemnicza-piwnica/index.html" title="Tajemnicza Piwnica"><img src="https://okaytaxi.pl/wp-content/uploads/2021/08/228406983_226147332845008_96367679627940252_n-300x300.jpg" alt="Tajemnicza Piwnica — partner Okayka" width="120" height="120" loading="lazy" decoding="async"></a>
</div>
</div>
</section>
"""


def get_prefix(rel_from_base):
    """Get relative prefix from a directory relative to BASE."""
    if rel_from_base == ".":
        return ""
    depth = rel_from_base.replace("\\", "/").count("/") + 1
    return "../" * depth


def fix_file(fpath):
    """Fix links in a single file to append index.html for file:/// browsing."""
    rel_dir = os.path.relpath(os.path.dirname(fpath), BASE).replace("\\", "/")
    prefix = get_prefix(rel_dir)

    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # Fix internal links: href="something/" -> href="something/index.html"
    # Match relative paths ending with / that are internal pages
    # Pattern: href="(optional ../)pagename/" -> href="(optional ../)pagename/index.html"
    def fix_href(m):
        full = m.group(0)
        url = m.group(1)
        # Skip external links, anchors, tel:, mailto:, javascript:
        if url.startswith(("http", "#", "tel:", "mailto:", "javascript:")):
            return full
        # Skip CSS/JS/image files
        if any(url.endswith(ext) for ext in (".css", ".js", ".png", ".jpg", ".svg", ".html")):
            return full
        # If ends with /, add index.html
        if url.endswith("/"):
            return f'href="{url}index.html"'
        return full

    content = re.sub(r'href="([^"]*)"', fix_href, content)

    # Add partner logos section to index.html (homepage) before CTA section
    if os.path.basename(os.path.dirname(fpath)) == "okaytaxi" and os.path.basename(fpath) == "index.html":
        logos = PARTNER_LOGOS_HTML.replace("{pfx}", prefix)
        # Insert before the CTA banner section (before "Potrzebujesz taxi?")
        if "logos-grid" not in content and "Potrzebujesz taxi?" in content:
            content = content.replace(
                '<!-- ===== CTA ===== -->',
                logos + '\n<!-- ===== CTA ===== -->'
            )
            # If no marker, try before section with cta-banner
            if "logos-grid" not in content:
                content = content.replace(
                    '<section>\n<div class="container">\n<div class="cta-banner reveal">\n<h2>Potrzebujesz taxi?',
                    logos + '\n<section>\n<div class="container">\n<div class="cta-banner reveal">\n<h2>Potrzebujesz taxi?'
                )

    # Add partner logos to okayka page too
    if fpath.endswith(os.path.join("okayka", "index.html")):
        logos = PARTNER_LOGOS_HTML.replace("{pfx}", prefix)
        if "logos-grid" not in content and "cta-banner" in content:
            # Insert before the CTA section
            idx = content.find('<section><div class="container"><div class="cta-banner')
            if idx > 0:
                content = content[:idx] + logos + "\n" + content[idx:]

    if content != original:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


# Process all HTML files
changed = 0
total = 0
for root, dirs, files in os.walk(BASE):
    for fname in files:
        if not fname.endswith(".html"):
            continue
        total += 1
        fpath = os.path.join(root, fname)
        if fix_file(fpath):
            changed += 1
            print(f"  Fixed: {os.path.relpath(fpath, BASE)}")

print(f"\n{changed}/{total} files updated")
print("DONE")
