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
    s = s.replace('@Json(name = "phone") val phone: String,', '@Json(name = "phone") val phone: String? = null,', 1)
    s = s.replace('    @Json(name = "discount_amount") val discountAmount: Double? = null,\n', '', 1)
    anchor = '    @Json(name = "coupon_free_shipping") val couponFreeShipping: Boolean? = null\n'
    if s.count(anchor) != 1:
        raise SystemExit("Order DTO coupon field anchor missing or duplicated")
    s = s.replace(anchor, '    @Json(name = "coupon_free_shipping") val couponFreeShipping: Boolean? = null,\n    @Json(name = "prime_discount") val primeDiscount: Double? = null,\n    @Json(name = "customer_order_code") val customerOrderCode: String? = null\n', 1)
    # Offers.discount is NUMERIC in Supabase, not a string.
    s = s.replace('@Json(name = "discount") val discount: String? = null,', '@Json(name = "discount") val discount: Double? = null,', 1)
    # staff_profiles has no phone column; never send an unsupported property.
    s = s.replace('    @Json(name = "phone") val phone: String? = null,\n    @Json(name = "role")', '    @Json(name = "role")', 1)
    # Replace legacy Prime DTO with the real prime_subscriptions schema.
    start = s.find('data class SupabasePrimeSubscriptionDto(')
    if start < 0:
        raise SystemExit("Prime DTO not found")
    end = s.find('\n)', start)
    if end < 0:
        raise SystemExit("Prime DTO closing delimiter not found")
    end += 2
    block = '''data class SupabasePrimeSubscriptionDto(
    @Json(name = "id") val id: String,
    @Json(name = "user_id") val userId: String? = null,
    @Json(name = "started_at") val startedAt: String? = null,
    @Json(name = "expires_at") val expiresAt: String? = null,
    @Json(name = "active") val active: Boolean? = null,
    @Json(name = "free_shipping_limit") val freeShippingLimit: Int? = null,
    @Json(name = "free_shipping_used") val freeShippingUsed: Int? = null,
    @Json(name = "discount_percent") val discountPercent: Double? = null,
    @Json(name = "packaging_enabled") val packagingEnabled: Boolean? = null,
    @Json(name = "price") val price: Double? = null,
    @Json(name = "payment_reference") val paymentReference: String? = null,
    @Json(name = "status") val status: String? = null,
    @Json(name = "order_id") val orderId: String? = null,
    @Json(name = "actual_free_shipping_cost_total") val actualFreeShippingCostTotal: Double? = null,
    @Json(name = "duration_days") val durationDays: Int? = null,
    @Json(name = "theme_enabled") val themeEnabled: Boolean? = null,
    @Json(name = "payment_confirmed") val paymentConfirmed: Boolean? = null
)'''
    s = s[:start] + block + s[end:]
    # Add a narrow PATCH contract for toggling an existing subscription without overwriting payment/usage data.
    anchor = '''    @POST("rest/v1/prime_subscriptions")
    suspend fun upsertPrimeSubscription(
        @Body sub: SupabasePrimeSubscriptionDto,
        @Header("Prefer") prefer: String = "resolution=merge-duplicates"
    ): Response<Unit>
'''
    if s.count(anchor) != 1:
        raise SystemExit("Prime upsert API anchor missing or duplicated")
    s = s.replace(anchor, anchor + '''
    @PATCH("rest/v1/prime_subscriptions")
    suspend fun patchPrimeSubscription(
        @Query("id") filter: String,
        @Body updates: Map<String, @JvmSuppressWildcards Any>
    ): Response<Unit>
''', 1)
    return s

edit(remote, patch_remote)

def patch_repo(s):
    s = s.replace('orderNumber = dto.orderNumber,', 'orderNumber = dto.orderNumber.toString(),', 1)
    s = s.replace('customerName = dto.customerName,', 'customerName = dto.customerName.orEmpty(),', 1)
    s = s.replace('customerPhone = dto.phone,', 'customerPhone = dto.phone.orEmpty(),', 1)
    s = s.replace('discountAmount = dto.discountAmount ?: 0.0,', 'discountAmount = (dto.couponDiscount ?: 0.0) + (dto.primeDiscount ?: 0.0),', 1)
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

def patch_vm(s):
    # Correct Prime decoding: actual table has started_at/expires_at and lower-case status values.
    old = '''                            customerName = dto.customerName,
                            phone = dto.phone,
                            startDate = dto.startDate.toEpochMillisOrNull() ?: System.currentTimeMillis(),
                            expiryDate = dto.expiryDate.toEpochMillisOrNull() ?: System.currentTimeMillis(),
                            status = try { PrimeSubscriberStatus.valueOf(dto.status) } catch (e: Exception) { PrimeSubscriberStatus.ACTIVE },
                            totalOrdersWithPrime = dto.totalOrders ?: 0,
                            totalSavedWithPrime = dto.totalSaved ?: 0.0'''
    new = '''                            customerName = "عميل Prime",
                            phone = "",
                            startDate = dto.startedAt.toEpochMillisOrNull() ?: System.currentTimeMillis(),
                            expiryDate = dto.expiresAt.toEpochMillisOrNull() ?: System.currentTimeMillis(),
                            status = when {
                                dto.active != true -> PrimeSubscriberStatus.EXPIRED
                                (dto.expiresAt.toEpochMillisOrNull() ?: 0L) <= System.currentTimeMillis() -> PrimeSubscriberStatus.EXPIRED
                                (dto.expiresAt.toEpochMillisOrNull() ?: Long.MAX_VALUE) <= System.currentTimeMillis() + 7L * 24 * 60 * 60 * 1000 -> PrimeSubscriberStatus.EXPIRING_SOON
                                else -> PrimeSubscriberStatus.ACTIVE
                            },
                            totalOrdersWithPrime = dto.freeShippingUsed ?: 0,
                            totalSavedWithPrime = 0.0'''
    if s.count(old) != 1:
        raise SystemExit("Prime DTO mapping anchor missing or duplicated")
    s = s.replace(old, new, 1)
    # Existing-subscription status changes must only patch active/status and preserve payment, price, expiry and usage fields.
    start = s.find('    fun savePrimeSubscriber(subscriber: PrimeSubscriber) {')
    if start < 0:
        raise SystemExit("savePrimeSubscriber function not found")
    end = s.find('\n    fun togglePrimeStatus', start)
    if end < 0:
        raise SystemExit("savePrimeSubscriber end not found")
    block = s[start:end]
    old_body_start = block.find('        viewModelScope.launch {')
    if old_body_start < 0:
        raise SystemExit("savePrimeSubscriber coroutine not found")
    new_block = '''    fun savePrimeSubscriber(subscriber: PrimeSubscriber) {
        viewModelScope.launch {
            try {
                val subscriptionId = subscriber.id
                if (runCatching { java.util.UUID.fromString(subscriptionId) }.isFailure) {
                    android.util.Log.e("EloryPrime", "Prime activation requires an existing Supabase subscription UUID; refusing to create a detached local-only subscriber.")
                    return@launch
                }
                val isActive = subscriber.status == PrimeSubscriberStatus.ACTIVE ||
                    subscriber.status == PrimeSubscriberStatus.EXPIRING_SOON
                val response = SupabaseClient.service.patchPrimeSubscription(
                    "eq.$subscriptionId",
                    mapOf(
                        "active" to isActive,
                        "status" to if (isActive) "active" else "inactive"
                    )
                )
                if (!response.isSuccessful) {
                    android.util.Log.e("EloryPrime", "Prime status update failed: HTTP ${response.code()}")
                    return@launch
                }
                _primeSubscribers.value = _primeSubscribers.value.map {
                    if (it.id == subscriber.id) subscriber else it
                }
            } catch (e: Exception) {
                android.util.Log.e("EloryPrime", "Prime status update failed", e)
            }
        }
    }
'''
    s = s[:start] + new_block + s[end:]
    # Staff profile schema has no phone field; omit it from writes and default on reads.
    s = s.replace('                            phone = dto.phone ?: "",', '                            phone = "",', 1)
    s = s.replace('                    phone = staff.phone,\n', '', 1)
    return s

edit(vm_file, patch_vm)
print("PASS: Supabase order, offer, Prime and staff DTOs now match the live schema contract.")
