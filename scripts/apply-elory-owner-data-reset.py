#!/usr/bin/env python3
"""Apply the owner-only PIN data reset flow to the extracted Elory Android project."""
from pathlib import Path
import os, re

ROOT = Path(os.environ.get("PROJECT_DIR", "")).resolve()
if not ROOT.is_dir():
    raise SystemExit("PROJECT_DIR is missing or is not a directory")
SRC = ROOT / "app/src/main/java"
PKG = SRC / "com/pinky/dashboard"
DAO_FILE = PKG / "data/local/dao/Daos.kt"
REPO_FILE = PKG / "data/repository/RepositoriesImpl.kt"
VM_FILE = PKG / "ui/PinkyViewModel.kt"
API_FILE = PKG / "data/remote/SupabaseClient.kt"
APP_FILE = PKG / "ui/PinkyApp.kt"

def read(path):
    if not path.exists():
        raise RuntimeError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")

def write(path, value):
    path.write_text(value, encoding="utf-8")

def matching_end(text, start, left="{", right="}"):
    depth, i, state, quote = 0, start, "normal", ""
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if state == "line":
            if ch == "\n": state = "normal"
        elif state == "block":
            if ch == "*" and nxt == "/": state = "normal"; i += 1
        elif state == "string":
            if ch == "\\": i += 1
            elif ch == quote: state = "normal"
        else:
            if ch == "/" and nxt == "/": state = "line"; i += 1
            elif ch == "/" and nxt == "*": state = "block"; i += 1
            elif ch in ('"', "'"): state = "string"; quote = ch
            elif ch == left:
                depth += 1
            elif ch == right:
                depth -= 1
                if depth == 0: return i
        i += 1
    raise RuntimeError(f"Unbalanced Kotlin block beginning at {start}")

def add_screen_params(text, name, params):
    marker = f"fun {name}("
    start = text.find(marker)
    if start < 0: raise RuntimeError(f"Missing screen function {name}")
    op = text.find("(", start)
    end = matching_end(text, op, "(", ")")
    sig = text[op + 1:end]
    if "isPrimaryOwner" in sig: return text
    pos = sig.rfind("modifier:")
    if pos >= 0:
        insert = op + 1 + pos
        prefix = text[op + 1:insert].rstrip()
        comma = "" if not prefix or prefix.endswith(",") else ","
        return text[:insert] + comma + "\n    " + params + "\n    " + text[insert:]
    return text[:end] + ",\n    " + params + "\n" + text[end:]

def inject_screen_call(text, name, args):
    marker = name + "("
    start = text.find(marker)
    if start < 0: raise RuntimeError(f"Missing {name} call in PinkyApp")
    op = start + len(name)
    end = matching_end(text, op, "(", ")")
    block = text[start:end + 1]
    if "isPrimaryOwner =" in block: return text
    return text[:end] + ",\n                                    " + args + "\n                                " + text[end:]

def add_impl_method(text, class_name, method_name, body):
    marker = f"class {class_name}"
    start = text.find(marker)
    if start < 0: raise RuntimeError(f"Missing repository implementation {class_name}")
    op = text.find("{", start)
    end = matching_end(text, op)
    block = text[start:end + 1]
    if method_name in block: return text
    sync = re.search(r"\n\s*override suspend fun sync\w+\(", block)
    at = start + sync.start() if sync else end
    return text[:at] + "\n" + body + "\n\n" + text[at:]

# Room DAO cache-clearing operations.
dao = read(DAO_FILE)
o = dao.find("interface OrderDao {")
if o < 0: raise RuntimeError("OrderDao missing")
ob = dao.find("{", o); oe = matching_end(dao, ob)
oblock = dao[o:oe + 1]
if "deleteAllOrders()" not in oblock:
    dao = dao[:oe] + '''
    @Query("DELETE FROM order_items")
    suspend fun deleteAllOrderItems()

    @Query("DELETE FROM orders")
    suspend fun deleteAllOrders()

    @Transaction
    suspend fun replaceOrders(orders: List<OrderEntity>, items: List<OrderItemEntity>) {
        deleteAllOrderItems()
        deleteAllOrders()
        if (orders.isNotEmpty()) insertOrders(orders)
        if (items.isNotEmpty()) insertOrderItems(items)
    }
''' + dao[oe:]
c = dao.find("interface CustomerDao {")
if c < 0: raise RuntimeError("CustomerDao missing")
cb = dao.find("{", c); ce = matching_end(dao, cb)
cblock = dao[c:ce + 1]
if "deleteAllCustomers()" not in cblock:
    dao = dao[:ce] + '''
    @Query("DELETE FROM customers")
    suspend fun deleteAllCustomers()

    @Transaction
    suspend fun replaceCustomers(customers: List<CustomerEntity>) {
        deleteAllCustomers()
        if (customers.isNotEmpty()) insertCustomers(customers)
    }
''' + dao[ce:]
write(DAO_FILE, dao)

# Add explicit cache-clearing methods to repository contracts.
for interface_name, method in (
    ("OrderRepository", "suspend fun clearLocalOrders()"),
    ("CustomerRepository", "suspend fun clearLocalCustomers()"),
):
    found = False
    for file in SRC.rglob("*.kt"):
        source = file.read_text(encoding="utf-8")
        marker = f"interface {interface_name}"
        if marker not in source: continue
        found = True
        if method not in source:
            start = source.find(marker)
            brace = source.find("{", start)
            source = source[:brace + 1] + "\n    " + method + "\n" + source[brace + 1:]
            write(file, source)
        break
    if not found: raise RuntimeError(f"{interface_name} interface not found")

repos = read(REPO_FILE)
repos = add_impl_method(repos, "OrderRepositoryImpl", "clearLocalOrders()",
    '''    override suspend fun clearLocalOrders() = withContext(Dispatchers.IO) {
        orderDao.deleteAllOrderItems()
        orderDao.deleteAllOrders()
    }''')
repos = add_impl_method(repos, "CustomerRepositoryImpl", "clearLocalCustomers()",
    '''    override suspend fun clearLocalCustomers() = withContext(Dispatchers.IO) {
        customerDao.deleteAllCustomers()
    }''')
repos = repos.replace("customerDao.insertCustomers(entities)", "customerDao.replaceCustomers(entities)", 1)
repos = repos.replace(
'''            } else {
                deriveCustomersFromLocalOrders()
            }
        } catch (e: Exception) {
            deriveCustomersFromLocalOrders()
        }''',
'''            } else {
                Result.failure(IllegalStateException("تعذر مزامنة بيانات العملاء من Supabase"))
            }
        } catch (e: Exception) {
            android.util.Log.e("SupabaseError", "syncCustomers failed", e)
            Result.failure(e)
        }''', 1)
write(REPO_FILE, repos)

# Supabase RPC declarations.
api = read(API_FILE)
if "admin_delete_selected_data" not in api:
    match = re.search(r"interface\s+\w+\s*\{", api)
    inserted = False
    while match:
        brace = api.find("{", match.start())
        end = matching_end(api, brace)
        block = api[match.start():end + 1]
        if "getOrders" in block or "rest/v1/orders" in block:
            methods = '''
    @POST("rest/v1/rpc/admin_is_primary_owner")
    suspend fun isPrimaryOwner(@Body body: Map<String, String>): retrofit2.Response<Boolean>

    @POST("rest/v1/rpc/admin_set_data_reset_pin")
    suspend fun setOwnerDataResetPin(@Body body: Map<String, String>): retrofit2.Response<Map<String, Any>>

    @POST("rest/v1/rpc/admin_delete_selected_data")
    suspend fun deleteSelectedData(@Body body: Map<String, Any?>): retrofit2.Response<Map<String, Any>>
'''
            api = api[:end] + methods + api[end:]
            inserted = True
            break
        match = re.search(r"interface\s+\w+\s*\{", api, match.end())
    if not inserted: raise RuntimeError("Supabase Retrofit interface not found")
write(API_FILE, api)

# ViewModel methods.
vm = read(VM_FILE)
if "private val _isPrimaryOwner" not in vm:
    anchor = "    val currentUser: StateFlow<AdminUser?>"
    if anchor not in vm: raise RuntimeError("currentUser state anchor not found")
    vm = vm.replace(anchor, '''    private val _isPrimaryOwner = MutableStateFlow(false)
    val isPrimaryOwner: StateFlow<Boolean> = _isPrimaryOwner.asStateFlow()

''' + anchor, 1)
if "import kotlinx.coroutines.Dispatchers" not in vm:
    vm = vm.replace("import kotlinx.coroutines.launch", "import kotlinx.coroutines.launch\nimport kotlinx.coroutines.Dispatchers\nimport kotlinx.coroutines.withContext", 1)
if "suspend fun refreshPrimaryOwnerStatus()" not in vm:
    methods = '''
    suspend fun refreshPrimaryOwnerStatus() {
        _isPrimaryOwner.value = try {
            val response = SupabaseClient.service.isPrimaryOwner(emptyMap())
            response.isSuccessful && response.body() == true
        } catch (e: Exception) {
            android.util.Log.w("OwnerDataReset", "Could not verify primary owner status", e)
            false
        }
    }

    suspend fun setOwnerDataResetPin(pin: String): Result<Unit> = withContext(Dispatchers.IO) {
        if (pin.length != 6 || !pin.all { it.isDigit() }) {
            return@withContext Result.failure(IllegalArgumentException("رمز PIN يجب أن يتكون من 6 أرقام"))
        }
        try {
            val response = SupabaseClient.service.setOwnerDataResetPin(mapOf("p_pin" to pin))
            if (!response.isSuccessful) {
                return@withContext Result.failure(IllegalStateException("تعذر حفظ رمز PIN (\${response.code()})"))
            }
            val body = response.body()
            if (body?.get("success") as? Boolean != true) {
                return@withContext Result.failure(IllegalStateException(body?.get("message")?.toString() ?: "تعذر حفظ رمز PIN"))
            }
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun deleteOwnerData(scope: String, ids: List<String>?, pin: String): Result<Int> = withContext(Dispatchers.IO) {
        if (scope !in setOf("orders", "customers", "coupons")) {
            return@withContext Result.failure(IllegalArgumentException("نوع البيانات غير مسموح بحذفه"))
        }
        if (pin.length != 6 || !pin.all { it.isDigit() }) {
            return@withContext Result.failure(IllegalArgumentException("أدخل رمز PIN المكون من 6 أرقام"))
        }
        try {
            val response = SupabaseClient.service.deleteSelectedData(
                mapOf("p_pin" to pin, "p_scope" to scope, "p_ids" to ids)
            )
            if (!response.isSuccessful) {
                return@withContext Result.failure(IllegalStateException("فشل الحذف من قاعدة البيانات (\${response.code()})"))
            }
            val body = response.body()
            if (body?.get("success") as? Boolean != true) {
                return@withContext Result.failure(IllegalStateException(body?.get("message")?.toString() ?: "تعذر حذف البيانات"))
            }
            val deleted = (body["deleted_count"] as? Number)?.toInt() ?: 0
            when (scope) {
                "orders" -> {
                    orderRepository.clearLocalOrders()
                    val refresh = orderRepository.syncOrders()
                    if (refresh.isFailure) android.util.Log.w("OwnerDataReset", "Orders deleted remotely; local refresh will retry", refresh.exceptionOrNull())
                }
                "customers" -> {
                    customerRepository.clearLocalCustomers()
                    val refresh = customerRepository.syncCustomers()
                    if (refresh.isFailure) android.util.Log.w("OwnerDataReset", "Customers deleted remotely; local refresh will retry", refresh.exceptionOrNull())
                }
                "coupons" -> {
                    _coupons.value = if (ids == null) emptyList() else _coupons.value.filterNot { it.id in ids }
                    syncRemainingSupabaseData()
                }
            }
            Result.success(deleted)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
'''
    methods = methods.replace("\\" + chr(36) + "{", chr(36) + "{")
    close = vm.rfind("\n}")
    if close < 0: raise RuntimeError("PinkyViewModel class closing brace missing")
    vm = vm[:close] + "\n" + methods + vm[close:]
write(VM_FILE, vm)

# Shared PIN dialog and selection toolbar.
component = PKG / "ui/components/OwnerDataResetControls.kt"
component.parent.mkdir(parents=True, exist_ok=True)
if not component.exists():
    write(component, r'''package com.pinky.dashboard.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

@Composable
fun OwnerDataResetControls(
    scopeLabel: String,
    isPrimaryOwner: Boolean,
    selectedIds: List<String>,
    totalCount: Int,
    onSelectAll: () -> Unit,
    onClearSelection: () -> Unit,
    onDeleteSelected: suspend (List<String>?, String) -> Result<Int>,
    onSetPin: suspend (String) -> Result<Unit>,
    onDeleteComplete: () -> Unit,
    modifier: Modifier = Modifier
) {
    if (!isPrimaryOwner) return
    val coroutineScope = rememberCoroutineScope()
    var showPinSetup by remember { mutableStateOf(false) }
    var showDeleteDialog by remember { mutableStateOf(false) }
    var newPin by remember { mutableStateOf("") }
    var confirmPin by remember { mutableStateOf("") }
    var enteredPin by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var feedback by remember { mutableStateOf<String?>(null) }
    val allSelected = totalCount > 0 && selectedIds.size >= totalCount

    Column(modifier = modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            OutlinedButton(
                onClick = { if (allSelected) onClearSelection() else onSelectAll() },
                enabled = totalCount > 0 && !busy,
                modifier = Modifier.weight(1f)
            ) { Text(if (allSelected) "إلغاء تحديد الكل" else "تحديد الكل") }
            Button(
                onClick = { enteredPin = ""; errorMessage = null; showDeleteDialog = true },
                enabled = selectedIds.isNotEmpty() && !busy,
                modifier = Modifier.weight(1f)
            ) { Text("حذف المحدد (\${selectedIds.size})") }
        }
        TextButton(onClick = {
            newPin = ""; confirmPin = ""; errorMessage = null; showPinSetup = true
        }, enabled = !busy) { Text("إعداد / تغيير رمز PIN") }
        feedback?.let { Text(it, color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodySmall) }
    }

    if (showPinSetup) {
        AlertDialog(
            onDismissRequest = { if (!busy) showPinSetup = false },
            title = { Text("إعداد رمز الحذف") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("اختر رمزًا سريًا من 6 أرقام. الحساب الأساسي وحده يستطيع تغييره.")
                    OutlinedTextField(
                        value = newPin,
                        onValueChange = { if (it.length <= 6 && it.all(Char::isDigit)) newPin = it },
                        label = { Text("رمز PIN الجديد") },
                        singleLine = true,
                        visualTransformation = PasswordVisualTransformation(),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                        enabled = !busy
                    )
                    OutlinedTextField(
                        value = confirmPin,
                        onValueChange = { if (it.length <= 6 && it.all(Char::isDigit)) confirmPin = it },
                        label = { Text("تأكيد رمز PIN") },
                        singleLine = true,
                        visualTransformation = PasswordVisualTransformation(),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                        enabled = !busy
                    )
                    errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                }
            },
            confirmButton = {
                TextButton(
                    enabled = !busy && newPin.length == 6 && newPin == confirmPin,
                    onClick = {
                        coroutineScope.launch {
                            busy = true
                            errorMessage = null
                            val result = onSetPin(newPin)
                            busy = false
                            if (result.isSuccess) {
                                showPinSetup = false
                                feedback = "تم حفظ رمز الحذف بأمان"
                            } else errorMessage = result.exceptionOrNull()?.message ?: "تعذر حفظ الرمز"
                        }
                    }
                ) { Text(if (busy) "جارٍ الحفظ..." else "حفظ الرمز") }
            },
            dismissButton = {
                TextButton(onClick = { if (!busy) showPinSetup = false }, enabled = !busy) { Text("إلغاء") }
            }
        )
    }

    if (showDeleteDialog) {
        AlertDialog(
            onDismissRequest = { if (!busy) showDeleteDialog = false },
            title = { Text("تأكيد حذف $scopeLabel") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("سيتم حذف \${selectedIds.size} سجل من $scopeLabel نهائيًا. لا يمكن التراجع عن العملية.")
                    OutlinedTextField(
                        value = enteredPin,
                        onValueChange = { if (it.length <= 6 && it.all(Char::isDigit)) enteredPin = it },
                        label = { Text("رمز PIN المكون من 6 أرقام") },
                        singleLine = true,
                        visualTransformation = PasswordVisualTransformation(),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                        enabled = !busy
                    )
                    errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                }
            },
            confirmButton = {
                TextButton(
                    enabled = !busy && enteredPin.length == 6 && selectedIds.isNotEmpty(),
                    onClick = {
                        coroutineScope.launch {
                            busy = true
                            errorMessage = null
                            val ids = selectedIds
                            val result = onDeleteSelected(ids, enteredPin)
                            busy = false
                            if (result.isSuccess) {
                                val count = result.getOrNull() ?: 0
                                showDeleteDialog = false
                                onDeleteComplete()
                                feedback = "تم حذف $count سجل من $scopeLabel"
                            } else errorMessage = result.exceptionOrNull()?.message ?: "تعذر تنفيذ الحذف"
                        }
                    }
                ) { Text(if (busy) "جارٍ الحذف..." else "تأكيد الحذف") }
            },
            dismissButton = {
                TextButton(onClick = { if (!busy) showDeleteDialog = false }, enabled = !busy) { Text("إلغاء") }
            }
        )
    }
}
''')

    component_text = read(component).replace("\\" + chr(36) + "{", chr(36) + "{")
    write(component, component_text)

def add_selection_screen(file, function_name, ids_var, list_name, item_name, scope_label, panel_anchor):
    text = read(file)
    params = '''isPrimaryOwner: Boolean = false,
    onDeleteSelected: suspend (List<String>?, String) -> Result<Int> = { _, _ -> Result.failure(IllegalStateException("غير متاح")) },
    onSetDataResetPin: suspend (String) -> Result<Unit> = { Result.failure(IllegalStateException("غير متاح")) },'''
    text = add_screen_params(text, function_name, params)
    if f"var {ids_var} by remember" not in text:
        marker = f"fun {function_name}("
        fs = text.find(marker)
        op = text.find("(", fs)
        sig_end = matching_end(text, op, "(", ")")
        body = text.find("{", sig_end)
        text = text[:body + 1] + f"\n    var {ids_var} by remember {{ mutableStateOf(setOf<String>()) }}\n" + text[body + 1:]
    if panel_anchor not in text: raise RuntimeError(f"Panel anchor missing in {file}")
    panel = f'''
        if (isPrimaryOwner) {{
            OwnerDataResetControls(
                scopeLabel = "{scope_label}",
                isPrimaryOwner = isPrimaryOwner,
                selectedIds = {ids_var}.toList(),
                totalCount = {list_name}.size,
                onSelectAll = {{ {ids_var} = {list_name}.map {{ it.id }}.toSet() }},
                onClearSelection = {{ {ids_var} = emptySet() }},
                onDeleteSelected = onDeleteSelected,
                onSetPin = onSetDataResetPin,
                onDeleteComplete = {{ {ids_var} = emptySet() }},
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
            )
        }}
'''
    if f'scopeLabel = "{scope_label}"' not in text:
        text = text.replace(panel_anchor, panel_anchor + panel, 1)
    marker = item_name + "("
    call_start = text.find(marker)
    if call_start < 0: raise RuntimeError(f"{item_name} call not found in {file}")
    call_open = text.find("(", call_start)
    call_end = matching_end(text, call_open, "(", ")")
    call = text[call_start:call_end + 1]
    if ids_var not in call:
        checkbox_row = f'''
                    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {{
                        if (isPrimaryOwner) {{
                            Checkbox(
                                checked = {ids_var}.contains({item_name.replace("CardItem", "").lower()}.id),
                                onCheckedChange = {{ checked ->
                                    val selectedId = {item_name.replace("CardItem", "").lower()}.id
                                    {ids_var} = if (checked) {ids_var} + selectedId else {ids_var} - selectedId
                                }}
                            )
                        }}
                        Box(modifier = Modifier.weight(1f)) {{
                            {call}
                        }}
                    }}'''
        text = text[:call_start] + checkbox_row + text[call_end + 1:]
    write(file, text)

# Customers
customers_file = PKG / "ui/screens/customers/CustomersScreen.kt"
customers = read(customers_file)
if "OwnerDataResetControls" not in customers:
    customers = customers.replace(
        "import com.pinky.dashboard.ui.components.PinkyStatCard",
        "import com.pinky.dashboard.ui.components.PinkyStatCard\nimport com.pinky.dashboard.ui.components.OwnerDataResetControls", 1
    )
write(customers_file, customers)
add_selection_screen(
    customers_file, "CustomersScreen", "selectedCustomerIds", "customers",
    "CustomerCardItem", "العملاء", "        if (filteredCustomers.isEmpty()) {"
)

# Orders
orders_file = PKG / "ui/screens/orders/OrdersScreen.kt"
orders = read(orders_file)
if "OwnerDataResetControls" not in orders:
    orders = orders.replace(
        "import com.pinky.dashboard.ui.theme.PinkPrimary",
        "import com.pinky.dashboard.ui.theme.PinkPrimary\nimport com.pinky.dashboard.ui.components.OwnerDataResetControls", 1
    )
write(orders_file, orders)
add_selection_screen(
    orders_file, "OrdersScreen", "selectedOrderIds", "orders",
    "OrderCardItem", "الطلبات", "        if (filteredOrders.isEmpty()) {"
)

# Coupons
offers_file = PKG / "ui/screens/offers/OffersScreen.kt"
offers = read(offers_file)
if "OwnerDataResetControls" not in offers:
    offers = offers.replace(
        "import com.pinky.dashboard.ui.components.EmptyStateCard",
        "import com.pinky.dashboard.ui.components.EmptyStateCard\nimport com.pinky.dashboard.ui.components.OwnerDataResetControls", 1
    )
offers = add_screen_params(
    offers, "OffersScreen",
    '''isPrimaryOwner: Boolean = false,
    onDeleteSelected: suspend (List<String>?, String) -> Result<Int> = { _, _ -> Result.failure(IllegalStateException("غير متاح")) },
    onSetDataResetPin: suspend (String) -> Result<Unit> = { Result.failure(IllegalStateException("غير متاح")) },'''
)
if "selectedCouponIds" not in offers:
    offers = offers.replace(
        "var couponToDelete by remember { mutableStateOf<Coupon?>(null) }",
        "var couponToDelete by remember { mutableStateOf<Coupon?>(null) }\n    var selectedCouponIds by remember { mutableStateOf(setOf<String>()) }",
        1
    )
anchor = "                // Coupons Tab\n"
if anchor not in offers: raise RuntimeError("Coupons tab anchor not found")
panel = '''                if (isPrimaryOwner) {
                    OwnerDataResetControls(
                        scopeLabel = "الكوبونات",
                        isPrimaryOwner = isPrimaryOwner,
                        selectedIds = selectedCouponIds.toList(),
                        totalCount = coupons.size,
                        onSelectAll = { selectedCouponIds = coupons.map { it.id }.toSet() },
                        onClearSelection = { selectedCouponIds = emptySet() },
                        onDeleteSelected = onDeleteSelected,
                        onSetPin = onSetDataResetPin,
                        onDeleteComplete = { selectedCouponIds = emptySet() },
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                    )
                }
'''
if 'scopeLabel = "الكوبونات"' not in offers:
    offers = offers.replace(anchor, anchor + panel, 1)
old_delete = '''                                            IconButton(onClick = { couponToDelete = coupon }) {
                                                Icon(Icons.Outlined.Delete, contentDescription = "حذف", tint = StatusCancelled)
                                            }'''
new_delete = '''                                            if (isPrimaryOwner) {
                                                Checkbox(
                                                    checked = selectedCouponIds.contains(coupon.id),
                                                    onCheckedChange = { checked ->
                                                        selectedCouponIds = if (checked) selectedCouponIds + coupon.id else selectedCouponIds - coupon.id
                                                    }
                                                )
                                            }'''
if old_delete in offers:
    offers = offers.replace(old_delete, new_delete, 1)
elif "couponToDelete = coupon" in offers:
    raise RuntimeError("Could not replace the unprotected coupon delete button")
write(offers_file, offers)

# PinkyApp state and screen callbacks.
app = read(APP_FILE)
if "val isPrimaryOwner by viewModel.isPrimaryOwner.collectAsStateWithLifecycle()" not in app:
    anchor = "val currentUser by viewModel.currentUser.collectAsStateWithLifecycle()"
    if anchor not in app: raise RuntimeError("PinkyApp currentUser state not found")
    if "import androidx.compose.runtime.LaunchedEffect" not in app:
        app = app.replace("package com.pinky.dashboard.ui", "package com.pinky.dashboard.ui\n\nimport androidx.compose.runtime.LaunchedEffect", 1)
    app = app.replace(anchor, anchor + "\n    val isPrimaryOwner by viewModel.isPrimaryOwner.collectAsStateWithLifecycle()\n    LaunchedEffect(currentUser?.id) { viewModel.refreshPrimaryOwnerStatus() }", 1)
app = inject_screen_call(app, "OrdersScreen", '''isPrimaryOwner = isPrimaryOwner,
                                    onDeleteSelected = { ids, pin -> viewModel.deleteOwnerData("orders", ids, pin) },
                                    onSetDataResetPin = { pin -> viewModel.setOwnerDataResetPin(pin) }''')
app = inject_screen_call(app, "CustomersScreen", '''isPrimaryOwner = isPrimaryOwner,
                                    onDeleteSelected = { ids, pin -> viewModel.deleteOwnerData("customers", ids, pin) },
                                    onSetDataResetPin = { pin -> viewModel.setOwnerDataResetPin(pin) }''')
app = inject_screen_call(app, "OffersScreen", '''isPrimaryOwner = isPrimaryOwner,
                                    onDeleteSelected = { ids, pin -> viewModel.deleteOwnerData("coupons", ids, pin) },
                                    onSetDataResetPin = { pin -> viewModel.setOwnerDataResetPin(pin) }''')
write(APP_FILE, app)

print("Owner-only PIN reset patch applied to Orders, Customers and Coupons. Products are untouched.")
