from pathlib import Path
import os
import re

root = Path(os.environ["PROJECT_DIR"])
print("PROJECT_DIR:", root)

targets = [
    "app/src/main/java/com/pinky/dashboard/ui/screens/analytics/AnalyticsScreen.kt",
    "app/src/main/java/com/pinky/dashboard/data/repository/RepositoriesImpl.kt",
    "app/src/main/java/com/pinky/dashboard/ui/PinkyViewModel.kt",
    "app/src/main/java/com/pinky/dashboard/ui/PinkyApp.kt",
    "app/src/main/java/com/pinky/dashboard/domain/model/Order.kt",
    "app/src/main/java/com/pinky/dashboard/ui/screens/prime/PrimeScreen.kt",
    "app/src/main/java/com/pinky/dashboard/data/remote/SupabaseClient.kt",
]
for relative in targets:
    path = root / relative
    if not path.is_file():
        print(f"\n=== MISSING: {relative} ===")
        continue
    lines = path.read_text(encoding="utf-8").splitlines()
    print(f"\n=== TARGET SOURCE: {relative} ({len(lines)} lines) ===")
    if len(lines) <= 1000:
        for number, line in enumerate(lines, 1):
            print(f"{number}: {line}")
    else:
        print(f"File too large for full log; first 1000 lines only.")
        for number, line in enumerate(lines[:1000], 1):
            print(f"{number}: {line}")

patterns = re.compile(r"data class AnalyticsData|interface AnalyticsRepository|enum class OrderStatus|data class .*PrimeSubscription|prime_subscriptions|VIEW_PROFIT")
for path in root.rglob("*.kt"):
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        continue
    hits = [i for i, line in enumerate(lines) if patterns.search(line)]
    if not hits or str(path.relative_to(root)) in targets:
        continue
    print(f"\n=== MODEL OR PRIME SOURCE: {path.relative_to(root)} ({len(lines)} lines) ===")
    ranges = []
    for hit in hits:
        start, end = max(0, hit - 25), min(len(lines), hit + 55)
        if ranges and start <= ranges[-1][1]:
            ranges[-1] = (ranges[-1][0], max(ranges[-1][1], end))
        else:
            ranges.append((start, end))
    for start, end in ranges:
        print(f"--- lines {start + 1}-{end} ---")
        for number in range(start, end):
            print(f"{number + 1}: {lines[number]}")
