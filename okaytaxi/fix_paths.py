import os, re

BASE = r"C:\Users\klimc\Desktop\Asystenci\okaytaxi"

for root, dirs, files in os.walk(BASE):
    for fname in files:
        if not fname.endswith(".html"):
            continue
        fpath = os.path.join(root, fname)
        rel = os.path.relpath(root, BASE).replace("\\", "/")

        if rel == ".":
            prefix = ""
        else:
            depth = rel.count("/") + 1
            prefix = "../" * depth

        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # Fix CSS path
        content = content.replace('href="/css/style.css"', f'href="{prefix}css/style.css"')

        # Fix JS path
        content = content.replace('src="/js/script.js"', f'src="{prefix}js/script.js"')

        # Fix internal nav links: href="/something/" -> href="{prefix}something/"
        # Only match lowercase paths starting with /
        def fix_link(m):
            return f'href="{prefix}{m.group(1)}'
        content = re.sub(r'href="/([a-z])', fix_link, content)

        if content != original:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed: {os.path.relpath(fpath, BASE)}")
        else:
            print(f"Skip:  {os.path.relpath(fpath, BASE)}")

print("\nDONE")
