import os

BASE = r"C:\Users\klimc\Desktop\Asystenci\okaytaxi"

for root, dirs, files in os.walk(BASE):
    for fname in files:
        if not fname.endswith(".html"):
            continue
        fpath = os.path.join(root, fname)
        rel_dir = os.path.relpath(root, BASE).replace(os.sep, "/")

        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        if rel_dir == ".":
            content = content.replace('href="/index.html"', 'href="index.html"')
        else:
            depth = rel_dir.count("/") + 1
            prefix = "../" * depth
            content = content.replace('href="/index.html"', f'href="{prefix}index.html"')

        if content != original:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed: {os.path.relpath(fpath, BASE)}")

print("DONE")
