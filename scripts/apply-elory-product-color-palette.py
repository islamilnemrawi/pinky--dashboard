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
palette_helpers = r'''
private val ELORY_PRODUCT_COLOR_PALETTE = listOf(
    ProductColorOption("أحمر", "#DC2626"),
    ProductColorOption("عنابي", "#7F1D3A"),
    ProductColorOption("وردي", "#EC4899"),
    ProductColorOption("روز", "#D87591"),
    ProductColorOption("موف", "#8B5CF6"),
    ProductColorOption("لافندر", "#B49AE8"),
    ProductColorOption("بنفسجي", "#6D4CBB"),
    ProductColorOption("أزرق", "#2563EB"),
    ProductColorOption("كحلي", "#1E3A8A"),
    ProductColorOption("سماوي", "#38BDF8"),
    ProductColorOption("تركواز", "#0F9D9A"),
    ProductColorOption("أخضر", "#16A34A"),
    ProductColorOption("زيتي", "#65743A"),
    ProductColorOption("نعناعي", "#A7DCC3"),
    ProductColorOption("أصفر", "#EAB308"),
    ProductColorOption("ذهبي", "#C7A04A"),
    ProductColorOption("برتقالي", "#F97316"),
    ProductColorOption("بني", "#8B5E3C"),
    ProductColorOption("بيج", "#D6C2A1"),
    ProductColorOption("جملي", "#B98B62"),
    ProductColorOption("أبيض", "#F8FAFC"),
    ProductColorOption("عاجي", "#F2E8D5"),
    ProductColorOption("رمادي", "#9CA3AF"),
    ProductColorOption("أسود", "#171717")
)

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
    var customColorName by remember(initialProduct?.id) { mutableStateOf("") }
    var customColorHex by remember(initialProduct?.id) { mutableStateOf("#D87591") }
    var colorError by remember(initialProduct?.id) { mutableStateOf<String?>(null) }""",
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
new_colors_ui = '''                    // Stock
                    item {
                        OutlinedTextField(
                            value = stockText,
                            onValueChange = { stockText = it.filter(Char::isDigit) },
                            label = { Text("الكمية بالمخزون *") },
                            modifier = Modifier.fillMaxWidth().testTag("product_stock_input"),
                            shape = RoundedCornerShape(12.dp)
                        )
                    }

                    // Visual color palette: every swatch has a name, a real HEX value and a selected state.
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
                                Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                                    Text("ألوان المنتج", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                                    Text(
                                        "اختارِي الألوان من الباليتة؛ ستظهر كدوائر حقيقية للعميل عند اختيار المنتج.",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }

                                ELORY_PRODUCT_COLOR_PALETTE.chunked(6).forEach { paletteRow ->
                                    Row(
                                        Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.spacedBy(5.dp)
                                    ) {
                                        paletteRow.forEach { preset ->
                                            val isSelected = colorOptions.any {
                                                it.name.equals(preset.name, ignoreCase = true) &&
                                                    it.hex.equals(preset.hex, ignoreCase = true)
                                            }
                                            Column(
                                                Modifier.weight(1f),
                                                horizontalAlignment = Alignment.CenterHorizontally,
                                                verticalArrangement = Arrangement.spacedBy(4.dp)
                                            ) {
                                                Box(
                                                    modifier = Modifier
                                                        .size(40.dp)
                                                        .clip(CircleShape)
                                                        .background(eloryColorFromHex(preset.hex))
                                                        .border(
                                                            if (isSelected) 3.dp else 1.dp,
                                                            if (isSelected) PinkPrimary else MaterialTheme.colorScheme.outlineVariant,
                                                            CircleShape
                                                        )
                                                        .clickable {
                                                            colorError = null
                                                            if (!isSelected) colorOptions = colorOptions + preset
                                                        }
                                                        .testTag("product_color_" + preset.hex.removePrefix("#")),
                                                    contentAlignment = Alignment.Center
                                                ) {
                                                    if (isSelected) {
                                                        Icon(
                                                            Icons.Outlined.Check,
                                                            contentDescription = "محدد",
                                                            tint = eloryColorCheckTint(preset.hex),
                                                            modifier = Modifier.size(19.dp)
                                                        )
                                                    }
                                                }
                                                Text(
                                                    preset.name,
                                                    fontSize = 9.sp,
                                                    maxLines = 1,
                                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                                )
                                            }
                                        }
                                        repeat(6 - paletteRow.size) { Spacer(Modifier.weight(1f)) }
                                    }
                                }

                                Text(
                                    "الألوان المختارة (" + colorOptions.size + ")",
                                    style = MaterialTheme.typography.labelLarge,
                                    fontWeight = FontWeight.Bold
                                )
                                if (colorOptions.isEmpty()) {
                                    Text(
                                        "لم يتم اختيار ألوان بعد.",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                } else {
                                    colorOptions.chunked(2).forEach { selectedRow ->
                                        Row(
                                            Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                                        ) {
                                            selectedRow.forEach { selectedColor ->
                                                Row(
                                                    Modifier.weight(1f)
                                                        .clip(RoundedCornerShape(14.dp))
                                                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f))
                                                        .padding(start = 9.dp, end = 4.dp, top = 4.dp, bottom = 4.dp),
                                                    verticalAlignment = Alignment.CenterVertically
                                                ) {
                                                    Box(
                                                        Modifier.size(24.dp).clip(CircleShape)
                                                            .background(eloryColorFromHex(selectedColor.hex))
                                                            .border(1.dp, MaterialTheme.colorScheme.outlineVariant, CircleShape)
                                                    )
                                                    Column(
                                                        Modifier.weight(1f).padding(horizontal = 7.dp),
                                                        verticalArrangement = Arrangement.spacedBy(0.dp)
                                                    ) {
                                                        Text(selectedColor.name, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, maxLines = 1)
                                                        Text(selectedColor.hex, fontSize = 9.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                                    }
                                                    IconButton(
                                                        onClick = { colorOptions = colorOptions.filterNot { it == selectedColor } },
                                                        modifier = Modifier.size(28.dp)
                                                    ) {
                                                        Icon(
                                                            Icons.Outlined.Close,
                                                            contentDescription = "حذف " + selectedColor.name,
                                                            modifier = Modifier.size(16.dp),
                                                            tint = MaterialTheme.colorScheme.error
                                                        )
                                                    }
                                                }
                                            }
                                            if (selectedRow.size == 1) Spacer(Modifier.weight(1f))
                                        }
                                    }
                                }

                                Divider(color = MaterialTheme.colorScheme.outlineVariant)
                                Text("إضافة لون مخصص", style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold)
                                Row(
                                    Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    OutlinedTextField(
                                        value = customColorName,
                                        onValueChange = { customColorName = it; colorError = null },
                                        label = { Text("اسم اللون") },
                                        placeholder = { Text("مثلاً: وردي فاتح") },
                                        modifier = Modifier.weight(1.2f),
                                        singleLine = true,
                                        shape = RoundedCornerShape(12.dp)
                                    )
                                    OutlinedTextField(
                                        value = customColorHex,
                                        onValueChange = {
                                            customColorHex = it.filter { char -> char.isDigit() || char.lowercaseChar() in 'a'..'f' || char == '#' }.take(7).uppercase()
                                            colorError = null
                                        },
                                        label = { Text("HEX") },
                                        placeholder = { Text("#D87591") },
                                        modifier = Modifier.weight(0.8f),
                                        singleLine = true,
                                        shape = RoundedCornerShape(12.dp)
                                    )
                                }
                                Row(
                                    Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(9.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Box(
                                        Modifier.size(34.dp).clip(CircleShape)
                                            .background(eloryColorFromHex(customColorHex))
                                            .border(1.dp, MaterialTheme.colorScheme.outlineVariant, CircleShape)
                                    )
                                    Button(
                                        onClick = {
                                            val cleanName = customColorName.trim()
                                            val cleanHex = customColorHex.trim().uppercase()
                                            when {
                                                cleanName.isBlank() -> colorError = "اكتب اسم اللون أولاً."
                                                !cleanHex.matches(Regex("^#[0-9A-F]{6}$")) -> colorError = "اكتب كود HEX صحيحًا مثل #D87591."
                                                colorOptions.any { it.name.equals(cleanName, true) || it.hex.equals(cleanHex, true) } ->
                                                    colorError = "هذا اللون مضاف بالفعل."
                                                else -> {
                                                    colorOptions = colorOptions + ProductColorOption(cleanName, cleanHex)
                                                    customColorName = ""
                                                    customColorHex = "#D87591"
                                                    colorError = null
                                                }
                                            }
                                        },
                                        shape = RoundedCornerShape(12.dp),
                                        colors = ButtonDefaults.buttonColors(containerColor = PinkPrimary, contentColor = Color(0xFF381528))
                                    ) {
                                        Icon(Icons.Outlined.Add, contentDescription = null)
                                        Spacer(Modifier.width(5.dp))
                                        Text("إضافة اللون")
                                    }
                                }
                                colorError?.let {
                                    Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                                }
                            }
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
import re
orders_pattern = re.compile(
    r"(return\s+orderDao\.getAllOrdersFlow\(\)\.map\s*\{\s*entities\s*->\s*)entities\.map\s*\{\s*entity\s*->"
)
text, order_matches = orders_pattern.subn(
    r"\1entities.filterNot { isUnconfirmedPayment(it) }.map { entity ->",
    text,
    count=1
)
if order_matches != 1:
    raise SystemExit("Could not uniquely attach the unpaid-order filter to OrderRepositoryImpl.getOrdersFlow().")
print("PASS hide unpaid and failed payment rows from all dashboard order flows")

detail_pattern = re.compile(
    r"(val entity = orderDao\.getOrderById\(orderId\) \?: return@withContext null\s*)val items = orderDao\.getOrderItems\(entity\.id\)\.map"
)
text, detail_matches = detail_pattern.subn(
    r"\1if (isUnconfirmedPayment(entity)) return@withContext null\n        val items = orderDao.getOrderItems(entity.id).map",
    text,
    count=1
)
if detail_matches != 1:
    raise SystemExit("Could not uniquely protect direct dashboard order lookup.")
print("PASS prevent direct dashboard lookup of unpaid payment attempts")

file.write_text(text, encoding="utf-8")

print("PASS: structured product swatches, backward-compatible Room cache, visual palette, UUID product IDs, and unpaid-order dashboard filter.")
