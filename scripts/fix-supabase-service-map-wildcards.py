from pathlib import Path
import os
import re

root = Path(os.environ["PROJECT_DIR"]).resolve()
matches = list(root.rglob("SupabaseService.kt"))
if len(matches) != 1:
    raise SystemExit(f"Expected exactly one SupabaseService.kt, found {len(matches)}")

path = matches[0]
source = path.read_text(encoding="utf-8")

target = re.compile(
    r"(clearSiteCustomizationDraft\s*\([^)]*?)Map\s*<\s*String\s*,\s*\*>",
    re.DOTALL,
)
if len(target.findall(source)) != 1:
    raise SystemExit("Expected one clearSiteCustomizationDraft Map<String, *> parameter; source differs from reviewed contract")

# Retrofit inspects Java reflection types. Kotlin's star projection becomes
# Map<String, ?> and is rejected; suppress the generated wildcard at the value type.
updated, target_count = target.subn(
    lambda m: m.group(1) + "Map<String, @JvmSuppressWildcards Any>",
    source,
)
if target_count != 1:
    raise SystemExit("Could not safely repair clearSiteCustomizationDraft")

# Apply the same narrowly-scoped correction to other wildcard Map parameters
# declared by this Retrofit service (including customer mutation endpoints).
wildcard = re.compile(r"Map\s*<\s*String\s*,\s*\*>")
updated, other_count = wildcard.subn(
    "Map<String, @JvmSuppressWildcards Any>",
    updated,
)

if "clearSiteCustomizationDraft" not in updated:
    raise SystemExit("Target method disappeared during patch")
if wildcard.search(updated):
    raise SystemExit("A wildcard Map parameter remains in SupabaseService")

path.write_text(updated, encoding="utf-8")
print(f"Repaired clearSiteCustomizationDraft and {other_count} additional wildcard Map parameter(s) in {path.name}")
