from pathlib import Path
import os
root = Path(os.environ["PROJECT_DIR"])
terms = ("profit", "ربح", "هامش", "wholesalePrice", "wholesale_price")
found = 0
for path in root.rglob("*.kt"):
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        continue
    hits = [i for i, line in enumerate(lines) if any(term.lower() in line.lower() for term in terms)]
    if not hits:
        continue
    print(f"\n=== FINANCE SOURCE: {path.relative_to(root)} ({len(lines)} lines) ===")
    shown = set()
    for i in hits:
        start, end = max(0, i-12), min(len(lines), i+18)
        if any(n in shown for n in range(start,end)):
            continue
        shown.update(range(start,end))
        print(f"--- lines {start+1}-{end} ---")
        for n in range(start,end):
            print(f"{n+1}: {lines[n]}")
        found += 1
if not found:
    raise SystemExit("No finance-related Kotlin source found; refusing to patch blindly.")
