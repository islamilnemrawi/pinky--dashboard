#!/usr/bin/env python3
"""Repair Retrofit @Body Map wildcard signatures after all Elory overlays are applied."""
from pathlib import Path
import os
import re

PROJECT_DIR = Path(os.environ["PROJECT_DIR"]).resolve()
SERVICE_FILE = PROJECT_DIR / "app/src/main/java/com/pinky/dashboard/data/remote/SupabaseClient.kt"

if not SERVICE_FILE.is_file():
    raise SystemExit(f"Supabase service file not found: {SERVICE_FILE}")

source = SERVICE_FILE.read_text(encoding="utf-8")
interface_match = re.search(r"\binterface\s+SupabaseService\s*\{", source)
if not interface_match:
    raise SystemExit("SupabaseService interface declaration not found")

def matching_brace(text: str, opening: int) -> int:
    depth = 0
    state = "code"
    quote = ""
    i = opening
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if state == "line_comment":
            if char == "\n":
                state = "code"
        elif state == "block_comment":
            if char == "*" and nxt == "/":
                state = "code"
                i += 1
        elif state == "string":
            if char == "\\":
                i += 1
            elif char == quote:
                state = "code"
        else:
            if char == "/" and nxt == "/":
                state = "line_comment"
                i += 1
            elif char == "/" and nxt == "*":
                state = "block_comment"
                i += 1
            elif char in ('"', "'"):
                state = "string"
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    raise SystemExit("SupabaseService has an unmatched brace")

opening = source.find("{", interface_match.start())
closing = matching_brace(source, opening)
service_body = source[opening + 1:closing]

# A body parameter Map<String, Any/Any?> becomes Map<String, ? extends Object>
# in Java unless wildcard suppression is placed on the value type argument.
body_map = re.compile(
    r"(@Body\s+\w+\s*:\s*Map\s*<\s*String\s*,\s*)"
    r"(?:(@JvmSuppressWildcards)\s+)?(Any\??)(\s*>)"
)

changes = 0
def suppress(match: re.Match) -> str:
    global changes
    if match.group(2):
        return match.group(0)
    changes += 1
    return match.group(1) + "@JvmSuppressWildcards " + match.group(3) + match.group(4)

updated_body = body_map.sub(suppress, service_body)

# These declarations are inserted by existing overlay scripts and must be present
# before the final Retrofit service contract is validated.
required_methods = (
    "saveShippingGovernorate",
    "patchSiteCustomizationsRaw",
    "getSiteCustomizationDraft",
    "clearSiteCustomizationDraft",
)
for method in required_methods:
    if not re.search(r"\bsuspend\s+fun\s+" + re.escape(method) + r"\s*\(", updated_body):
        raise SystemExit(f"Expected Retrofit service method is missing: {method}")

# Verify each affected API's @Body Map value type is now suppressed. Return
# types are intentionally not rewritten.
for method in required_methods:
    start = re.search(r"\bsuspend\s+fun\s+" + re.escape(method) + r"\s*\(", updated_body)
    open_paren = updated_body.find("(", start.start())
    depth = 0
    end = -1
    for i in range(open_paren, len(updated_body)):
        if updated_body[i] == "(":
            depth += 1
        elif updated_body[i] == ")":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end < 0:
        raise SystemExit(f"Could not parse Retrofit method parameters: {method}")
    signature = updated_body[open_paren:end + 1]
    if not re.search(
        r"@Body\s+\w+\s*:\s*Map\s*<\s*String\s*,\s*@JvmSuppressWildcards\s+Any\??\s*>",
        signature,
    ):
        raise SystemExit(f"Retrofit @Body wildcard suppression did not validate: {method}")

unsuppressed_body_map = re.compile(
    r"@Body\\s+\\w+\\s*:\\s*Map\\s*<\\s*String\\s*,\\s*"
    r"(?!@JvmSuppressWildcards\\b)Any\\??\\s*>"
)
remaining = unsuppressed_body_map.search(updated_body)
if remaining:
    raise SystemExit(
        "An unsuppressed @Body Map<String, Any/Any?> remains in SupabaseService: "
        + remaining.group(0)
    )

# Customer bulk deletion must keep its dedicated typed request DTO; don't
# replace this API with a generic Map while repairing neighbouring methods.
customer_delete = re.search(
    r"\bsuspend\s+fun\s+deleteSelectedData\s*\(([^)]*)\)",
    updated_body,
    re.DOTALL,
)
if not customer_delete or "SupabaseDeleteSelectedDataRequest" not in customer_delete.group(1):
    raise SystemExit("Customer deletion Retrofit method lost its typed request DTO")

if updated_body != service_body:
    source = source[:opening + 1] + updated_body + source[closing:]
    SERVICE_FILE.write_text(source, encoding="utf-8")

print(
    "PASS: Retrofit @Body Map wildcard validation; "
    f"{changes} unsuppressed parameter(s) repaired; "
    "website draft and customer-delete contracts preserved."
)
