#!/usr/bin/env python3
"""Apply deterministic Prime data/status fixes to the Elory Android dashboard."""
from __future__ import annotations
import sys
from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one source match in {path}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply-elory-prime-quality-fixes.py PROJECT_DIR")
    project = Path(sys.argv[1]).resolve()
    if not (project / "settings.gradle.kts").is_file():
        raise SystemExit(f"Invalid Android project directory: {project}")
    java = project / "app/src/main/java/com/pinky/dashboard"

    replace_once(
        java / "data/remote/SupabaseClient.kt",
        '    @Json(name = "order_id") val orderId: String? = null,\n    @Json(name = "customer_name") val customerName: String? = null,',
        '    @Json(name = "order_id") val orderId: String? = null,\n'
        '    @Json(name = "order_number") val orderNumber: String? = null,\n'
        '    @Json(name = "display_status") val displayStatus: String? = null,\n'
        '    @Json(name = "customer_name") val customerName: String? = null,',
        "Prime DTO order linkage",
    )

    replace_once(
        java / "domain/model/StoreModels.kt",
        '''enum class PrimeSubscriberStatus(val arabicLabel: String) {
    ACTIVE("نشط"),
    EXPIRING_SOON("ينتهي قريباً"),
    PENDING("بانتظار التفعيل عند التسليم"),
    EXPIRED("منتهي")
}''',
        '''enum class PrimeSubscriberStatus(val arabicLabel: String) {
    ACTIVE("نشط"),
    EXPIRING_SOON("ينتهي قريباً"),
    PENDING("مطلوب مع أوردر — التفعيل بعد التسليم"),
    PENDING_PAYMENT("بانتظار تأكيد الدفع"),
    INACTIVE("غير نشط"),
    EXPIRED("منتهي")
}''',
        "Prime status types",
    )

    replace_once(
        java / "domain/model/StoreModels.kt",
        '''    val totalSavedWithPrime: Double = 0.0,
    val userId: String? = null,
    val email: String? = null
)''',
        '''    val totalSavedWithPrime: Double = 0.0,
    val userId: String? = null,
    val email: String? = null,
    val orderNumber: String? = null
)''',
        "Prime order number domain field",
    )

    replace_once(
        java / "domain/model/StoreModels.kt",
        '''data class PinkyPrimeSettings(
    val monthlyPrice: Double = 149.0,
    val annualPrice: Double = 1190.0,
    val isServiceActive: Boolean = true,
    val benefits: List<PrimeBenefit> = listOf(
        PrimeBenefit("b1", "شحن مجاني غير محدود", "على جميع الطلبات لأي مكان في مصر بدون حد أدنى"),
        PrimeBenefit("b2", "خصم إضافي 5% حصري", "يطبق تلقائياً على كافة التشكيلات غير المخفضة"),
        PrimeBenefit("b3", "أولوية التجهيز والشحن السريع", "يتم تسليم الطلب خلال 24 ساعة في القاهرة والجيزة"),
        PrimeBenefit("b4", "هدية خاصة مع كل طلب", "عينات وإكسسوارات حصرية مع شحنات المشتركين")
    )
)''',
        '''data class PinkyPrimeSettings(
    val monthlyPrice: Double = 300.0,
    val annualPrice: Double = 3600.0,
    val isServiceActive: Boolean = true,
    val benefits: List<PrimeBenefit> = listOf(
        PrimeBenefit("b1", "شحن مجاني", "حتى 6 طلبات خلال مدة الاشتراك"),
        PrimeBenefit("b2", "خصم إضافي 10%", "على المنتجات المؤهلة وفق شروط الخصم"),
        PrimeBenefit("b3", "تغليف مميز", "تغليف مميز مجاني لأعضاء Elory Prime"),
        PrimeBenefit("b4", "هوية Prime", "مظهر ومزايا Prime الخاصة أثناء الاشتراك")
    )
)''',
        "Legacy Prime defaults alignment",
    )

    replace_once(
        java / "ui/PinkyViewModel.kt",
        '''            val rawStatus = dto.status.orEmpty().lowercase()
            val status = when {
                dto.active == true && expiry > now && expiry <= soon -> PrimeSubscriberStatus.EXPIRING_SOON
                dto.active == true && expiry > now -> PrimeSubscriberStatus.ACTIVE
                rawStatus in setOf("pending", "pending_payment", "awaiting_payment") -> PrimeSubscriberStatus.PENDING
                else -> PrimeSubscriberStatus.EXPIRED
            }''',
        '''            val rawStatus = (dto.displayStatus ?: dto.status).orEmpty().lowercase()
            val isOrderLinked = !dto.orderId.isNullOrBlank()
            val status = when {
                dto.active == true && expiry > now && expiry <= soon -> PrimeSubscriberStatus.EXPIRING_SOON
                dto.active == true && expiry > now -> PrimeSubscriberStatus.ACTIVE
                rawStatus in setOf("pending_delivery", "pending") && isOrderLinked -> PrimeSubscriberStatus.PENDING
                rawStatus in setOf("pending_payment", "pending", "awaiting_payment") -> PrimeSubscriberStatus.PENDING_PAYMENT
                rawStatus in setOf("inactive", "superseded", "cancelled", "canceled", "failed") -> PrimeSubscriberStatus.INACTIVE
                else -> PrimeSubscriberStatus.EXPIRED
            }''',
        "Prime pending-state mapping",
    )

    replace_once(
        java / "ui/PinkyViewModel.kt",
        '''                totalSavedWithPrime = dto.totalSaved ?: 0.0,
                userId = dto.userId,
                email = dto.email
            )''',
        '''                totalSavedWithPrime = dto.totalSaved ?: 0.0,
                userId = dto.userId,
                email = dto.email,
                orderNumber = dto.orderNumber
            )''',
        "Prime subscriber linked order mapping",
    )

    replace_once(
        java / "ui/screens/prime/PrimeScreen.kt",
        '''            it.phone.contains(searchQuery) ||
            (it.email?.contains(searchQuery, ignoreCase = true) == true)''',
        '''            it.phone.contains(searchQuery) ||
            (it.email?.contains(searchQuery, ignoreCase = true) == true) ||
            (it.orderNumber?.contains(searchQuery, ignoreCase = true) == true)''',
        "Prime search includes order number",
    )

    replace_once(
        java / "ui/screens/prime/PrimeScreen.kt",
        '                                subscriber.email?.takeIf { it.isNotBlank() }?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }',
        '''                                subscriber.email?.takeIf { it.isNotBlank() }?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                                    when (subscriber.status) {
                                        PrimeSubscriberStatus.PENDING -> Text(
                                            "طلب Prime مرتبط بالأوردر ${subscriber.orderNumber?.let { "#$it" } ?: ""} — سيتم التفعيل بعد التسليم",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.primary
                                        )
                                        PrimeSubscriberStatus.PENDING_PAYMENT -> Text(
                                            "اشتراك مستقل — بانتظار تأكيد الدفع، وليس طلبًا بانتظار التسليم",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                        else -> subscriber.orderNumber?.takeIf { it.isNotBlank() }?.let {
                                            Text("الأوردر المرتبط: #$it", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        }
                                    }''',
        "Prime card activation context",
    )

    replace_once(
        java / "ui/screens/website/WebsiteEditorScreen.kt",
        '''        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            OutlinedTextField(
                value = config.primePrice.toString(),
                onValueChange = { onUpdate(config.copy(primePrice = it.toDoubleOrNull() ?: 0.0)) },
                label = { Text("سعر الاشتراك الشهري (جنيه)") },
                modifier = Modifier.weight(1f)
            )
            OutlinedTextField(
                value = config.primeDurationDays.toString(),
                onValueChange = { onUpdate(config.copy(primeDurationDays = it.toIntOrNull() ?: 30)) },
                label = { Text("مدة الصلاحية بالأيام") },
                modifier = Modifier.weight(1f)
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            OutlinedTextField(
                value = config.primeDiscountPercent.toString(),
                onValueChange = { onUpdate(config.copy(primeDiscountPercent = it.toDoubleOrNull() ?: 0.0)) },
                label = { Text("نسبة الخصم الإضافية للأعضاء (%)") },
                modifier = Modifier.weight(1f)
            )
            OutlinedTextField(
                value = config.primeFreeShippingOrdersCount.toString(),
                onValueChange = { onUpdate(config.copy(primeFreeShippingOrdersCount = it.toIntOrNull() ?: 4)) },
                label = { Text("عدد مرات الشحن المجاني شهرياً") },
                modifier = Modifier.weight(1f)
            )
        }''',
        '''        Text(
            "قيم الاشتراك مرتبطة مباشرة بنظام الدفع والتفعيل: 300 جنيه لمدة 30 يومًا، خصم 10%، و6 شحنات مجانية. تعديل هذه القيم يحتاج تحديثًا متزامنًا في الباك إند، لذلك تظهر هنا للقراءة فقط حتى لا تختلف المعلومات عن المبلغ الفعلي.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            OutlinedTextField(
                value = "300",
                onValueChange = {},
                readOnly = true,
                label = { Text("سعر الاشتراك الشهري (جنيه)") },
                modifier = Modifier.weight(1f)
            )
            OutlinedTextField(
                value = "30",
                onValueChange = {},
                readOnly = true,
                label = { Text("مدة الصلاحية بالأيام") },
                modifier = Modifier.weight(1f)
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            OutlinedTextField(
                value = "10",
                onValueChange = {},
                readOnly = true,
                label = { Text("نسبة الخصم الإضافية للأعضاء (%)") },
                modifier = Modifier.weight(1f)
            )
            OutlinedTextField(
                value = "6",
                onValueChange = {},
                readOnly = true,
                label = { Text("عدد مرات الشحن المجاني لكل اشتراك") },
                modifier = Modifier.weight(1f)
            )
        }''',
        "Prime pricing editor consistency",
    )

    print("Elory Prime dashboard quality fixes applied.")


if __name__ == "__main__":
    main()
