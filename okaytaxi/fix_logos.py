"""Fix partner logo image URLs to use existing files on server."""
import os

BASE = r"C:\Users\klimc\Desktop\Asystenci\okaytaxi"

REPLACEMENTS = {
    "Barimed_podstawowy@2x-300x300.png": "Barimed_podstawowy%402x-150x150.png",
    "Eco-horizon-300x300.jpg": "Eco-horizon-150x150.jpg",
    "ecusoft_logoR_2-300x300.png": "ecusoft_logoR_2.png",
    "2be-300x300.jpg": "2be.jpg",
    "215338898_375022654331889_1463690656319699277_n-300x300.jpg": "215338898_375022654331889_1463690656319699277_n-150x150.jpg",
    "222560285_383984693435685_8126693780151981263_n-300x300.jpg": "222560285_383984693435685_8126693780151981263_n-150x150.jpg",
    "233663853_517682642648454_5569740505533794322_n-300x300.jpg": "233663853_517682642648454_5569740505533794322_n-150x150.jpg",
    "237446803_403315848169236_7822426788490659224_n-300x300.jpg": "237446803_403315848169236_7822426788490659224_n-150x150.jpg",
    "8bfe87071488a1c5-150x150.png": "8bfe87071488a1c5-150x150.png",  # already OK
    "20faf959a6f4dc29-150x150.png": "20faf959a6f4dc29-150x150.png",  # already OK
    "228406983_226147332845008_96367679627940252_n-300x300.jpg": "228406983_226147332845008_96367679627940252_n-150x150.jpg",
}

# Also fix the @ encoding issue - Barimed has @ in filename
# The src attribute already has @2x but it needs %40 for URL encoding
# Actually browsers handle @ fine in src, the issue was the -300x300 suffix

count = 0
for root, dirs, files in os.walk(BASE):
    for fname in files:
        if not fname.endswith(".html"):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        original = content
        for old, new in REPLACEMENTS.items():
            content = content.replace(old, new)

        if content != original:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            count += 1
            print(f"Fixed: {os.path.relpath(fpath, BASE)}")

print(f"\n{count} files fixed")
