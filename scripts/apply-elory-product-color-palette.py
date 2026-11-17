from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ["PROJECT_DIR"]).resolve()


def source(path: str) -> tuple[Path, str]:
    file = ROOT / path
    return file, file.read_text(encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print("Already applied: " + label)
        return text
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            "Refusing ambiguous edit for " + label + ": expected one anchor, found " + str(count)
        )
    print("PASS " + label)
    return text.replace(old, new, 1)


# Domain model.
path = "app/src/main/java/com/pinky/dashboard/domain/model/Product.kt"
file, text = source(path)
text = replace_once(
    text,
    "data class Product(\n",
    """data class ProductColorOption(
    val name: String,
    val hex: String
)

data class Product(
""",
    "product color option model",
)
text = replace_once(
    text,
    "    val createdAt: Long = System.currentTimeMillis()\n)",
    "    val createdAt: Long = System.currentTimeMillis(),\n    val colorOptions: List<ProductColorOption> = emptyList()\n)",
    "product model color option field",
)
file.write_text(text, encoding="utf-8")


# Supabase JSONB DTO.
path = "app/src/main/java/com/pinky/dashboard/data/remote/SupabaseClient.kt"
file, text = source(path)
text = replace_once(
    text,
    "@JsonClass(generateAdapter = true)\ndata class SupabaseProductAdminDto(",
    """@JsonClass(generateAdapter = true)
data class SupabaseProductColorOptionDto(
    @Json(name = "name") val name: String,
    @Json(name = "hex") val hex: String
)

@JsonClass(generateAdapter = true)
data class SupabaseProductAdminDto(""",
    "Supabase color option DTO",
)
text = replace_once(
    text,
    '@Json(name = "color_options") val colorOptions: List<String>? = null',
    '@Json(name = "color_options") val colorOptions: List<SupabaseProductColorOptionDto>? = null',
    "Supabase structured color_options field",
)
file.write_text(text, encoding="utf-8")


# Store structured swatches in the existing Room colorsJson field to avoid destructive DB migrations.
path = "app/src/main/java/com/pinky/dashboard/data/repository/RepositoriesImpl.kt"
file, text = source(path)
helper_anchor = "class ProductRepositoryImpl(\n"
helpers = r'''private const val ELORY_COLOR_OPTIONS_STORAGE_PREFIX = "__ELORY_COLOR_OPTIONS_V1__:"

private fun encodeLocalProductColors(
    options: List<com.pinky.dashboard.domain.model.ProductColorOption>,
    legacyNames: List<String>
): String {
    if (options.isEmpty()) return legacyNames.joinToString(",")
    val array = org.json.JSONArray()
    options.forEach { option ->
        array.put(
            org.json.JSONObject()
                .put("name", option.name)
                .put("hex", option.hex)
        )
    }
    return ELORY_COLOR_OPTIONS_STORAGE_PREFIX + array.toString()
}

private fun decodeLocalProductColors(
    stored: String
): Pair<List<String>, List<com.pinky.dashboard.domain.model.ProductColorOption>> {
    if (!stored.startsWith(ELORY_COLOR_OPTIONS_STORAGE_PREFIX)) {
        val names = stored.split(",").map { it.trim() }.filter { it.isNotEmpty() }
        return names to emptyList()
    }
    return try {
        val json = org.json.JSONArray(stored.removePrefix(ELORY_COLOR_OPTIONS_STORAGE_PREFIX))
        val options = buildList {
            for (index in 0 until json.length()) {
                val item = json.optJSONObject(index) ?: continue
                val name = item.optString("name").trim()
                val hex = item.optString("hex").trim()
                if (name.isNotEmpty() && hex.matches(Regex("^#[0-9A-Fa-f]{6}$"))) {
                    add(com.pinky.dashboard.domain.model.ProductColorOption(name, hex.uppercase()))
                }
            }
        }
        options.map { it.name } to options
    } catch (error: Exception) {
        android.util.Log.w("EloryProducts", "Could not decode cached product swatches; preserving legacy names.", error)
        emptyList<String>() to emptyList()
    }
}

'''
text = replace_once(text, helper_anchor, helpers + helper_anchor, "local product color codec")
text = replace_once(
    text,
    "                colors = product.colors,\n                sizes = product.sizes,\n                gallery = product.gallery",
    """                colors = product.colorOptions.map { it.name }.ifEmpty { product.colors },
                sizes = product.sizes,
                gallery = product.gallery,
                colorOptions = product.colorOptions.map {
                    com.pinky.dashboard.data.remote.SupabaseProductColorOptionDto(it.name, it.hex)
                }""",
    "save structured color options to Supabase",
)
text = replace_once(
    text,
    '                colorsJson = product.colors.joinToString(",") ,'.replace(" ,", ","),
    "                colorsJson = encodeLocalProductColors(product.colorOptions, product.colors),",
    "persist structured swatches in existing local Room field",
)
text = replace_once(
    text,
    '                        colorsJson = dto.colors?.joinToString(",") ?: "",',
    """                        colorsJson = encodeLocalProductColors(
                            dto.colorOptions?.map {
                                com.pinky.dashboard.domain.model.ProductColorOption(it.name, it.hex)
                            }.orEmpty(),
                            dto.colors.orEmpty()
                        ),""",
    "restore swatches from Supabase into local cache",
)
text = replace_once(
    text,
    "    private fun ProductEntity.toDomain(): Product {\n        return Product(",
    """    private fun ProductEntity.toDomain(): Product {
        val storedColors = decodeLocalProductColors(colorsJson)
        return Product(""",
    "decode product swatches into domain model",
)
text = replace_once(
    text,
    '            colors = if (colorsJson.isBlank()) emptyList() else colorsJson.split(",").filter { it.isNotBlank() },',
    "            colors = storedColors.first,\n            colorOptions = storedColors.second,",
    "map cached swatches to domain model",
)
file.write_text(text, encoding="utf-8")


# Professional visual palette in the product editor.
path = "app/src/main/java/com/pinky/dashboard/ui/screens/products/ProductEditDialog.kt"
file, text = source(path)
text = replace_once(
    text,
    "import androidx.compose.foundation.shape.RoundedCornerShape\n",
    "import androidx.compose.foundation.shape.CircleShape\nimport androidx.compose.foundation.shape.RoundedCornerShape\n",
    "circle shape import",
)
text = replace_once(
    text,
    "import com.pinky.dashboard.domain.model.ProductVariant\n",
    "import com.pinky.dashboard.domain.model.ProductVariant\nimport com.pinky.dashboard.domain.model.ProductColorOption\n",
    "product color model import",
)
# Material color chooser controls.
required_color_imports = [
    "import androidx.compose.material3.AlertDialog",
    "import androidx.compose.material3.Slider",
    "import androidx.compose.material3.TextButton"
]
for required_import in required_color_imports:
    if required_import not in text:
        marker = "import androidx.compose.material3.ExperimentalMaterial3Api"
        position = text.find(marker)
        if position < 0:
            raise SystemExit("Could not find Compose Material3 import section for color picker.")
        line_end = text.find("\n", position)
        if line_end < 0:
            raise SystemExit("Malformed Compose import section.")
        text = text[:line_end + 2] + required_import + "\n" + text[line_end + 2:]

palette_helpers = r'''
private fun eloryColorFromHex(hex: String): Color =
    runCatching { Color(android.graphics.Color.parseColor(hex)) }.getOrDefault(Color.Gray)

private fun eloryColorCheckTint(hex: String): Color {
    val parsed = runCatching { android.graphics.Color.parseColor(hex) }.getOrDefault(android.graphics.Color.GRAY)
    val luminance =
        (android.graphics.Color.red(parsed) * 0.299 +
            android.graphics.Color.green(parsed) * 0.587 +
            android.graphics.Color.blue(parsed) * 0.114) / 255.0
    return if (luminance > 0.62) Color(0xFF171717) else Color.White
}

private fun legacyEloryProductColor(name: String): ProductColorOption {
    val key = name.trim().lowercase()
        .replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        .replace("ى", "ي").replace(" ", "")
    val hex = when (key) {
        "احمر", "red" -> "#DC2626"
        "عنابي", "نبيتي", "burgundy", "maroon" -> "#7F1D3A"
        "وردي", "pink" -> "#EC4899"
        "روز", "rose" -> "#D87591"
        "موف", "mauve" -> "#8B5CF6"
        "لافندر", "lavender" -> "#B49AE8"
        "بنفسجي", "purple", "violet" -> "#6D4CBB"
        "ازرق", "blue" -> "#2563EB"
        "كحلي", "navy" -> "#1E3A8A"
        "سماوي", "cyan", "skyblue" -> "#38BDF8"
        "تركواز", "turquoise", "teal" -> "#0F9D9A"
        "اخضر", "green" -> "#16A34A"
        "زيتي", "olive" -> "#65743A"
        "نعناعي", "mint" -> "#A7DCC3"
        "اصفر", "yellow" -> "#EAB308"
        "ذهبي", "gold" -> "#C7A04A"
        "برتقالي", "orange" -> "#F97316"
        "بني", "brown" -> "#8B5E3C"
        "بيج", "beige" -> "#D6C2A1"
        "جملي", "camel" -> "#B98B62"
        "ابيض", "white", "اوفوايت", "offwhite" -> "#F8FAFC"
        "عاجي", "ivory" -> "#F2E8D5"
        "رمادي", "gray", "grey", "فضي", "silver" -> "#9CA3AF"
        "اسود", "black" -> "#171717"
        else -> "#8E7A85"
    }
    return ProductColorOption(name.trim(), hex)
}

'''
text = replace_once(
    text,
    "@OptIn(ExperimentalMaterial3Api::class)\n@Composable\nfun ProductEditDialog(",
    palette_helpers + "@OptIn(ExperimentalMaterial3Api::class)\n@Composable\nfun ProductEditDialog(",
    "professional color palette and legacy color mapper",
)
text = replace_once(
    text,
    '    var colorsText by remember { mutableStateOf(initialProduct?.colors?.joinToString("، ") ?: "") }',
    """    var colorOptions by remember(initialProduct?.id) {
        mutableStateOf(
            initialProduct?.colorOptions?.takeIf { it.isNotEmpty() }
                ?: initialProduct?.colors?.map(::legacyEloryProductColor).orEmpty()
        )
    }
    var showColorPicker by remember(initialProduct?.id) { mutableStateOf(false) }
    var pickerHue by remember(initialProduct?.id) { mutableStateOf(320f) }
    var pickerSaturation by remember(initialProduct?.id) { mutableStateOf(0.72f) }
    var pickerBrightness by remember(initialProduct?.id) { mutableStateOf(0.88f) }
    var colorError by remember(initialProduct?.id) { mutableStateOf<String?>(null) }
    val pickerHex = remember(pickerHue, pickerSaturation, pickerBrightness) {
        val argb = android.graphics.Color.HSVToColor(floatArrayOf(pickerHue, pickerSaturation, pickerBrightness))
        String.format(java.util.Locale.US, "#%06X", argb and 0xFFFFFF)
    }""",
    "product color selection state",
)
old_colors_ui = '''                    // Stock, Colors, Sizes
                    item {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            OutlinedTextField(
                                value = stockText,
                                onValueChange = { stockText = it },
                                label = { Text("الكمية بالمخزون *") },
                                modifier = Modifier.weight(1f).testTag("product_stock_input"),
                                shape = RoundedCornerShape(12.dp)
                            )

                            OutlinedTextField(
                                value = colorsText,
                                onValueChange = { colorsText = it },
                                label = { Text("الألوان (مفصولة بـ ،)") },
                                placeholder = { Text("وردي، أسود، كحلي") },
                                modifier = Modifier.weight(1.5f),
                                shape = RoundedCornerShape(12.dp)
                            )
                        }
                    }
'''
new_colors_ui = '''                    // Product colors: unrestricted HSV picker and circles only.
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(18.dp),
                            border = CardDefaults.outlinedCardBorder(),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                        ) {
                            Column(
                                Modifier.fillMaxWidth().padding(14.dp),
                                verticalArrangement = Arrangement.spacedBy(12.dp)
                            ) {
                                Row(
                                    Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column(Modifier.weight(1f)) {
                                        Text("ألوان المنتج", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                                        Text(
                                            "اختاري أي درجة لون من منتقي الألوان الحر.",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                    Button(
                                        onClick = {
                                            colorError = null
                                            showColorPicker = true
                                        },
                                        shape = RoundedCornerShape(14.dp),
                                        colors = ButtonDefaults.buttonColors(
                                            containerColor = PinkPrimary,
                                            contentColor = Color(0xFF381528)
                                        )
                                    ) {
                                        Text("اختيار لون")
                                    }
                                }

                                if (colorOptions.isEmpty()) {
                                    Text(
                                        "لم تتم إضافة ألوان بعد.",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                } else {
                                    colorOptions.chunked(6).forEach { selectedRow ->
                                        Row(
                                            Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                                        ) {
                                            selectedRow.forEach { selectedColor ->
                                                Box(
                                                    Modifier.size(42.dp)
                                                        .clip(CircleShape)
                                                        .background(eloryColorFromHex(selectedColor.hex))
                                                        .border(2.dp, MaterialTheme.colorScheme.outlineVariant, CircleShape)
                                                        .clickable {
                                                            colorOptions = colorOptions.filterNot {
                                                                it.hex.equals(selectedColor.hex, ignoreCase = true)
                                                            }
                                                        }
                                                )
                                            }
                                            repeat(6 - selectedRow.size) { Spacer(Modifier.weight(1f)) }
                                        }
                                    }
                                }

                                Text(
                                    "اضغطي على أي دائرة لإزالتها. لا تُعرض أسماء الألوان في المتجر.",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                colorError?.let {
                                    Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                                }
                            }
                        }

                        if (showColorPicker) {
                            AlertDialog(
                                onDismissRequest = { showColorPicker = false },
                                title = { Text("منتقي ألوان المنتج") },
                                text = {
                                    Column(
                                        Modifier.fillMaxWidth(),
                                        verticalArrangement = Arrangement.spacedBy(9.dp)
                                    ) {
                                        Box(
                                            Modifier.fillMaxWidth()
                                                .height(76.dp)
                                                .clip(RoundedCornerShape(16.dp))
                                                .background(eloryColorFromHex(pickerHex))
                                        )
                                        Row(
                                            Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween
                                        ) {
                                            Text("درجة اللون")
                                            Text(pickerHue.toInt().toString() + "°")
                                        }
                                        Slider(
                                            value = pickerHue,
                                            onValueChange = { pickerHue = it },
                                            valueRange = 0f..360f
                                        )
                                        Row(
                                            Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween
                                        ) {
                                            Text("تشبع اللون")
                                            Text((pickerSaturation * 100).toInt().toString() + "%")
                                        }
                                        Slider(
                                            value = pickerSaturation,
                                            onValueChange = { pickerSaturation = it },
                                            valueRange = 0f..1f
                                        )
                                        Row(
                                            Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween
                                        ) {
                                            Text("الإضاءة")
                                            Text((pickerBrightness * 100).toInt().toString() + "%")
                                        }
                                        Slider(
                                            value = pickerBrightness,
                                            onValueChange = { pickerBrightness = it },
                                            valueRange = 0f..1f
                                        )
                                    }
                                },
                                confirmButton = {
                                    TextButton(
                                        onClick = {
                                            val selectedHex = pickerHex.uppercase()
                                            if (colorOptions.none { it.hex.equals(selectedHex, ignoreCase = true) }) {
                                                colorOptions = colorOptions + ProductColorOption(selectedHex, selectedHex)
                                            }
                                            colorError = null
                                            showColorPicker = false
                                        }
                                    ) {
                                        Text("إضافة الدائرة")
                                    }
                                },
                                dismissButton = {
                                    TextButton(onClick = { showColorPicker = false }) {
                                        Text("إلغاء")
                                    }
                                }
                            )
                        }
                    }
'''
text = replace_once(text, old_colors_ui, new_colors_ui, "replace typed colors field with professional swatch palette")
text = replace_once(
    text,
    'val productId = initialProduct?.id ?: "prod_\u0024{System.currentTimeMillis()}"',
    'val productId = initialProduct?.id ?: java.util.UUID.randomUUID().toString()',
    "generate UUID for new products",
)
text = replace_once(
    text,
    '                                            colors = colorsText.split("،", ",").map { it.trim() }.filter { it.isNotEmpty() },',
    '                                            colors = colorOptions.map { it.name },\n                                            colorOptions = colorOptions,',
    "save selected color names and HEX values",
)
file.write_text(text, encoding="utf-8")


# Hide unconfirmed payment attempts from orders, analytics, reports and order detail lookup.
path = "app/src/main/java/com/pinky/dashboard/data/repository/RepositoriesImpl.kt"
file, text = source(path)
order_class_anchor = """class OrderRepositoryImpl(
    private val database: PinkyDatabase
) : OrderRepository {
    private val orderDao = database.orderDao()
"""
order_class_new = order_class_anchor + """
    private fun isUnconfirmedPayment(order: OrderEntity): Boolean {
        val status = order.status.trim().lowercase()
        val method = order.paymentMethod.trim().lowercase()
        val electronic = method in setOf("card", "visa", "paymob", "vodafone_cash", "vodafone cash")
        val transientStatus = status in setOf(
            "جاري الدفع",
            "فشل الدفع",
            "فشل إنشاء الدفع",
            "payment pending",
            "pending payment",
            "payment failed",
            "failed payment",
            "failed to create payment"
        )
        val electronicUnverifiedStatus = electronic && status in setOf("جديد", "جاري التأكيد", "pending", "new")
        return transientStatus || electronicUnverifiedStatus
    }
"""
text = replace_once(text, order_class_anchor, order_class_new, "transient order visibility guard")
flow_start = text.find("override fun getOrdersFlow()")
flow_end = text.find("override suspend fun getOrderById(", flow_start)
if flow_start < 0 or flow_end < 0:
    raise SystemExit("Could not locate OrderRepositoryImpl.getOrdersFlow() boundaries.")
flow = text[flow_start:flow_end]
flow_anchor = "entities.map { entity ->"
if flow.count(flow_anchor) != 1:
    raise SystemExit("Expected one entity mapper inside getOrdersFlow(), found " + str(flow.count(flow_anchor)))
flow = flow.replace(
    flow_anchor,
    "entities.filterNot { isUnconfirmedPayment(it) }.map { entity ->",
    1
)
text = text[:flow_start] + flow + text[flow_end:]
print("PASS hide unpaid and failed payment rows from all dashboard order flows")

detail_start = text.find("override suspend fun getOrderById(")
detail_end = text.find("override suspend fun updateOrderStatus(", detail_start)
if detail_start < 0 or detail_end < 0:
    raise SystemExit("Could not locate OrderRepositoryImpl.getOrderById() boundaries.")
detail = text[detail_start:detail_end]
detail_anchor = "val entity = orderDao.getOrderById(orderId) ?: return@withContext null"
if detail.count(detail_anchor) != 1:
    raise SystemExit("Expected one order entity lookup in getOrderById(), found " + str(detail.count(detail_anchor)))
detail = detail.replace(
    detail_anchor,
    detail_anchor + "\n        if (isUnconfirmedPayment(entity)) return@withContext null",
    1
)
text = text[:detail_start] + detail + text[detail_end:]
print("PASS prevent direct dashboard lookup of unpaid payment attempts")

file.write_text(text, encoding="utf-8")

print("PASS: structured product swatches, backward-compatible Room cache, visual palette, UUID product IDs, and unpaid-order dashboard filter.")
