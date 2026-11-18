#!/usr/bin/env python3
"""Verify that order detail renders the saved selected color as a circular swatch."""
from pathlib import Path
import os

root = Path(os.environ["PROJECT_DIR"])
path = root / "app/src/main/java/com/pinky/dashboard/ui/screens/orders/OrderDetailDialog.kt"
source = path.read_text(encoding="utf-8")
required = [
    "internal fun parseOrderItemColor(value: String): Color?",
    "CircleShape",
    '.testTag("order_item_color_swatch")',
    "val selectedColor = parseOrderItemColor(item.color)",
    'if (isHexColor) "اللون:" else "اللون: ${item.color}"',
]
missing = [marker for marker in required if marker not in source]
if missing:
    raise SystemExit(f"Order color swatch verification failed: {missing}")
if 'else "اللون: ${item.color}"' not in source:
    raise SystemExit("Named color fallback label is missing")
print("PASS: order detail color swatch is present; hex values are no longer shown as raw codes.")
