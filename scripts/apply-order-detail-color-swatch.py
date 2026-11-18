#!/usr/bin/env python3
"""Render the customer's selected product color as a swatch in order details only."""
from pathlib import Path
import os

ROOT = Path(os.environ["PROJECT_DIR"]).resolve()
DETAIL = ROOT / "app/src/main/java/com/pinky/dashboard/ui/screens/orders/OrderDetailDialog.kt"
source = DETAIL.read_text(encoding="utf-8")

old_attributes = '''                                    val attributes = listOfNotNull(
                                        if (item.variantName.isNullOrEmpty()) null else "النوع: ${item.variantName}",
                                        if (item.color.isNullOrEmpty()) null else "اللون: ${item.color}",
                                        if (item.size.isNullOrEmpty()) null else "المقاس: ${item.size}"
                                    )'''
new_attributes = '''                                    val attributes = listOfNotNull(
                                        if (item.variantName.isNullOrEmpty()) null else "النوع: ${item.variantName}",
                                        if (item.size.isNullOrEmpty()) null else "المقاس: ${item.size}"
                                    )'''
if new_attributes not in source:
    if source.count(old_attributes) != 1:
        raise SystemExit(f"Expected one order-item attributes block, found {source.count(old_attributes)}")
    source = source.replace(old_attributes, new_attributes, 1)
    print("PASS: remove raw color code from order item attribute text")
else:
    print("Already applied: order item attribute text")

old_insert = '''                                    if (attributes.isNotEmpty()) {
                                        Text(
                                            text = attributes.joinToString(" • "),
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }

                                    Text(
                                        text = "${item.quantity} قطعة × ${Formatters.formatCurrencyEgp(item.unitPrice)}",'''
new_insert = '''                                    if (attributes.isNotEmpty()) {
                                        Text(
                                            text = attributes.joinToString(" • "),
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                    if (!item.color.isNullOrBlank()) {
                                        val selectedColor = parseOrderItemColor(item.color)
                                        val isHexColor = item.color.trim().matches(Regex("^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$"))
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(7.dp)
                                        ) {
                                            Text(
                                                text = if (isHexColor) "اللون:" else "اللون: ${item.color}",
                                                style = MaterialTheme.typography.bodySmall,
                                                color = MaterialTheme.colorScheme.onSurfaceVariant
                                            )
                                            Box(
                                                modifier = Modifier
                                                    .size(19.dp)
                                                    .clip(CircleShape)
                                                    .background(selectedColor ?: MaterialTheme.colorScheme.surfaceVariant)
                                                    .border(
                                                        width = 1.dp,
                                                        color = MaterialTheme.colorScheme.outline.copy(alpha = 0.55f),
                                                        shape = CircleShape
                                                    )
                                                    .testTag("order_item_color_swatch"),
                                                contentAlignment = Alignment.Center
                                            )
                                        }
                                    }

                                    Text(
                                        text = "${item.quantity} قطعة × ${Formatters.formatCurrencyEgp(item.unitPrice)}",'''
if new_insert not in source:
    if source.count(old_insert) != 1:
        raise SystemExit(f"Expected one order item attribute rendering block, found {source.count(old_insert)}")
    source = source.replace(old_insert, new_insert, 1)
    print("PASS: render selected color as a circular swatch")
else:
    print("Already applied: color swatch rendering")

old_import = '''import androidx.compose.foundation.shape.RoundedCornerShape'''
new_import = '''import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape'''
if new_import not in source:
    if source.count(old_import) != 1:
        raise SystemExit("Could not locate shape imports")
    source = source.replace(old_import, new_import, 1)

marker = '''@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrderDetailDialog('''
helper = '''/**
 * Converts the color value saved with the order item into the exact Compose swatch color.
 * Supports #RGB, #RRGGBB, #AARRGGBB and common Arabic color names.
 */
internal fun parseOrderItemColor(value: String): Color? {
    val raw = value.trim()
    if (raw.startsWith("#")) {
        val hex = raw.drop(1)
        val argb = runCatching {
            when (hex.length) {
                3 -> {
                    val r = hex.substring(0, 1).repeat(2).toInt(16)
                    val g = hex.substring(1, 2).repeat(2).toInt(16)
                    val b = hex.substring(2, 3).repeat(2).toInt(16)
                    (0xFF shl 24) or (r shl 16) or (g shl 8) or b
                }
                6 -> (0xFF000000L or hex.toLong(16)).toInt()
                8 -> hex.toLong(16).toInt()
                else -> return null
            }
        }.getOrNull() ?: return null
        return Color(argb)
    }

    return when (raw.lowercase()) {
        "أحمر", "احمر", "red" -> Color(0xFFF44336)
        "أزرق", "ازرق", "blue" -> Color(0xFF2196F3)
        "أخضر", "اخضر", "green" -> Color(0xFF4CAF50)
        "أصفر", "اصفر", "yellow" -> Color(0xFFFFEB3B)
        "أسود", "اسود", "black" -> Color(0xFF000000)
        "أبيض", "ابيض", "white" -> Color(0xFFFFFFFF)
        "وردي", "pink" -> Color(0xFFE91E63)
        "بنفسجي", "purple" -> Color(0xFF9C27B0)
        "برتقالي", "orange" -> Color(0xFFFF9800)
        "رمادي", "gray", "grey" -> Color(0xFF9E9E9E)
        "بني", "brown" -> Color(0xFF795548)
        "بيج", "beige" -> Color(0xFFD7C4A3)
        else -> null
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrderDetailDialog('''
if 'internal fun parseOrderItemColor(value: String)' not in source:
    if source.count(marker) != 1:
        raise SystemExit("Could not locate OrderDetailDialog declaration")
    source = source.replace(marker, helper, 1)

DETAIL.write_text(source, encoding="utf-8")
print("PASS: dashboard order-detail color swatch patch")
