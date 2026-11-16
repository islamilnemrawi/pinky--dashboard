from __future__ import annotations
import os
from pathlib import Path

PROJECT = Path(os.environ["PROJECT_DIR"]).resolve()

def read(relative: str) -> str:
    path = PROJECT / relative
    if not path.is_file():
        raise SystemExit("Missing required source file: " + relative)
    return path.read_text(encoding="utf-8")

def write(relative: str, source: str) -> None:
    path = PROJECT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")

def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit("Expected one insertion point for " + label + "; found " + str(count))
    return source.replace(old, new, 1)

remote = "app/src/main/java/com/pinky/dashboard/data/remote/SupabaseClient.kt"
source = read(remote)
dto_anchor = "// RETROFIT INTERFACE FOR SUPABASE REST API"
dto_block = r"""
@JsonClass(generateAdapter = true)
data class ProfitDashboardDto(
    @Json(name = "period_days") val periodDays: Int = 90,
    @Json(name = "summary") val summary: ProfitSummaryDto = ProfitSummaryDto(),
    @Json(name = "daily") val daily: List<ProfitDailyDto> = emptyList(),
    @Json(name = "products") val products: List<ProfitProductDto> = emptyList(),
    @Json(name = "governorates") val governorates: List<ProfitGovernorateDto> = emptyList(),
    @Json(name = "prime") val prime: List<PrimeProfitDto> = emptyList()
)
@JsonClass(generateAdapter = true)
data class ProfitSummaryDto(
    @Json(name = "delivered_orders") val deliveredOrders: Int = 0,
    @Json(name = "delivered_sales") val deliveredSales: Double = 0.0,
    @Json(name = "product_gross_margin") val productGrossMargin: Double = 0.0,
    @Json(name = "missing_profit_orders") val missingProfitOrders: Int = 0,
    @Json(name = "open_orders") val openOrders: Int = 0,
    @Json(name = "open_order_value") val openOrderValue: Double = 0.0,
    @Json(name = "open_missing_profit_orders") val openMissingProfitOrders: Int = 0,
    @Json(name = "cancelled_orders") val cancelledOrders: Int = 0,
    @Json(name = "cancelled_order_value") val cancelledOrderValue: Double = 0.0
)
@JsonClass(generateAdapter = true)
data class ProfitDailyDto(
    @Json(name = "day") val day: String = "",
    @Json(name = "delivered_orders") val deliveredOrders: Int = 0,
    @Json(name = "delivered_sales") val deliveredSales: Double = 0.0,
    @Json(name = "product_gross_margin") val productGrossMargin: Double = 0.0,
    @Json(name = "missing_profit_orders") val missingProfitOrders: Int = 0,
    @Json(name = "requested_orders") val requestedOrders: Int = 0
)
@JsonClass(generateAdapter = true)
data class ProfitProductDto(
    @Json(name = "product_key") val productKey: String = "",
    @Json(name = "product_name") val productName: String = "",
    @Json(name = "requested_units") val requestedUnits: Int = 0,
    @Json(name = "delivered_units") val deliveredUnits: Int = 0,
    @Json(name = "open_units") val openUnits: Int = 0,
    @Json(name = "requested_orders") val requestedOrders: Int = 0,
    @Json(name = "delivered_item_sales") val deliveredItemSales: Double = 0.0
)
@JsonClass(generateAdapter = true)
data class ProfitGovernorateDto(
    @Json(name = "governorate") val governorate: String = "",
    @Json(name = "requested_orders") val requestedOrders: Int = 0,
    @Json(name = "delivered_orders") val deliveredOrders: Int = 0,
    @Json(name = "requested_value") val requestedValue: Double = 0.0,
    @Json(name = "delivered_value") val deliveredValue: Double = 0.0
)
@JsonClass(generateAdapter = true)
data class PrimeProfitDto(
    @Json(name = "id") val id: String = "",
    @Json(name = "status") val status: String? = null,
    @Json(name = "active") val active: Boolean = false,
    @Json(name = "started_at") val startedAt: String? = null,
    @Json(name = "expires_at") val expiresAt: String? = null,
    @Json(name = "free_shipping_limit") val freeShippingLimit: Int = 6,
    @Json(name = "discount_percent") val discountPercent: Double = 10.0,
    @Json(name = "membership_price") val membershipPrice: Double = 300.0,
    @Json(name = "order_id") val orderId: String? = null,
    @Json(name = "order_number") val orderNumber: Long? = null,
    @Json(name = "membership_revenue") val membershipRevenue: Double? = null,
    @Json(name = "free_shipping_used") val freeShippingUsed: Int = 0,
    @Json(name = "free_shipping_remaining") val freeShippingRemaining: Int = 6,
    @Json(name = "free_shipping_completed") val freeShippingCompleted: Int = 0,
    @Json(name = "prime_discount_total") val primeDiscountTotal: Double = 0.0,
    @Json(name = "prime_discount_pending") val primeDiscountPending: Double = 0.0,
    @Json(name = "free_shipping_orders") val freeShippingOrders: Int = 0,
    @Json(name = "actual_free_shipping_cost_total") val actualFreeShippingCostTotal: Double? = null,
    @Json(name = "financial_complete") val financialComplete: Boolean = false,
    @Json(name = "prime_profit") val primeProfit: Double? = null
)
"""
source = replace_once(source, dto_anchor, dto_block + "\n" + dto_anchor, "profit DTOs")
api_anchor = "    // COUPONS"
api_block = r"""
    // Financial dashboard: values are calculated on the database from delivered orders.
    @POST("rest/v1/rpc/admin_get_profit_dashboard")
    suspend fun getProfitDashboard(
        @Body params: Map<String, Int>
    ): Response<ProfitDashboardDto>

    @POST("rest/v1/rpc/admin_set_prime_actual_shipping_cost")
    suspend fun setPrimeActualShippingCost(
        @Body params: Map<String, @JvmSuppressWildcards Any>
    ): Response<Map<String, Any>>

"""
source = replace_once(source, api_anchor, api_block + api_anchor, "profit RPC endpoints")
write(remote, source)
print("PASS: profit DTOs and Retrofit RPC endpoints.")

viewmodel = "app/src/main/java/com/pinky/dashboard/ui/PinkyViewModel.kt"
source = read(viewmodel)
state_anchor = """    private val _primeSubscribers = MutableStateFlow<List<PrimeSubscriber>>(emptyList())
    val primeSubscribers: StateFlow<List<PrimeSubscriber>> = _primeSubscribers.asStateFlow()
"""
state_block = r"""
    private val _profitDashboard = MutableStateFlow<ProfitDashboardDto?>(null)
    val profitDashboard: StateFlow<ProfitDashboardDto?> = _profitDashboard.asStateFlow()
    private val _profitDashboardLoading = MutableStateFlow(false)
    val profitDashboardLoading: StateFlow<Boolean> = _profitDashboardLoading.asStateFlow()
    private val _profitDashboardError = MutableStateFlow<String?>(null)
    val profitDashboardError: StateFlow<String?> = _profitDashboardError.asStateFlow()
    private val _profitDashboardDays = MutableStateFlow(90)
    val profitDashboardDays: StateFlow<Int> = _profitDashboardDays.asStateFlow()

"""
source = replace_once(source, state_anchor, state_anchor + state_block, "profit dashboard state")
method_anchor = "    // Staff member management"
methods = r"""
    fun loadProfitDashboard(days: Int = _profitDashboardDays.value) {
        val safeDays = days.coerceIn(1, 3650)
        _profitDashboardDays.value = safeDays
        viewModelScope.launch {
            _profitDashboardLoading.value = true
            _profitDashboardError.value = null
            try {
                val response = SupabaseClient.service.getProfitDashboard(mapOf("p_days" to safeDays))
                if (response.isSuccessful) {
                    _profitDashboard.value = response.body()
                        ?: throw IllegalStateException("استجابة تقرير الأرباح فارغة")
                } else {
                    val details = response.errorBody()?.string().orEmpty()
                    _profitDashboardError.value =
                        "تعذر تحميل تقرير الأرباح (HTTP " + response.code() + "). " + details.take(220)
                }
            } catch (error: Exception) {
                _profitDashboardError.value = error.message ?: "تعذر الاتصال بتقرير الأرباح"
                android.util.Log.e("ProfitDashboard", "Load failed", error)
            } finally {
                _profitDashboardLoading.value = false
            }
        }
    }

    fun savePrimeActualShippingCost(subscriptionId: String, actualCost: Double) {
        if (subscriptionId.isBlank() || !actualCost.isFinite() || actualCost < 0.0) {
            _profitDashboardError.value = "أدخل تكلفة شحن صحيحة لا تقل عن صفر."
            return
        }
        viewModelScope.launch {
            _profitDashboardLoading.value = true
            _profitDashboardError.value = null
            try {
                val response = SupabaseClient.service.setPrimeActualShippingCost(
                    mapOf("p_subscription_id" to subscriptionId, "p_cost" to actualCost)
                )
                if (!response.isSuccessful) {
                    val details = response.errorBody()?.string().orEmpty()
                    _profitDashboardError.value =
                        "تعذر حفظ تكلفة الشحن (HTTP " + response.code() + "). " + details.take(220)
                } else {
                    loadProfitDashboard(_profitDashboardDays.value)
                }
            } catch (error: Exception) {
                _profitDashboardError.value = error.message ?: "تعذر حفظ تكلفة شحن Prime"
                android.util.Log.e("ProfitDashboard", "Prime shipping-cost save failed", error)
            } finally {
                _profitDashboardLoading.value = false
            }
        }
    }

"""
source = replace_once(source, method_anchor, methods + method_anchor, "profit dashboard actions")
write(viewmodel, source)
print("PASS: ViewModel state, report loading, and Prime shipping-cost save.")

app = "app/src/main/java/com/pinky/dashboard/ui/PinkyApp.kt"
source = read(app)
collect_anchor = "    val analytics by viewModel.analytics.collectAsStateWithLifecycle()\n"
collect_block = r"""    val profitDashboard by viewModel.profitDashboard.collectAsStateWithLifecycle()
    val profitDashboardLoading by viewModel.profitDashboardLoading.collectAsStateWithLifecycle()
    val profitDashboardError by viewModel.profitDashboardError.collectAsStateWithLifecycle()
    val profitDashboardDays by viewModel.profitDashboardDays.collectAsStateWithLifecycle()
"""
source = replace_once(source, collect_anchor, collect_anchor + collect_block, "profit state collection")
reports_anchor = """                                    analytics = analytics,
                                    currentUser = currentUser
"""
reports_new = """                                    analytics = analytics,
                                    currentUser = currentUser,
                                    profitDashboard = profitDashboard,
                                    profitDashboardLoading = profitDashboardLoading,
                                    profitDashboardError = profitDashboardError,
                                    profitDashboardDays = profitDashboardDays,
                                    onRefreshProfitDashboard = { viewModel.loadProfitDashboard() },
                                    onProfitDashboardDaysChange = { viewModel.loadProfitDashboard(it) },
                                    onSavePrimeActualShippingCost = { id, cost ->
                                        viewModel.savePrimeActualShippingCost(id, cost)
                                    }
"""
source = replace_once(source, reports_anchor, reports_new, "ReportsScreen profit bindings")
write(app, source)
print("PASS: app connected to the financial dashboard.")

panel = r'''package com.pinky.dashboard.ui.screens.reports

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pinky.dashboard.core.util.Formatters
import com.pinky.dashboard.data.remote.PrimeProfitDto
import com.pinky.dashboard.data.remote.ProfitDashboardDto
import com.pinky.dashboard.data.remote.ProfitDailyDto
import com.pinky.dashboard.data.remote.ProfitGovernorateDto
import com.pinky.dashboard.data.remote.ProfitProductDto
import com.pinky.dashboard.ui.components.PinkyStatCard
import com.pinky.dashboard.ui.theme.PinkPrimary

@Composable
fun ProfitDashboardPanel(
    data: ProfitDashboardDto?,
    loading: Boolean,
    error: String?,
    selectedDays: Int,
    canManagePrime: Boolean,
    onDaysChange: (Int) -> Unit,
    onRefresh: () -> Unit,
    onSavePrimeShippingCost: (String, Double) -> Unit,
    modifier: Modifier = Modifier
) {
    var selectedDay by remember(data?.daily) {
        mutableStateOf(data?.daily?.lastOrNull()?.day)
    }
    Column(modifier = modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text("لوحة الأرباح والتحليل المالي", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                Text("الحسابات من الطلبات المسلّمة والتكاليف المسجلة فقط",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            IconButton(onClick = onRefresh, enabled = !loading) {
                Icon(Icons.Outlined.Refresh, contentDescription = "تحديث التقرير", tint = PinkPrimary)
            }
        }
        Row(
            modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            listOf(7 to "7 أيام", 30 to "30 يوم", 90 to "90 يوم", 365 to "سنة", 3650 to "كل الفترة")
                .forEach { (days, label) ->
                    FilterChip(
                        selected = selectedDays == days,
                        onClick = { if (selectedDays != days) onDaysChange(days) },
                        label = { Text(label) }
                    )
                }
        }
        if (loading && data == null) {
            Box(Modifier.fillMaxWidth().padding(28.dp), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = PinkPrimary)
            }
        }
        if (!error.isNullOrBlank()) {
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                shape = RoundedCornerShape(12.dp)) {
                Text(error, modifier = Modifier.padding(12.dp),
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    style = MaterialTheme.typography.bodySmall)
            }
        }
        if (data == null) {
            if (!loading) OutlinedButton(onClick = onRefresh, modifier = Modifier.fillMaxWidth()) {
                Text("تحميل بيانات الأرباح")
            }
            return@Column
        }

        val summary = data.summary
        Text("ملخص الفترة", fontWeight = FontWeight.Bold, fontSize = 16.sp)
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                PinkyStatCard(
                    title = "مبيعات الطلبات المسلّمة",
                    value = Formatters.formatCurrencyEgp(summary.deliveredSales),
                    subtitle = summary.deliveredOrders.toString() + " طلب تم تسليمه",
                    icon = Icons.Outlined.Payments,
                    modifier = Modifier.weight(1f)
                )
                PinkyStatCard(
                    title = "هامش ربح المنتجات",
                    value = Formatters.formatCurrencyEgp(summary.productGrossMargin),
                    subtitle = "بعد خصومات الطلبات وقبل مصاريف التشغيل",
                    icon = Icons.Outlined.TrendingUp,
                    modifier = Modifier.weight(1f)
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                PinkyStatCard(
                    title = "طلبات قيد التنفيذ",
                    value = summary.openOrders.toString(),
                    subtitle = "قيمة معلّقة: " + Formatters.formatCurrencyEgp(summary.openOrderValue),
                    icon = Icons.Outlined.PendingActions,
                    modifier = Modifier.weight(1f)
                )
                PinkyStatCard(
                    title = "طلبات ملغاة",
                    value = summary.cancelledOrders.toString(),
                    subtitle = "قيمة ملغاة: " + Formatters.formatCurrencyEgp(summary.cancelledOrderValue),
                    icon = Icons.Outlined.Cancel,
                    modifier = Modifier.weight(1f)
                )
            }
        }
        Text(
            "هامش ربح المنتجات ليس صافي ربح المتجر؛ فهو لا يشمل تكلفة الشحن الفعلية أو التغليف أو رسوم الدفع أو المصاريف التشغيلية.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        if (summary.missingProfitOrders > 0) {
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                shape = RoundedCornerShape(12.dp)) {
                Text(
                    "تنبيه: " + summary.missingProfitOrders.toString() + " طلبًا مسلّمًا بلا تكلفة منتج مكتملة. لم يتم تقدير أرباحها أو اعتبارها صفرًا.",
                    modifier = Modifier.padding(12.dp),
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    style = MaterialTheme.typography.bodySmall,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }

        if (summary.openMissingProfitOrders > 0) {
            Text(
                "ملاحظة: هامش الربح لم يُسجّل بعد لـ " + summary.openMissingProfitOrders +
                    " طلب مفتوح. لن يدخل ضمن الأرباح المحققة قبل التسليم واكتمال تكلفة المنتجات.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        SectionCard(title = "الأرباح حسب اليوم") {
            if (data.daily.isEmpty()) {
                EmptyLine("لا توجد طلبات في الفترة المحددة.")
            } else {
                data.daily.forEach { metric ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(metric.day, fontWeight = FontWeight.SemiBold)
                            Text(
                                metric.deliveredOrders.toString() + " طلب مسلّم • " +
                                    metric.requestedOrders + " طلب غير ملغى",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text(
                                Formatters.formatCurrencyEgp(metric.productGrossMargin),
                                fontWeight = FontWeight.Bold,
                                color = PinkPrimary
                            )
                            Text(
                                metric.missingProfitOrders.toString() + " هامش ناقص",
                                style = MaterialTheme.typography.labelSmall,
                                color = if (metric.missingProfitOrders > 0)
                                    MaterialTheme.colorScheme.error
                                else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                    Divider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
                }
                Text(
                    "اضغط على اليوم لعرض تفاصيله:",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Row(modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    data.daily.forEach { day ->
                        FilterChip(selected = selectedDay == day.day,
                            onClick = { selectedDay = day.day },
                            label = { Text(day.day) })
                    }
                }
                val day = data.daily.firstOrNull { it.day == selectedDay } ?: data.daily.last()
                DailyProfitDetails(day)
            }
        }

        SectionCard(title = "أكثر المنتجات طلبًا") {
            if (data.products.isEmpty()) EmptyLine("لا توجد منتجات مسجلة في هذه الفترة.")
            else {
                Text("الترتيب حسب عدد القطع المطلوبة من الطلبات غير الملغاة، مع فصل المسلّم عن المفتوح.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                data.products.forEachIndexed { index, product -> ProductDemandRow(index + 1, product) }
            }
        }

        SectionCard(title = "أكثر المحافظات طلبًا") {
            if (data.governorates.isEmpty()) EmptyLine("لا توجد بيانات محافظات في الفترة المحددة.")
            else data.governorates.forEachIndexed { index, governorate ->
                GovernorateDemandRow(index + 1, governorate)
            }
        }

        SectionCard(title = "ربحية اشتراكات Elory Prime") {
            Text(
                "المعادلة: إيراد الاشتراك المثبت − خصم Prime المستخدم في الطلبات المسلّمة − تكلفة الشحن المجاني الفعلية. لا يتم افتراض استهلاك الشحنات الست.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            if (data.prime.isEmpty()) EmptyLine("لا توجد اشتراكات Prime مسجلة.")
            else {
                val complete = data.prime.filter { it.financialComplete && it.primeProfit != null }
                val incomplete = data.prime.size - complete.size
                val netKnown = complete.sumOf { it.primeProfit ?: 0.0 }
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    PinkyStatCard(
                        title = "نتيجة الاشتراكات المكتملة",
                        value = Formatters.formatCurrencyEgp(netKnown),
                        subtitle = complete.size.toString() + " اشتراك بحساب مكتمل",
                        icon = Icons.Outlined.WorkspacePremium,
                        modifier = Modifier.weight(1f)
                    )
                    PinkyStatCard(
                        title = "بيانات غير مكتملة",
                        value = incomplete.toString(),
                        subtitle = "لا تدخل في مجموع الربح",
                        icon = Icons.Outlined.Info,
                        modifier = Modifier.weight(1f)
                    )
                }
                data.prime.forEach { row -> PrimeProfitRow(row, canManagePrime, onSavePrimeShippingCost) }
            }
        }
    }
}

@Composable
private fun SectionCard(title: String, content: @Composable ColumnScope.() -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder()
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(title, fontWeight = FontWeight.Bold, fontSize = 15.sp)
            content()
        }
    }
}

@Composable
private fun DailyProfitDetails(day: ProfitDailyDto) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text("تفاصيل يوم " + day.day, fontWeight = FontWeight.SemiBold)
        DetailLine("طلبات تم تسليمها", day.deliveredOrders.toString())
        DetailLine("قيمة الطلبات المسلّمة", Formatters.formatCurrencyEgp(day.deliveredSales))
        DetailLine("هامش ربح المنتجات", Formatters.formatCurrencyEgp(day.productGrossMargin))
        DetailLine("طلبات بيانات ربحها ناقصة", day.missingProfitOrders.toString())
        DetailLine("طلبات غير ملغاة تم تسجيلها", day.requestedOrders.toString())
        if (day.missingProfitOrders > 0) {
            Text("الرقم المعروض لا يتضمن هامش الطلبات الناقصة.",
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun ProductDemandRow(index: Int, product: ProfitProductDto) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f)) {
                Text(index.toString() + ". " + product.productName, fontWeight = FontWeight.SemiBold)
                Text(product.requestedOrders.toString() + " طلب • " + product.requestedUnits + " قطعة مطلوبة",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(product.deliveredUnits.toString() + " مسلّمة", fontWeight = FontWeight.Bold, color = PinkPrimary)
                Text(product.openUnits.toString() + " مفتوحة", style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Divider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
    }
}

@Composable
private fun GovernorateDemandRow(index: Int, governorate: ProfitGovernorateDto) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f)) {
                Text(index.toString() + ". " + governorate.governorate, fontWeight = FontWeight.SemiBold)
                Text(governorate.requestedOrders.toString() + " طلب • " + governorate.deliveredOrders + " مسلّم",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Text(Formatters.formatCurrencyEgp(governorate.requestedValue),
                color = PinkPrimary, fontWeight = FontWeight.Bold)
        }
        Divider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
    }
}

@Composable
private fun PrimeProfitRow(
    row: PrimeProfitDto,
    canManagePrime: Boolean,
    onSavePrimeShippingCost: (String, Double) -> Unit
) {
    var shippingCostText by remember(row.id, row.actualFreeShippingCostTotal) {
        mutableStateOf(row.actualFreeShippingCostTotal?.toString().orEmpty())
    }
    val parsedCost = shippingCostText.trim().toDoubleOrNull()
    val statusLabel = when (row.status?.lowercase()) {
        "active" -> "نشط"
        "expired" -> "منتهي"
        "inactive" -> "غير نشط"
        "superseded" -> "استبدل باشتراك أحدث"
        "pending" -> "بانتظار التسليم"
        "failed" -> "فشل"
        "cancelled" -> "ملغي"
        else -> row.status ?: "غير محدد"
    }
    Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.25f)),
        border = CardDefaults.outlinedCardBorder()) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f)) {
                    val identifier = row.orderNumber?.let { "#" + it } ?: row.id.take(8)
                    Text("اشتراك " + identifier, fontWeight = FontWeight.Bold)
                    Text(statusLabel, style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Text(
                    if (row.financialComplete && row.primeProfit != null) {
                        if (row.primeProfit >= 0) "ربح" else "خسارة"
                    } else "غير مكتمل",
                    color = if (row.financialComplete && row.primeProfit != null && row.primeProfit < 0)
                        MaterialTheme.colorScheme.error else PinkPrimary,
                    fontWeight = FontWeight.Bold
                )
            }
            DetailLine("سعر العضوية", Formatters.formatCurrencyEgp(row.membershipPrice))
            DetailLine("إيراد عضوية مثبت",
                row.membershipRevenue?.let { Formatters.formatCurrencyEgp(it) } ?: "غير مثبت")
            DetailLine("نسبة الخصم", row.discountPercent.toString() + "%")
            DetailLine("خصومات Prime المنفذة", Formatters.formatCurrencyEgp(row.primeDiscountTotal))
            if (row.primeDiscountPending > 0.0) {
                DetailLine("خصومات على طلبات لم تُسلّم", Formatters.formatCurrencyEgp(row.primeDiscountPending))
            }
            DetailLine("الشحن المجاني المستهلك",
                row.freeShippingUsed.toString() + " من " + row.freeShippingLimit + " • المتبقي " + row.freeShippingRemaining)
            DetailLine("شحنات مجانية تم تسليمها", row.freeShippingCompleted.toString())
            if (row.actualFreeShippingCostTotal != null) {
                DetailLine("التكلفة الفعلية للشحن المجاني",
                    Formatters.formatCurrencyEgp(row.actualFreeShippingCostTotal))
            } else if (row.freeShippingCompleted > 0) {
                Text("أدخل إجمالي تكلفة الشحن الفعلية للشحنات المجانية التي تم تسليمها.",
                    color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
            } else {
                DetailLine("تكلفة الشحن المجاني", "لا توجد شحنات مجانية مسلّمة بعد")
            }
            if (row.financialComplete && row.primeProfit != null) {
                DetailLine("نتيجة الاشتراك", Formatters.formatCurrencyEgp(row.primeProfit))
            } else {
                Text("لا يمكن تثبيت ربح أو خسارة هذا الاشتراك قبل اكتمال إيراد العضوية وتكلفة الشحن المطلوبة.",
                    color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
            }
            if (canManagePrime && (row.freeShippingCompleted > 0 || row.actualFreeShippingCostTotal != null)) {
                OutlinedTextField(
                    value = shippingCostText,
                    onValueChange = { shippingCostText = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text("إجمالي تكلفة الشحن الفعلية (ج.م)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    shape = RoundedCornerShape(10.dp)
                )
                Button(
                    onClick = { parsedCost?.let { onSavePrimeShippingCost(row.id, it) } },
                    enabled = parsedCost != null && parsedCost >= 0.0,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = PinkPrimary)
                ) { Text("حفظ تكلفة الشحن وإعادة الحساب") }
            }
        }
    }
}

@Composable
private fun DetailLine(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically) {
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun EmptyLine(text: String) {
    Text(text, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
}
'''
write("app/src/main/java/com/pinky/dashboard/ui/screens/reports/ProfitDashboardPanel.kt", panel)

reports = "app/src/main/java/com/pinky/dashboard/ui/screens/reports/ReportsScreen.kt"
source = read(reports)
source = replace_once(source,
    "import com.pinky.dashboard.core.util.Formatters\n",
    "import com.pinky.dashboard.core.util.Formatters\nimport com.pinky.dashboard.data.remote.ProfitDashboardDto\n",
    "profit DTO import")
signature_anchor = """    analytics: AnalyticsData,
    currentUser: AdminUser?,
    modifier: Modifier = Modifier
"""
signature_new = """    analytics: AnalyticsData,
    currentUser: AdminUser?,
    profitDashboard: ProfitDashboardDto? = null,
    profitDashboardLoading: Boolean = false,
    profitDashboardError: String? = null,
    profitDashboardDays: Int = 90,
    onRefreshProfitDashboard: () -> Unit = {},
    onProfitDashboardDaysChange: (Int) -> Unit = {},
    onSavePrimeActualShippingCost: (String, Double) -> Unit = { _, _ -> },
    modifier: Modifier = Modifier
"""
source = replace_once(source, signature_anchor, signature_new, "ReportsScreen signature")
start = source.find("                if (selectedReportType == 0) {")
end = source.find("                } else if (selectedReportType == 1) {", start + 1)
if start < 0 or end < 0:
    raise SystemExit("Could not locate financial report branch in ReportsScreen.")
new_branch = """                if (selectedReportType == 0) {
                    item {
                        if (currentUser?.canViewProfit == true) {
                            ProfitDashboardPanel(
                                data = profitDashboard,
                                loading = profitDashboardLoading,
                                error = profitDashboardError,
                                selectedDays = profitDashboardDays,
                                canManagePrime = currentUser.hasPermission(Permission.MANAGE_PRIME),
                                onDaysChange = onProfitDashboardDaysChange,
                                onRefresh = onRefreshProfitDashboard,
                                onSavePrimeShippingCost = onSavePrimeActualShippingCost
                            )
                        } else {
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(16.dp),
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                border = CardDefaults.outlinedCardBorder()
                            ) {
                                Column(
                                    modifier = Modifier.fillMaxWidth().padding(24.dp),
                                    horizontalAlignment = Alignment.CenterHorizontally,
                                    verticalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    Icon(Icons.Outlined.Lock, contentDescription = null, tint = PinkPrimary, modifier = Modifier.size(48.dp))
                                    Text("تقارير الأرباح وهوامش التكلفة محجوبة", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                                    Text("تحتاج هذه البيانات إلى صلاحية مشاهدة الأرباح.",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                    }
"""
source = source[:start] + new_branch + source[end:]
effect_anchor = "    var showExportToast by remember { mutableStateOf(false) }\n"
source = replace_once(source, effect_anchor,
    effect_anchor + "\n    LaunchedEffect(selectedReportType, currentUser?.canViewProfit) {\n        if (selectedReportType == 0 && currentUser?.canViewProfit == true) onRefreshProfitDashboard()\n    }\n",
    "profit dashboard refresh effect")
write(reports, source)
print("PASS: the financial tab now uses the structured profit dashboard.")

checks = {
    "DTO and endpoint": (remote, ("admin_get_profit_dashboard", "ProfitDashboardDto", "admin_set_prime_actual_shipping_cost")),
    "ViewModel actions": (viewmodel, ("loadProfitDashboard", "savePrimeActualShippingCost", "_profitDashboard")),
    "app state bindings": (app, ("profitDashboard = profitDashboard", "onSavePrimeActualShippingCost")),
    "financial tab integration": (reports, ("ProfitDashboardPanel(", "onProfitDashboardDaysChange")),
    "Prime cost editor": ("app/src/main/java/com/pinky/dashboard/ui/screens/reports/ProfitDashboardPanel.kt",
                          ("onSavePrimeShippingCost", "primeDiscountTotal", "freeShippingRemaining"))
}
for label, (relative, needles) in checks.items():
    text = read(relative)
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit("Verification failed for " + label + ": " + str(missing))
    print("PASS: " + label)
print("Elory profit dashboard patch completed.")
