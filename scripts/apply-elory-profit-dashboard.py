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
    @Json(name = "open_missing_profit_orders") val openMissingProfitOrders: Int = 0,
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
method_anchor = state_anchor + state_block
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
source = replace_once(source, method_anchor, method_anchor + methods, "profit dashboard actions")
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

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.clip
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
                    icon = Icons.Outlined.MonetizationOn,
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
                    icon = Icons.Outlined.Inventory2,
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
                    val selected = selectedDay == metric.day
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(10.dp))
                            .background(
                                if (selected) PinkPrimary.copy(alpha = 0.10f)
                                else MaterialTheme.colorScheme.surface
                            )
                            .clickable { selectedDay = metric.day }
                            .padding(horizontal = 10.dp, vertical = 12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(metric.day, fontWeight = FontWeight.SemiBold)
                            Text(
                                metric.deliveredOrders.toString() + " مسلّم • " +
                                    (metric.requestedOrders - metric.deliveredOrders).coerceAtLeast(0) + " مفتوح",
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
                                metric.missingProfitOrders.toString() + " مسلّم بلا هامش",
                                style = MaterialTheme.typography.labelSmall,
                                color = if (metric.missingProfitOrders > 0)
                                    MaterialTheme.colorScheme.error
                                else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                metric.openMissingProfitOrders.toString() + " مفتوح بلا هامش",
                                style = MaterialTheme.typography.labelSmall,
                                color = if (metric.openMissingProfitOrders > 0)
                                    MaterialTheme.colorScheme.error
                                else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                    Divider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
                }
                val day = data.daily.firstOrNull { it.day == selectedDay } ?: data.daily.last()
                DailyProfitDetails(day)
            }
        }

        SectionCard(title = "أعلى 10 منتجات طلبًا") {
            if (data.products.isEmpty()) EmptyLine("لا توجد منتجات مسجلة في هذه الفترة.")
            else {
                Text("نعرض أعلى 10 منتجات فقط، مرتبة حسب عدد القطع المطلوبة، مع فصل المسلّم عن المفتوح.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                data.products.forEachIndexed { index, product -> ProductDemandRow(index + 1, product) }
            }
        }

        SectionCard(title = "أعلى 10 محافظات طلبًا") {
            if (data.governorates.isEmpty()) EmptyLine("لا توجد بيانات محافظات في الفترة المحددة.")
            else {
                Text("نعرض أعلى 10 محافظات فقط، مرتبة حسب عدد الطلبات، مع قيمة الطلبات وعدد الطلبات المسلّمة.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                data.governorates.forEachIndexed { index, governorate ->
                    GovernorateDemandRow(index + 1, governorate)
                }
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
                        icon = Icons.Outlined.Star,
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
        DetailLine("طلبات مسلّمة هامشها ناقص", day.missingProfitOrders.toString())
        DetailLine("طلبات مفتوحة هامشها ناقص", day.openMissingProfitOrders.toString())
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
            DetailLine("شحنات مجانية أُرسلت/سُلّمت", row.freeShippingUsed.toString())
            DetailLine("منها تم تسليمها", row.freeShippingCompleted.toString())
            if (row.actualFreeShippingCostTotal != null) {
                DetailLine("إجمالي تكلفة الشحن الفعلية",
                    Formatters.formatCurrencyEgp(row.actualFreeShippingCostTotal))
            } else if (row.freeShippingUsed > 0) {
                Text("أدخل إجمالي تكلفة الشحن الفعلية للشحنات المجانية التي تم إرسالها أو تسليمها.",
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
            if (canManagePrime && (row.freeShippingUsed > 0 || row.actualFreeShippingCostTotal != null)) {
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

def panel_replace_once(old: str, new: str, label: str) -> None:
    global panel
    count = panel.count(old)
    if count != 1:
        raise SystemExit("Expected one panel insertion point for " + label + "; found " + str(count))
    panel = panel.replace(old, new, 1)

panel_replace_once(
    """import androidx.compose.ui.unit.sp
""",
    """import androidx.compose.ui.unit.sp
import androidx.compose.ui.graphics.vector.ImageVector
""",
    "report tile icon import"
)
panel_replace_once(
    """    var selectedDay by remember(data?.daily) {
        mutableStateOf(data?.daily?.lastOrNull()?.day)
    }
""",
    """    var selectedDay by remember(data?.daily) {
        mutableStateOf(data?.daily?.lastOrNull()?.day)
    }
    var selectedSection by remember { mutableIntStateOf(0) }
""",
    "selected report section state"
)

summary_start = panel.find('        Text("ملخص الفترة", fontWeight = FontWeight.Bold, fontSize = 16.sp)')
daily_start = panel.find('        SectionCard(title = "الأرباح حسب اليوم")', summary_start)
if summary_start < 0 or daily_start < 0:
    raise SystemExit("Could not isolate the existing financial summary block.")
summary_block = panel[summary_start:daily_start]
panel = panel[:summary_start] + panel[daily_start:]

tile_grid = """        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            ReportSectionTile(
                title = "الأرباح اليومية",
                subtitle = "تفاصيل الربح حسب اليوم",
                icon = Icons.Outlined.DateRange,
                selected = selectedSection == 0,
                onClick = { selectedSection = 0 },
                modifier = Modifier.weight(1f)
            )
            ReportSectionTile(
                title = "أكثر المنتجات",
                subtitle = "أعلى 10 منتجات طلبًا",
                icon = Icons.Outlined.Inventory2,
                selected = selectedSection == 1,
                onClick = { selectedSection = 1 },
                modifier = Modifier.weight(1f)
            )
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            ReportSectionTile(
                title = "أعلى المحافظات",
                subtitle = "أعلى 10 محافظات طلبًا",
                icon = Icons.Outlined.LocationOn,
                selected = selectedSection == 2,
                onClick = { selectedSection = 2 },
                modifier = Modifier.weight(1f)
            )
            ReportSectionTile(
                title = "Elory Prime",
                subtitle = "ربح وخسارة الاشتراكات",
                icon = Icons.Outlined.Star,
                selected = selectedSection == 3,
                onClick = { selectedSection = 3 },
                modifier = Modifier.weight(1f)
            )
        }
"""
panel_replace_once(
    """        val summary = data.summary
""",
    """        val summary = data.summary
""" + tile_grid,
    "four report selector cards"
)
summary_indented = "".join(("    " + line if line.strip() else line) for line in summary_block.splitlines(keepends=True))
panel_replace_once(
    """        SectionCard(title = "الأرباح حسب اليوم") {
""",
    """        if (selectedSection == 0) {
""" + summary_indented + """            SectionCard(title = "الأرباح حسب اليوم") {
""",
    "daily report conditional"
)
panel_replace_once(
    """        SectionCard(title = "أعلى 10 منتجات طلبًا") {
""",
    """        }
        if (selectedSection == 1) {
            SectionCard(title = "أعلى 10 منتجات طلبًا") {
""",
    "product report conditional"
)
panel_replace_once(
    """        SectionCard(title = "أعلى 10 محافظات طلبًا") {
""",
    """        }
        if (selectedSection == 2) {
            SectionCard(title = "أعلى 10 محافظات طلبًا") {
""",
    "governorate report conditional"
)
panel_replace_once(
    """        SectionCard(title = "ربحية اشتراكات Elory Prime") {
""",
    """        }
        if (selectedSection == 3) {
            SectionCard(title = "ربحية اشتراكات Elory Prime") {
""",
    "Prime report conditional"
)
panel_replace_once(
    """        }
    }
}

@Composable
private fun SectionCard""",
    """            }
        }
    }
}

@Composable
private fun ReportSectionTile(
    title: String,
    subtitle: String,
    icon: ImageVector,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.clickable(onClick = onClick),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (selected) PinkPrimary.copy(alpha = 0.12f)
            else MaterialTheme.colorScheme.surface
        ),
        border = CardDefaults.outlinedCardBorder()
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().heightIn(min = 96.dp).padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(5.dp)
        ) {
            Icon(icon, contentDescription = null, tint = PinkPrimary, modifier = Modifier.size(22.dp))
            Text(title, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall, maxLines = 1)
            Text(
                subtitle,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2
            )
        }
    }
}

@Composable
private fun SectionCard""",
    "close single report content and add selector tile"
)


def panel_replace_once(old: str, new: str, label: str) -> None:
    global panel
    count = panel.count(old)
    if count != 1:
        raise SystemExit("Expected one panel insertion point for " + label + "; found " + str(count))
    panel = panel.replace(old, new, 1)

panel_replace_once(
    """import androidx.compose.ui.unit.sp
""",
    """import androidx.compose.ui.unit.sp
import androidx.compose.ui.graphics.vector.ImageVector
""",
    "report tile icon import"
)
panel_replace_once(
    """    var selectedDay by remember(data?.daily) {
        mutableStateOf(data?.daily?.lastOrNull()?.day)
    }
""",
    """    var selectedDay by remember(data?.daily) {
        mutableStateOf(data?.daily?.lastOrNull()?.day)
    }
    var selectedSection by remember { mutableIntStateOf(0) }
""",
    "selected report section state"
)

summary_start = panel.find('        Text("ملخص الفترة", fontWeight = FontWeight.Bold, fontSize = 16.sp)')
daily_start = panel.find('        SectionCard(title = "الأرباح حسب اليوم")', summary_start)
if summary_start < 0 or daily_start < 0:
    raise SystemExit("Could not isolate the existing financial summary block.")
summary_block = panel[summary_start:daily_start]
panel = panel[:summary_start] + panel[daily_start:]

tile_grid = """        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            ReportSectionTile(
                title = "الأرباح اليومية",
                subtitle = "تفاصيل الربح حسب اليوم",
                icon = Icons.Outlined.DateRange,
                selected = selectedSection == 0,
                onClick = { selectedSection = 0 },
                modifier = Modifier.weight(1f)
            )
            ReportSectionTile(
                title = "أكثر المنتجات",
                subtitle = "أعلى 10 منتجات طلبًا",
                icon = Icons.Outlined.Inventory2,
                selected = selectedSection == 1,
                onClick = { selectedSection = 1 },
                modifier = Modifier.weight(1f)
            )
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            ReportSectionTile(
                title = "أعلى المحافظات",
                subtitle = "أعلى 10 محافظات طلبًا",
                icon = Icons.Outlined.LocationOn,
                selected = selectedSection == 2,
                onClick = { selectedSection = 2 },
                modifier = Modifier.weight(1f)
            )
            ReportSectionTile(
                title = "Elory Prime",
                subtitle = "ربح وخسارة الاشتراكات",
                icon = Icons.Outlined.Star,
                selected = selectedSection == 3,
                onClick = { selectedSection = 3 },
                modifier = Modifier.weight(1f)
            )
        }
"""
panel_replace_once(
    """        val summary = data.summary
""",
    """        val summary = data.summary
""" + tile_grid,
    "four report selector cards"
)
summary_indented = "".join(("    " + line if line.strip() else line) for line in summary_block.splitlines(keepends=True))
panel_replace_once(
    """        SectionCard(title = "الأرباح حسب اليوم") {
""",
    """        if (selectedSection == 0) {
""" + summary_indented + """            SectionCard(title = "الأرباح حسب اليوم") {
""",
    "daily report conditional"
)
panel_replace_once(
    """        SectionCard(title = "أعلى 10 منتجات طلبًا") {
""",
    """        }
        if (selectedSection == 1) {
            SectionCard(title = "أعلى 10 منتجات طلبًا") {
""",
    "product report conditional"
)
panel_replace_once(
    """        SectionCard(title = "أعلى 10 محافظات طلبًا") {
""",
    """        }
        if (selectedSection == 2) {
            SectionCard(title = "أعلى 10 محافظات طلبًا") {
""",
    "governorate report conditional"
)
panel_replace_once(
    """        SectionCard(title = "ربحية اشتراكات Elory Prime") {
""",
    """        }
        if (selectedSection == 3) {
            SectionCard(title = "ربحية اشتراكات Elory Prime") {
""",
    "Prime report conditional"
)
panel_replace_once(
    """        }
    }
}

@Composable
private fun SectionCard""",
    """            }
        }
    }
}

@Composable
private fun ReportSectionTile(
    title: String,
    subtitle: String,
    icon: ImageVector,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.clickable(onClick = onClick),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (selected) PinkPrimary.copy(alpha = 0.12f)
            else MaterialTheme.colorScheme.surface
        ),
        border = CardDefaults.outlinedCardBorder()
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().heightIn(min = 96.dp).padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(5.dp)
        ) {
            Icon(icon, contentDescription = null, tint = PinkPrimary, modifier = Modifier.size(22.dp))
            Text(title, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall, maxLines = 1)
            Text(
                subtitle,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2
            )
        }
    }
}

@Composable
private fun SectionCard""",
    "close single report content and add selector tile"
)

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

# Reports is intentionally financial-only. Inventory and delivery operations live
# in their dedicated product and shipping screens below.
source = read(reports)
source = replace_once(
    source,
    'text = "التقارير المالية والتشغيلية",',
    'text = "التقارير والأرباح",',
    "financial-only reports title"
)
source = replace_once(
    source,
    'text = "تحليلات الأرباح، أداء الشحن، حركة المخزون، وحساب هوامش الربح التقديرية",',
    'text = "أربعة تقارير مالية واضحة: الأرباح اليومية، المنتجات، المحافظات، وربحية Elory Prime.",',
    "financial-only reports subtitle"
)
source = replace_once(
    source,
    '    var selectedReportType by remember { mutableIntStateOf(0) } // 0 = Financial/Profit, 1 = Products/Inventory, 2 = Shipping\n',
    '',
    "remove legacy report category state"
)
tab_start = source.find("            // Report Sub-Tabs\n")
lazy_start = source.find("            LazyColumn(", tab_start)
if tab_start < 0 or lazy_start < 0:
    raise SystemExit("Could not locate the reports tab row for removal.")
source = source[:tab_start] + source[lazy_start:]

branch_start = source.find("                if (selectedReportType == 0) {")
branch_end = source.find("\n            }\n        )", branch_start)
if branch_start < 0 or branch_end < 0:
    raise SystemExit("Could not locate the entire legacy inventory/shipping report block.")
financial_only = """                item {
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
                                Text(
                                    "تحتاج هذه البيانات إلى صلاحية مشاهدة الأرباح.",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }"""
source = source[:branch_start] + financial_only + source[branch_end:]

source = replace_once(
    source,
    """    LaunchedEffect(selectedReportType, currentUser?.canViewProfit) {
        if (selectedReportType == 0 && currentUser?.canViewProfit == true) onRefreshProfitDashboard()
    }
""",
    """    LaunchedEffect(currentUser?.canViewProfit) {
        if (currentUser?.canViewProfit == true) onRefreshProfitDashboard()
    }
""",
    "financial dashboard refresh without legacy tabs"
)
write(reports, source)
print("PASS: reports page contains only the four selectable financial reports.")

# Move the inventory overview into the dedicated Products screen.
products_screen = "app/src/main/java/com/pinky/dashboard/ui/screens/products/ProductsScreen.kt"
source = read(products_screen)
products_anchor = """        ) {
            // Header: Search, Bulk Mode, Import Excel
"""
products_block = """        ) {
            if (products.isNotEmpty()) {
                val totalStockUnits = products.sumOf { it.stock.coerceAtLeast(0) }
                val lowStockCount = products.count { it.stock in 1..5 }
                val outOfStockCount = products.count { it.stock <= 0 }
                Card(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    border = CardDefaults.outlinedCardBorder()
                ) {
                    Column(
                        modifier = Modifier.fillMaxWidth().padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text("ملخص المخزون", fontWeight = FontWeight.Bold)
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text("عدد الأصناف", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text(products.size.toString(), fontWeight = FontWeight.Bold)
                            }
                            Column(Modifier.weight(1f)) {
                                Text("إجمالي القطع", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text(totalStockUnits.toString(), fontWeight = FontWeight.Bold)
                            }
                            Column(Modifier.weight(1f)) {
                                Text("منخفض / نافد", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text("$lowStockCount / $outOfStockCount", fontWeight = FontWeight.Bold,
                                    color = if (outOfStockCount > 0) StatusCancelled else MaterialTheme.colorScheme.onSurface)
                            }
                        }
                    }
                }
            }
            // Header: Search, Bulk Mode, Import Excel
"""
source = replace_once(source, products_anchor, products_block, "ProductsScreen inventory overview")
write(products_screen, source)
print("PASS: inventory overview moved into Products screen.")

# Move delivery performance into the existing shipping/governorates screen.
shipping_screen = "app/src/main/java/com/pinky/dashboard/ui/screens/shipping/ShippingScreen.kt"
source = read(shipping_screen)
source = replace_once(
    source,
    "import com.pinky.dashboard.domain.model.ShippingGovernorate\n",
    "import com.pinky.dashboard.domain.model.ShippingGovernorate\nimport com.pinky.dashboard.domain.model.Order\nimport com.pinky.dashboard.domain.model.OrderStatus\n",
    "shipping order model imports"
)
source = replace_once(
    source,
    "    shippingCenters: List<ShippingCenter>,\n",
    "    shippingCenters: List<ShippingCenter>,\n    orders: List<Order>,\n",
    "ShippingScreen orders input"
)
shipping_header_anchor = """                        Text(
                            text = "تعديل وإضافة أسعار شحن المحافظات ومندوبين التوصيل لكل المراكز الفرعية التابعة لها.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(16.dp))
"""
shipping_performance = """                        Text(
                            text = "تعديل وإضافة أسعار شحن المحافظات ومندوبين التوصيل لكل المراكز الفرعية التابعة لها.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        val dispatchedOrders = remember(orders) {
                            orders.count { it.status == OrderStatus.SHIPPED || it.status == OrderStatus.DELIVERED }
                        }
                        val deliveredCount = remember(orders) {
                            orders.count { it.status == OrderStatus.DELIVERED }
                        }
                        val inTransitCount = (dispatchedOrders - deliveredCount).coerceAtLeast(0)
                        val deliveryRate = if (dispatchedOrders > 0) deliveredCount * 100 / dispatchedOrders else null
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(14.dp),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                            border = CardDefaults.outlinedCardBorder()
                        ) {
                            Column(
                                modifier = Modifier.fillMaxWidth().padding(12.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Text("كفاءة الشحن والتوصيل", fontWeight = FontWeight.Bold)
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    Column(Modifier.weight(1f)) {
                                        Text("شحنات خرجت", style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        Text(dispatchedOrders.toString(), fontWeight = FontWeight.Bold)
                                    }
                                    Column(Modifier.weight(1f)) {
                                        Text("تم تسليمها", style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        Text(deliveredCount.toString(), fontWeight = FontWeight.Bold)
                                    }
                                    Column(Modifier.weight(1f)) {
                                        Text("قيد التوصيل", style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        Text(inTransitCount.toString(), fontWeight = FontWeight.Bold)
                                    }
                                    Column(Modifier.weight(1f)) {
                                        Text("معدل التسليم", style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        Text(deliveryRate?.let { "$it%" } ?: "—", fontWeight = FontWeight.Bold,
                                            color = PinkPrimary)
                                    }
                                }
                                if (dispatchedOrders == 0) {
                                    Text("لا توجد شحنات خرجت للتوصيل خلال البيانات المتاحة بعد.",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                        Spacer(modifier = Modifier.height(16.dp))
"""
source = replace_once(source, shipping_header_anchor, shipping_performance, "ShippingScreen delivery performance summary")
write(shipping_screen, source)
print("PASS: delivery performance moved into Shipping screen.")

# Pass live order statuses to the shipping screen; no order data is changed.
pinky_app = "app/src/main/java/com/pinky/dashboard/ui/PinkyApp.kt"
source = read(pinky_app)
source = replace_once(
    source,
    """                                ShippingScreen(
                                    governorates = governorates,
                                    shippingCenters = shippingCenters,
""",
    """                                ShippingScreen(
                                    governorates = governorates,
                                    shippingCenters = shippingCenters,
                                    orders = orders,
""",
    "PinkyApp ShippingScreen orders binding"
)
write(pinky_app, source)
print("PASS: Shipping screen receives the existing order list.")


checks = {
    "DTO and endpoint": (remote, ("admin_get_profit_dashboard", "ProfitDashboardDto", "admin_set_prime_actual_shipping_cost")),
    "ViewModel actions": (viewmodel, ("loadProfitDashboard", "savePrimeActualShippingCost", "_profitDashboard")),
    "app state bindings": (app, ("profitDashboard = profitDashboard", "onSavePrimeActualShippingCost")),
    "financial tab integration": (reports, ("ProfitDashboardPanel(", "onProfitDashboardDaysChange", "التقارير والأرباح")),
    "inventory report relocation": ("app/src/main/java/com/pinky/dashboard/ui/screens/products/ProductsScreen.kt", ("ملخص المخزون", "إجمالي القطع", "منخفض / نافد")),
    "delivery report relocation": ("app/src/main/java/com/pinky/dashboard/ui/screens/shipping/ShippingScreen.kt", ("كفاءة الشحن والتوصيل", "معدل التسليم", "orders: List<Order>")),
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
