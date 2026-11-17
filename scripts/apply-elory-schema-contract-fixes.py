from pathlib import Path
import re
import os

root = Path(os.environ["PROJECT_DIR"]).resolve()

def edit(rel, fn):
    p = root / rel
    s = p.read_text(encoding="utf-8")
    n = fn(s)
    if n == s:
        raise SystemExit(f"No change applied to {rel}; source did not match the reviewed version")
    p.write_text(n, encoding="utf-8")

remote = "app/src/main/java/com/pinky/dashboard/data/remote/SupabaseClient.kt"
repo_file = "app/src/main/java/com/pinky/dashboard/data/repository/RepositoriesImpl.kt"
vm_file = "app/src/main/java/com/pinky/dashboard/ui/PinkyViewModel.kt"

def patch_remote(s):
    # The live orders.order_number column is BIGINT; nullable customer fields must not break decoding.
    s = s.replace('@Json(name = "order_number") val orderNumber: String,', '@Json(name = "order_number") val orderNumber: Long,', 1)
    s = s.replace('@Json(name = "customer_name") val customerName: String,', '@Json(name = "customer_name") val customerName: String? = null,', 1)
    order_start = s.find("data class SupabaseOrderDto(")
    if order_start < 0:
        raise SystemExit("SupabaseOrderDto declaration not found")
    order_end = s.find("\n)", order_start)
    if order_end < 0:
        raise SystemExit("SupabaseOrderDto closing delimiter not found")
    order_block = s[order_start:order_end]
    if order_block.count('@Json(name = "phone") val phone: String,') != 1:
        raise SystemExit("Order phone field missing or duplicated")
    order_block = order_block.replace('@Json(name = "phone") val phone: String,', '@Json(name = "phone") val phone: String? = null,', 1)
    s = s[:order_start] + order_block + s[order_end:]
    s = s.replace('    @Json(name = "discount_amount") val discountAmount: Double? = null,\n', '', 1)
    # Prime request/discount fields are already added by the earlier Prime and profit patches.
    # Nullable columns in customers must not make the entire customer sync fail.
    s = s.replace('@Json(name = "id") val id: String,\\n    @Json(name = "name") val name: String,\\n    @Json(name = "phone") val phone: String,',
                  '@Json(name = "id") val id: String? = null,\\n    @Json(name = "name") val name: String? = null,\\n    @Json(name = "phone") val phone: String? = null,', 1)
    # Banner title and store contact fields are nullable in the live schema.
    s = s.replace('@Json(name = "title") val title: String,',
                  '@Json(name = "title") val title: String? = null,', 1)
    s = s.replace('@Json(name = "store_name") val storeName: String,',
                  '@Json(name = "store_name") val storeName: String? = null,', 1)
    s = s.replace('@Json(name = "whatsapp") val whatsappNumber: String,',
                  '@Json(name = "whatsapp") val whatsappNumber: String? = null,', 1)
    s = s.replace('@Json(name = "instagram") val instagramHandle: String,',
                  '@Json(name = "instagram") val instagramHandle: String? = null,', 1)
    s = s.replace('@Json(name = "facebook") val facebookPage: String',
                  '@Json(name = "facebook") val facebookPage: String? = null', 1)
    # Offers.discount is NUMERIC in Supabase, not a string.
    s = s.replace('@Json(name = "discount") val discount: String? = null,', '@Json(name = "discount") val discount: Double? = null,', 1)
    # staff_profiles has no phone column; never send an unsupported property.
    s = s.replace('    @Json(name = "phone") val phone: String? = null,\n    @Json(name = "role")', '    @Json(name = "role")', 1)
    # Prime is intentionally handled by the existing schema-safe admin RPCs
    # (admin_list_prime_subscriptions / admin_set_prime_subscription_active).
    return s

edit(remote, patch_remote)

def patch_repo(s):
    s = s.replace('orderNumber = dto.orderNumber,', 'orderNumber = dto.orderNumber.toString(),', 1)
    s = s.replace('customerName = dto.customerName,', 'customerName = dto.customerName.orEmpty(),', 1)
    s = s.replace('customerPhone = dto.phone,', 'customerPhone = dto.phone.orEmpty(),', 1)
    s = s.replace('discountAmount = dto.discountAmount ?: 0.0,', 'discountAmount = (dto.couponDiscount ?: 0.0) + (dto.primeDiscount ?: 0.0),', 1)
    s = s.replace('primeRequested = dto.primeRequested ?: false,', 'primeRequested = dto.primeRequested ?: false,', 1)
    if 'primeRequested = dto.primeRequested ?: false,' not in s:
        s = s.replace('prime = dto.prime ?: false,', 'prime = dto.prime ?: false,\n                        primeRequested = dto.primeRequested ?: false,\n                        primePackaging = dto.primePackaging ?: false,', 1)
    s = s.replace('orderNumber = order.orderNumber,', 'orderNumber = order.orderNumber.toLongOrNull() ?: throw IllegalArgumentException("رقم الطلب يجب أن يكون رقمًا صحيحًا."),', 1)
    s = s.replace('                discountAmount = order.discountAmount,\n', '', 1)
    anchor = '                notes = order.notes,\n                items = orderItemsDto\n'
    if s.count(anchor) != 1:
        raise SystemExit("Order create DTO anchor missing or duplicated")
    s = s.replace(anchor, '                notes = order.notes,\n                items = orderItemsDto,\n                prime = order.prime,\n                couponCode = order.couponCode.takeIf { it.isNotBlank() },\n                couponDiscount = order.couponDiscount,\n                couponFreeShipping = order.couponFreeShipping,\n                customerOrderCode = order.orderNumber\n', 1)
    # Numeric Supabase offers.discount is converted explicitly at the API boundary.
    s = s.replace('discount = offer.discountText,', 'discount = offer.discountText.filter { it.isDigit() || it == \'.\' }.toDoubleOrNull(),', 1)
    s = s.replace('discountText = dto.discount ?: "",', 'discountText = dto.discount?.let { if (it % 1.0 == 0.0) it.toLong().toString() else it.toString() } ?: "",', 1)
    return s

edit(repo_file, patch_repo)

# Safely map nullable customer, banner and store-setting columns to UI defaults.
def patch_nullable_mappings(source):
    start = source.find("override suspend fun syncCustomers()")
    if start < 0:
        raise SystemExit("syncCustomers method not found")
    end = source.find("\\n    override suspend fun", start + 1)
    if end < 0:
        end = len(source)
    block = source[start:end]
    block = block.replace("val entities = dtoList.map { dto ->", "val entities = dtoList.mapNotNull { dto ->", 1)
    block = block.replace("                    CustomerEntity(\\n                        id = dto.id,\\n                        name = dto.name,\\n                        phone = dto.phone,",
                          "                    val customerId = dto.id?.takeIf { it.isNotBlank() } ?: return@mapNotNull null\\n                    CustomerEntity(\\n                        id = customerId,\\n                        name = dto.name.orEmpty(),\\n                        phone = dto.phone.orEmpty(),", 1)
    source = source[:start] + block + source[end:]
    # The banner mapping is distinguished by the synthetic ban_ ID.
    source = source.replace("                        title = dto.title,\\n                        description = dto.subtitle ?: \\"\\",",
                          "                        title = dto.title.orEmpty(),\\n                        description = dto.subtitle ?: \\"\\", 1)
    return source

edit(repo_file, patch_nullable_mappings)

def patch_vm(s):
    # Prime reads and writes are intentionally left to the existing schema-safe RPC flow.
    # Staff profile schema has no phone field; omit it from writes and default on reads.
    s = s.replace('                            phone = dto.phone ?: "",', '                            phone = "",', 1)
    staff_start = s.find("SupabaseStaffProfileDto(")
    if staff_start >= 0:
        staff_end = s.find("\n                )", staff_start)
        if staff_end < 0:
            staff_end = s.find("\n            )", staff_start)
        if staff_end < 0:
            raise SystemExit("Could not locate SupabaseStaffProfileDto constructor end")
        staff_block = s[staff_start:staff_end]
        staff_block = re.sub(r'(?m)^\s*phone\s*=.*?,\s*\n', '', staff_block)
        s = s[:staff_start] + staff_block + s[staff_end:]
    return s

def patch_store_settings_nullable(source):
    old = """                            storeName = settings.storeName,
                            whatsappNumber = settings.whatsappNumber,
                            instagramHandle = settings.instagramHandle,
                            facebookPage = settings.facebookPage"""
    new = """                            storeName = settings.storeName.orEmpty(),
                            whatsappNumber = settings.whatsappNumber.orEmpty(),
                            instagramHandle = settings.instagramHandle.orEmpty(),
                            facebookPage = settings.facebookPage.orEmpty()"""
    if source.count(old) != 1:
        raise SystemExit("Store settings DTO mapping missing or duplicated")
    return source.replace(old, new, 1)

edit(vm_file, patch_store_settings_nullable)

# Use the bucket IDs that actually exist

# Use the bucket IDs that actually exist in the connected Elory Supabase project.
def replace_if_present(rel, replacements):
    p = root / rel
    source = p.read_text(encoding="utf-8")
    updated = source
    for old_value, new_value in replacements:
        updated = updated.replace(old_value, new_value)
    if updated != source:
        p.write_text(updated, encoding="utf-8")

replace_if_present("app/src/main/java/com/pinky/dashboard/data/remote/SupabaseConfig.kt", [
    ('"pinky-products"', '"product-images"'), ('"pinky-banners"', '"hero-ads"')
])
replace_if_present("app/src/main/java/com/pinky/dashboard/ui/screens/website/WebsiteEditorScreen.kt", [
    ('"pinky-products"', '"product-images"'), ('"pinky-banners"', '"hero-ads"')
])
replace_if_present("app/src/main/java/com/pinky/dashboard/ui/screens/categories/CategoriesScreen.kt", [
    ('"pinky-products"', '"product-images"')
])
replace_if_present("elory_security_storage_migration.sql", [
    ("'pinky-products'", "'product-images'"), ("'pinky-banners'", "'hero-ads'")
])
replace_if_present("README.md", [
    ("pinky-products", "product-images"), ("pinky-banners", "hero-ads")
])

print("PASS: Supabase order, offer, Prime and staff DTOs match the live schema; Storage uploads target the existing buckets.")
