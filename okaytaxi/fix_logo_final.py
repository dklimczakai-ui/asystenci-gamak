import os, re, time

BASE = r"C:\Users\klimc\Desktop\Asystenci\okaytaxi"
bust = str(int(time.time()))
count = 0

for root, dirs, files in os.walk(BASE):
    for fname in files:
        if not fname.endswith(".html"):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            c = f.read()
        orig = c

        # Logo header: 64 -> 80
        c = c.replace('width="64" height="64"', 'width="80" height="80"')

        # Cache bust
        c = re.sub(r'style\.css\?v=\d+', f'style.css?v={bust}', c)
        c = re.sub(r'script\.js\?v=\d+', f'script.js?v={bust}', c)

        if c != orig:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(c)
            count += 1

print(f"{count} files updated, v={bust}")
