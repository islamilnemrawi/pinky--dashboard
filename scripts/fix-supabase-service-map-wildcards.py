from pathlib import Path
import os
import re

root = Path(os.environ["PROJECT_DIR"]).resolve()
candidates = []
for path in root.rglob("*.kt"):
    source = path.read_text(encoding="utf-8")
    if "clearSiteCustomizationDraft" in source:
        candidates.append((path, source))
if len(candidates) != 1:
    raise SystemExit(f"Expected exactly one Kotlin file declaring clearSiteCustomizationDraft, found {len(candidates)}")

path, source = candidates[0]
target = re.compile(
    r"(clearSiteCustomizationDraft\s*\([^)]*?)Map\s*<\s*String\s*,\s*\*>",
    re.DOTALL,
)
if len(target.findall(source)) != 1:
    raise SystemExit("Expected one clearSiteCustomizationDraft Map<String, *> parameter; source differs from reviewed contract")

updated, target_count = target.subn(
    lambda m: m.group(1) + "Map<String, @JvmSuppressWildcards Any>",
    source,
)
if target_count != 1:
    raise SystemExit("Could not safely repair clearSiteCustomizationDraft")

# Repair only Retrofit service declarations in the same file, including
# customer mutation endpoints, without touching unrelated application maps.
wildcard = re.compile(r"Map\s*<\s*String\s*,\s*\*>")
updated, other_count = wildcard.subn(
    "Map<String, @JvmSuppressWildcards Any>",
    updated,
)
if wildcard.search(updated):
    raise SystemExit("A wildcard Map parameter remains in the Supabase service source")

path.write_text(updated, encoding="utf-8")
print(f"Repaired clearSiteCustomizationDraft and {other_count} other wildcard Map parameter(s) in {path.name}")
