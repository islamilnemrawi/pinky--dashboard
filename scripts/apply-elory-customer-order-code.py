from __future__ import annotations

import os
import re
import shutil
import zipfile
from pathlib import Path

PROJECT = Path(os.environ["PROJECT_DIR"]).resolve()
SCRIPT_DIR = Path(__file__).resolve().parent
RESOURCE_ROOT = (PROJECT / "app/src/main/res").resolve()


def replace_once(relative: str, old: str, new: str, label: str) -> None:
    path = PROJECT / relative
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count == 0 and new in source:
        print(f"Already applied: {label}")
        return
    if count != 1:
        raise SystemExit(
            f"Refusing partial/ambiguous feature edit ({label}): expected 1 anchor, found {count}."
        )
    path.write_text(source.replace(old, new, 1), encoding="utf-8")
    print(f"Applied: {label}")


# Install the supplied high-resolution Elory icon and Android adaptive resources.
icon_file = SCRIPT_DIR / "elory-dashboard-icon.webp"
if not icon_file.is_file() or icon_file.stat().st_size < 1000:
    raise SystemExit("The reviewed Elory launcher image is missing or incomplete.")

mipmap_root = RESOURCE_ROOT / "mipmap-nodpi"
drawable_root = RESOURCE_ROOT / "drawable"
adaptive_root = RESOURCE_ROOT / "mipmap-anydpi-v26"
mipmap_root.mkdir(parents=True, exist_ok=True)
drawable_root.mkdir(parents=True, exist_ok=True)
adaptive_root.mkdir(parents=True, exist_ok=True)
shutil.copy2(icon_file, mipmap_root / "ic_launcher.webp")
shutil.copy2(icon_file, mipmap_root / "ic_launcher_round.webp")

(drawable_root / "ic_launcher_foreground.xml").write_text(
    '<?xml version="1.0" encoding="utf-8"?>\\n'
    '<bitmap xmlns:android="http://schemas.android.com/apk/res/android"\\n'
    '    android:src="@mipmap/ic_launcher"\\n'
    '    android:gravity="center" />\\n',
    encoding="utf-8",
)
(drawable_root / "ic_launcher_background.xml").write_text(
    '<?xml version="1.0" encoding="utf-8"?>\\n'
    '<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">\\n'
    '    <solid android:color="#EB0063" />\\n'
    '</shape>\\n',
    encoding="utf-8",
)
adaptive_icon = (
    '<?xml version="1.0" encoding="utf-8"?>\\n'
    '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\\n'
    '    <background android:drawable="@drawable/ic_launcher_background" />\\n'
    '    <foreground android:drawable="@drawable/ic_launcher_foreground" />\\n'
    '</adaptive-icon>\\n'
)
(adaptive_root / "ic_launcher.xml").write_text(adaptive_icon, encoding="utf-8")
(adaptive_root / "ic_launcher_round.xml").write_text(adaptive_icon, encoding="utf-8")

required_icons = (
    mipmap_root / "ic_launcher.webp",
    mipmap_root / "ic_launcher_round.webp",
    drawable_root / "ic_launcher_foreground.xml",
    drawable_root / "ic_launcher_background.xml",
    adaptive_root / "ic_launcher.xml",
    adaptive_root / "ic_launcher_round.xml",
)
if any(not path.is_file() or path.stat().st_size == 0 for path in required_icons):
    raise SystemExit("Elory launcher resources were not installed completely.")

manifest = PROJECT / "app/src/main/AndroidManifest.xml"
manifest_text = manifest.read_text(encoding="utf-8")
manifest_text, round_icon_count = re.subn(
    r'android:roundIcon="@mipmap/[^"]+"',
    'android:roundIcon="@mipmap/ic_launcher_round"',
    manifest_text,
    count=1,
)
if round_icon_count != 1:
    raise SystemExit("Could not configure the Android round launcher icon.")
manifest.write_text(manifest_text, encoding="utf-8")
print("Installed and verified the new Elory adaptive + round launcher artwork.")

# Customer-facing code is an additional, immutable reference; orderNumber stays internal.
replace_once(
    "app/src/main/java/com/pinky/dashboard/domain/model/Order.kt",
    '    val couponFreeShipping: Boolean = false\n)',
    '    val couponFreeShipping: Boolean = false,\n    val customerOrderCode: String = ""\n)',
    "add customer code to domain model",
)

replace_once(
    "app/src/main/java/com/pinky/dashboard/data/remote/SupabaseClient.kt",
    '    @Json(name = "coupon_free_shipping") val couponFreeShipping: Boolean? = null\n)',
    '    @Json(name = "coupon_free_shipping") val couponFreeShipping: Boolean? = null,\n'
    '    @Json(name = "customer_order_code") val customerOrderCode: String? = null\n)',
    "read customer order code from Supabase",
)

replace_once(
    "app/src/main/java/com/pinky/dashboard/data/local/entity/Entities.kt",
    "import androidx.room.Entity\n",
    "import androidx.room.ColumnInfo\nimport androidx.room.Entity\n",
    "import Room column default annotation",
)
replace_once(
    "app/src/main/java/com/pinky/dashboard/data/local/entity/Entities.kt",
    '    val couponFreeShipping: Boolean = false\n)',
    '    val couponFreeShipping: Boolean = false,\n'
    '    @ColumnInfo(defaultValue = "\'\'") val customerOrderCode: String = ""\n)',
    "add customer code to cached order entity",
)

replace_once(
    "app/src/main/java/com/pinky/dashboard/data/local/PinkyDatabase.kt",
    "import androidx.room.RoomDatabase\n",
    "import androidx.room.RoomDatabase\nimport androidx.room.migration.Migration\n",
    "import Room migration API",
)
replace_once(
    "app/src/main/java/com/pinky/dashboard/data/local/PinkyDatabase.kt",
    "    version = 3,",
    "    version = 4,",
    "increment Room schema version",
)
replace_once(
    "app/src/main/java/com/pinky/dashboard/data/local/PinkyDatabase.kt",
    "        @Volatile\n        private var INSTANCE: PinkyDatabase? = null",
    '        private val MIGRATION_3_4 = object : Migration(3, 4) {\n'
    '            override fun migrate(db: SupportSQLiteDatabase) {\n'
    '                db.execSQL("ALTER TABLE orders ADD COLUMN customerOrderCode TEXT NOT NULL DEFAULT \'\'")\n'
    '            }\n'
    '        }\n\n'
    '        @Volatile\n'
    '        private var INSTANCE: PinkyDatabase? = null',
    "add non-destructive Room 3-to-4 migration",
)
replace_once(
    "app/src/main/java/com/pinky/dashboard/data/local/PinkyDatabase.kt",
    "                .fallbackToDestructiveMigration()",
    "                .addMigrations(MIGRATION_3_4)\n                .fallbackToDestructiveMigration()",
    "register safe Room migration",
)

# Preserve the code in both local-entity -> domain-model repository paths.
repository_path = PROJECT / "app/src/main/java/com/pinky/dashboard/data/repository/RepositoriesImpl.kt"
repository_source = repository_path.read_text(encoding="utf-8")
pattern = r'(?m)^(\s*)couponFreeShipping = entity\.couponFreeShipping$'
repository_source, mapping_count = re.subn(
    pattern,
    lambda match: (
        match.group(1) + "couponFreeShipping = entity.couponFreeShipping,\n"
        + match.group(1) + "customerOrderCode = entity.customerOrderCode"
    ),
    repository_source,
)
if mapping_count != 2:
    raise SystemExit(f"Expected exactly two entity-to-domain order mappings, found {mapping_count}.")
repository_path.write_text(repository_source, encoding="utf-8")
print("Applied: preserve customer code in both cached-order read paths.")

replace_once(
    "app/src/main/java/com/pinky/dashboard/data/repository/RepositoriesImpl.kt",
    "                        orderNumber = dto.orderNumber,\n",
    "                        orderNumber = dto.orderNumber,\n"
    "                        customerOrderCode = dto.customerOrderCode.orEmpty(),\n",
    "sync Supabase customer code into Room",
)
replace_once(
    "app/src/main/java/com/pinky/dashboard/data/repository/RepositoriesImpl.kt",
    "                orderNumber = order.orderNumber,\n",
    "                orderNumber = order.orderNumber,\n"
    "                customerOrderCode = order.customerOrderCode,\n",
    "preserve customer code for local order creation",
)

replace_once(
    "app/src/main/java/com/pinky/dashboard/ui/screens/orders/OrdersScreen.kt",
    "                order.orderNumber.contains(searchQuery, ignoreCase = true) ||\n",
    "                order.orderNumber.contains(searchQuery, ignoreCase = true) ||\n"
    "                order.customerOrderCode.contains(searchQuery, ignoreCase = true) ||\n",
    "search order screen by customer code",
)
replace_once(
    "app/src/main/java/com/pinky/dashboard/ui/screens/orders/OrdersScreen.kt",
    '                placeholder = { Text("بحث برقم الطلب، اسم العميل، أو رقم الهاتف...") },',
    '                placeholder = { Text("بحث برمز العميل، الرقم التسلسلي، الاسم أو الهاتف...") },',
    "clarify customer code search",
)
replace_once(
    "app/src/main/java/com/pinky/dashboard/ui/screens/orders/OrdersScreen.kt",
    '                    Text(\n'
    '                        text = "#${order.orderNumber}",\n'
    '                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),\n'
    '                        color = PinkPrimary\n'
    '                    )\n'
    '                    Text(\n'
    '                        text = Formatters.formatOrderDate(order.createdAt),',
    '                    Text(\n'
    '                        text = "#${order.orderNumber}",\n'
    '                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),\n'
    '                        color = PinkPrimary\n'
    '                    )\n'
    '                    if (order.customerOrderCode.isNotBlank()) {\n'
    '                        Text(\n'
    '                            text = "رمز العميل: ${order.customerOrderCode}",\n'
    '                            style = MaterialTheme.typography.bodySmall,\n'
    '                            color = MaterialTheme.colorScheme.onSurfaceVariant\n'
    '                        )\n'
    '                    }\n'
    '                    Text(\n'
    '                        text = Formatters.formatOrderDate(order.createdAt),',
    "show customer code beside internal serial",
)

replace_once(
    "app/src/main/java/com/pinky/dashboard/ui/screens/orders/OrderDetailDialog.kt",
    '                        Text(\n'
    '                            text = Formatters.formatOrderDate(order.createdAt),\n'
    '                            style = MaterialTheme.typography.bodySmall,\n'
    '                            color = MaterialTheme.colorScheme.onSurfaceVariant\n'
    '                        )',
    '                        Text(\n'
    '                            text = Formatters.formatOrderDate(order.createdAt),\n'
    '                            style = MaterialTheme.typography.bodySmall,\n'
    '                            color = MaterialTheme.colorScheme.onSurfaceVariant\n'
    '                        )\n'
    '                        if (order.customerOrderCode.isNotBlank()) {\n'
    '                            Text(\n'
    '                                text = "رمز العميل: ${order.customerOrderCode}",\n'
    '                                style = MaterialTheme.typography.bodySmall,\n'
    '                                color = MaterialTheme.colorScheme.onSurfaceVariant\n'
    '                            )\n'
    '                        }',
    "show customer code in order detail",
)

replace_once(
    "app/src/main/java/com/pinky/dashboard/ui/components/GlobalSearchDialog.kt",
    "            it.orderNumber.contains(searchQuery, ignoreCase = true) ||\n",
    "            it.orderNumber.contains(searchQuery, ignoreCase = true) ||\n"
    "            it.customerOrderCode.contains(searchQuery, ignoreCase = true) ||\n",
    "global search by customer order code",
)
replace_once(
    "app/src/main/java/com/pinky/dashboard/ui/components/GlobalSearchDialog.kt",
    '                    placeholder = { Text("ابحث برقم الطلب، اسم العميل، المنتج، الكوبون أو القسم...") },',
    '                    placeholder = { Text("ابحث برمز الطلب، رقمه الداخلي، العميل، المنتج أو الكوبون...") },',
    "clarify global search includes order code",
)
replace_once(
    "app/src/main/java/com/pinky/dashboard/ui/components/GlobalSearchDialog.kt",
    '                                    title = "${order.orderNumber} - ${order.customerName}",',
    '                                    title = "${order.customerOrderCode.ifBlank { "بدون رمز" }} • #${order.orderNumber} - ${order.customerName}",',
    "show customer code and internal serial in global results",
)

required_markers = {
    "app/src/main/java/com/pinky/dashboard/domain/model/Order.kt": "customerOrderCode",
    "app/src/main/java/com/pinky/dashboard/data/local/entity/Entities.kt": "customerOrderCode",
    "app/src/main/java/com/pinky/dashboard/data/local/PinkyDatabase.kt": "MIGRATION_3_4",
    "app/src/main/java/com/pinky/dashboard/data/remote/SupabaseClient.kt": "customer_order_code",
    "app/src/main/java/com/pinky/dashboard/data/repository/RepositoriesImpl.kt": "dto.customerOrderCode.orEmpty()",
    "app/src/main/java/com/pinky/dashboard/ui/screens/orders/OrdersScreen.kt": "order.customerOrderCode.contains",
    "app/src/main/java/com/pinky/dashboard/ui/screens/orders/OrderDetailDialog.kt": "رمز العميل:",
    "app/src/main/java/com/pinky/dashboard/ui/components/GlobalSearchDialog.kt": "it.customerOrderCode.contains",
}
for relative, marker in required_markers.items():
    if marker not in (PROJECT / relative).read_text(encoding="utf-8"):
        raise SystemExit("Customer order code integration check failed in " + relative)

database_source = (PROJECT / "app/src/main/java/com/pinky/dashboard/data/local/PinkyDatabase.kt").read_text(encoding="utf-8")
if "version = 4" not in database_source or ".addMigrations(MIGRATION_3_4)" not in database_source:
    raise SystemExit("Room 3-to-4 migration is not registered.")
print("PASS: customer code DTO/cache/search/detail and non-destructive Room migration are installed.")
