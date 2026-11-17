from pathlib import Path
import os

PROJECT = Path(os.environ["PROJECT_DIR"]).resolve()


def read(relative: str) -> str:
    path = PROJECT / relative
    if not path.is_file():
        raise SystemExit(f"Missing required source file: {relative}")
    return path.read_text(encoding="utf-8")


def write(relative: str, source: str) -> None:
    path = PROJECT / relative
    path.write_text(source, encoding="utf-8")


# 1) Use the shared compressed WebP uploader for category images.
category_path = "app/src/main/java/com/pinky/dashboard/ui/screens/categories/CategoriesScreen.kt"
category = read(category_path)
if "SupabaseStorageUploader.uploadProductImage" not in category:
    anchor = "val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }"
    if category.count(anchor) != 1:
        raise SystemExit("Category image upload anchor is missing or duplicated")
    anchor_pos = category.index(anchor)
    try_start = category.rfind("                try {", 0, anchor_pos)
    catch_start = category.find("                } catch (e: Exception) {", anchor_pos)
    if try_start < 0 or catch_start < 0:
        raise SystemExit("Could not locate the category image upload try/catch block")
    replacement = '''                try {
                    val uploadedUrl = SupabaseStorageUploader.uploadProductImage(
                        contentResolver = context.contentResolver,
                        uri = uri,
                        productId = category?.id ?: "new-category",
                        label = "category"
                    )
                    imageUrl = uploadedUrl
                    uploadSuccess = true
'''
    category = category[:try_start] + replacement + category[catch_start:]

category = category.replace(
    "import com.pinky.dashboard.data.remote.SupabaseClient\n",
    "",
)
category = category.replace(
    "import okhttp3.MediaType.Companion.toMediaTypeOrNull\n",
    "",
)
if "import com.pinky.dashboard.data.remote.SupabaseStorageUploader\n" not in category:
    import_anchor = "import com.pinky.dashboard.domain.model.Category\n"
    if category.count(import_anchor) != 1:
        raise SystemExit("Category import anchor is missing or duplicated")
    category = category.replace(
        import_anchor,
        "import com.pinky.dashboard.data.remote.SupabaseStorageUploader\n" + import_anchor,
        1,
    )
category = category.replace(
    'Text("صيغة JPG أو PNG", fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)',
    'Text("يتم ضغط الصورة تلقائيًا قبل رفعها", fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)',
)

# Preview the compact embedded JPEG category images without requiring Coil data-URI support.
package_anchor = "package com.pinky.dashboard.ui.screens.categories\n\n"
if "import android.graphics.BitmapFactory\n" not in category:
    if category.count(package_anchor) != 1:
        raise SystemExit("Category package anchor is missing or duplicated")
    category = category.replace(
        package_anchor,
        package_anchor
        + "import android.graphics.BitmapFactory\n"
        + "import android.util.Base64\n"
        + "import androidx.compose.foundation.Image\n"
        + "import androidx.compose.ui.graphics.asImageBitmap\n",
        1,
    )
context_anchor = "    val context = LocalContext.current\n"
bitmap_state = """    val storedImageBitmap = remember(imageUrl) {
        if (imageUrl.startsWith("data:image/") && ";base64," in imageUrl) {
            runCatching {
                val encoded = imageUrl.substringAfter(";base64,")
                val bytes = Base64.decode(encoded, Base64.DEFAULT)
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
            }.getOrNull()
        } else null
    }
"""
if "val storedImageBitmap = remember(imageUrl)" not in category:
    if category.count(context_anchor) != 1:
        raise SystemExit("Category dialog context anchor is missing or duplicated")
    category = category.replace(context_anchor, context_anchor + bitmap_state, 1)
image_block_old = """AsyncImage(
                    model = selectedImageUri ?: imageUrl,
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize()
                )"""
image_block_new = """if (selectedImageUri != null) {
                    AsyncImage(
                        model = selectedImageUri,
                        contentDescription = null,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize()
                    )
                } else if (storedImageBitmap != null) {
                    Image(
                        bitmap = storedImageBitmap,
                        contentDescription = null,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize()
                    )
                } else {
                    AsyncImage(
                        model = imageUrl,
                        contentDescription = null,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize()
                    )
                }"""
if image_block_old in category:
    category = category.replace(image_block_old,image_block_new,1)
elif "storedImageBitmap != null" not in category:
    raise SystemExit("Category image preview block is missing or duplicated")
if "SupabaseStorageUploader.uploadProductImage" not in category or "uploadStorageFile(" in category:
    raise SystemExit("Category image upload did not switch to the shared uploader")
write(category_path, category)
print("PASS: category images use compressed, uniquely named WebP uploads")

# 2) Make the secondary Supabase reads awaited and report failures to the sync UI.
view_model_path = "app/src/main/java/com/pinky/dashboard/ui/PinkyViewModel.kt"
source = read(view_model_path)
function_start = source.find("    private fun syncRemainingSupabaseData() {")
if function_start < 0:
    raise SystemExit("Could not locate syncRemainingSupabaseData()")
open_brace = source.find("{", function_start)
if open_brace < 0:
    raise SystemExit("Could not locate syncRemainingSupabaseData() body")
depth = 0
function_end = -1
for index in range(open_brace, len(source)):
    if source[index] == "{":
        depth += 1
    elif source[index] == "}":
        depth -= 1
        if depth == 0:
            function_end = index + 1
            break
if function_end < 0:
    raise SystemExit("Could not find end of syncRemainingSupabaseData()")
block = source[function_start:function_end]

old_header = "    private fun syncRemainingSupabaseData() {\n        viewModelScope.launch {\n"
new_header = "    private suspend fun syncRemainingSupabaseData(): List<String> {\n        val errors = mutableListOf<String>()\n"
if block.count(old_header) != 1:
    raise SystemExit("Unexpected syncRemainingSupabaseData() wrapper")
block = block.replace(old_header, new_header, 1)

# Surface unsuccessful HTTP responses rather than silently keeping stale dashboard state.
response_checks = [
    (
        "val response = SupabaseClient.service.getCoupons()\n                if (response.isSuccessful) {",
        "val response = SupabaseClient.service.getCoupons()\n                if (!response.isSuccessful) errors.add(\"الكوبونات: HTTP ${response.code()}\")\n                if (response.isSuccessful) {",
    ),
    (
        "val response = SupabaseClient.service.getPrimeSubscriptions()\n                if (response.isSuccessful) {",
        "val response = SupabaseClient.service.getPrimeSubscriptions()\n                if (!response.isSuccessful) errors.add(\"اشتراكات Prime: HTTP ${response.code()}\")\n                if (response.isSuccessful) {",
    ),
    (
        "val response = SupabaseClient.service.getStaffProfiles()\n                if (response.isSuccessful) {",
        "val response = SupabaseClient.service.getStaffProfiles()\n                if (!response.isSuccessful) errors.add(\"الموظفون: HTTP ${response.code()}\")\n                if (response.isSuccessful) {",
    ),
]
for old, new in response_checks:
    if block.count(old) != 1:
        raise SystemExit("Missing or duplicated Supabase read anchor: " + old.splitlines()[0])
    block = block.replace(old, new, 1)

settings_anchor = (
    "val settingsResponse = SupabaseClient.service.getStoreSettings()\n"
    "                val customizationsResponse = SupabaseClient.service.getSiteCustomizations()\n\n"
    "                var currentConfig = _websiteConfig.value"
)
settings_replacement = (
    "val settingsResponse = SupabaseClient.service.getStoreSettings()\n"
    "                val customizationsResponse = SupabaseClient.service.getSiteCustomizations()\n"
    "                if (!settingsResponse.isSuccessful) errors.add(\"إعدادات المتجر: HTTP ${settingsResponse.code()}\")\n"
    "                if (!customizationsResponse.isSuccessful) errors.add(\"تخصيصات الموقع: HTTP ${customizationsResponse.code()}\")\n\n"
    "                var currentConfig = _websiteConfig.value"
)
if block.count(settings_anchor) != 1:
    raise SystemExit("Missing or duplicated store/site settings read anchor")
block = block.replace(settings_anchor, settings_replacement, 1)

# Keep each read independent: a failed section reports its own error and does not cancel the other reads.
catch_sections = [
    ("// Fetch Coupons", "الكوبونات"),
    ("// Fetch Prime Subscriptions", "اشتراكات Prime"),
    ("// Fetch Staff Profiles", "الموظفون"),
    ("// Fetch Store Settings and Site Customizations", "إعدادات الموقع"),
]
for marker, label in catch_sections:
    marker_pos = block.find(marker)
    catch_pos = block.find("e.printStackTrace()", marker_pos + len(marker)) if marker_pos >= 0 else -1
    next_marker_positions = [block.find(next_marker, marker_pos + len(marker)) for next_marker, _ in catch_sections if block.find(next_marker, marker_pos + len(marker)) >= 0]
    next_marker = min(next_marker_positions) if next_marker_positions else len(block)
    if marker_pos < 0 or catch_pos < 0 or catch_pos > next_marker:
        raise SystemExit("Expected Supabase read catch block is missing: " + label)
    replacement = (
        'android.util.Log.e("SupabaseSync", "' + label + ' fetch failed", e)\n'
        '                errors.add(if (isNetworkException(e)) "NETWORK:' + label + '" '
        'else "' + label + ': ${e.message ?: e.javaClass.simpleName}")'
    )
    block = block[:catch_pos] + replacement + block[catch_pos + len("e.printStackTrace()"):]

if not block.endswith("        }\n    }"):
    raise SystemExit("Unexpected end of syncRemainingSupabaseData()")
block = block[:-len("        }\n    }")] + "        return errors\n    }"
if "viewModelScope.launch" in block:
    raise SystemExit("syncRemainingSupabaseData() still launches an unawaited coroutine")

source = source[:function_start] + block + source[function_end:]

old_sync_call = '''                // Sync remaining in-memory states (Coupons, Prime, Staff, Settings, Cust, Devices)
                try {
                    syncRemainingSupabaseData()
                } catch (e: Exception) {
                    android.util.Log.e("SupabaseSync", "Error syncing remaining in-memory data: ${e.message}")
                }

                val errors = mutableListOf<String>()
                var hasNetworkError = false
'''
new_sync_call = '''                val errors = mutableListOf<String>()
                var hasNetworkError = false

                // Wait for all secondary Supabase reads before marking synchronization complete.
                val remainingSyncErrors = syncRemainingSupabaseData()
                remainingSyncErrors.forEach { issue ->
                    if (issue.startsWith("NETWORK:")) {
                        hasNetworkError = true
                    } else {
                        errors.add(issue)
                    }
                }
'''
if source.count(old_sync_call) != 1:
    raise SystemExit("Could not locate centralized sync call site")
source = source.replace(old_sync_call, new_sync_call, 1)

if source.count("private suspend fun syncRemainingSupabaseData(): List<String>") != 1:
    raise SystemExit("Suspend sync function verification failed")
if "val remainingSyncErrors = syncRemainingSupabaseData()" not in source:
    raise SystemExit("Awaited sync call verification failed")
write(view_model_path, source)
print("PASS: secondary Supabase reads are awaited and HTTP/network failures reach syncError")
print("All Supabase sync repair checks passed.")
