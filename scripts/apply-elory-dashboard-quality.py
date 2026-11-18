from pathlib import Path
R=Path(__file__).resolve().parents[1]
def patch(path, old, new, name):
 p=R/path
 s=p.read_text(encoding="utf-8")
 if new in s:return
 if old not in s:raise SystemExit("Missing patch anchor: "+name)
 p.write_text(s.replace(old,new.replace("@@","$"),1),encoding="utf-8")

# Native clipboard component
p=R/"app/src/main/java/com/pinky/dashboard/ui/components/CopyTextButton.kt"
if not p.exists():
 p.write_text("""package com.pinky.dashboard.ui.components
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ContentCopy
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
@Composable
fun CopyTextButton(value:String,contentDescription:String="نسخ",modifier:Modifier=Modifier){
 val context=LocalContext.current
 IconButton(onClick={if(value.isNotBlank()){
  val cb=context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
  cb.setPrimaryClip(ClipData.newPlainText(contentDescription,value))
  Toast.makeText(context,"تم النسخ",Toast.LENGTH_SHORT).show()
 }},enabled=value.isNotBlank(),modifier=modifier){Icon(Icons.Outlined.ContentCopy,contentDescription=contentDescription)}
}
""",encoding="utf-8")

O="app/src/main/java/com/pinky/dashboard/ui/screens/orders/OrderDetailDialog.kt"
patch(O,"import com.pinky.dashboard.ui.components.OrderStatusBadge\n","import com.pinky.dashboard.ui.components.OrderStatusBadge\nimport com.pinky.dashboard.ui.components.CopyTextButton\n","order imports")
patch(O,"    var noteText by remember { mutableStateOf(order.notes) }\n",'''    var noteText by remember { mutableStateOf(order.notes) }
    val orderCopyText=remember(order){buildString{
      appendLine("رقم الطلب: @@{order.orderNumber}")
      appendLine("كود العميل: @@{order.customerOrderCode}")
      appendLine("العميل: @@{order.customerName}")
      appendLine("الهاتف: @@{order.customerPhone}")
      appendLine("المحافظة: @@{order.governorate} | المركز: @@{order.shippingCenter}")
      appendLine("العنوان: @@{order.customerAddress}")
      appendLine("الحالة: @@{order.status.displayLabel(order.paymentMethod)}")
      appendLine("الدفع: @@{order.paymentMethod.arabicLabel}")
      appendLine("الإجمالي: @@{order.totalAmount} | الشحن: @@{order.shippingFee} | الخصم: @@{order.discountAmount}")
      order.items.forEachIndexed{i,item->appendLine("@@{i+1}. @@{item.productName} | @@{item.quantity} قطعة | @@{item.color.orEmpty()} | @@{item.size.orEmpty()} | @@{item.lineTotal} | SKU @@{item.productCode}")}
      if(order.notes.isNotBlank())appendLine("ملاحظات: @@{order.notes}")
    }}
''',"order copy text")
patch(O,'                    IconButton(onClick = onDismiss, modifier = Modifier.testTag("close_order_detail_btn")) {\n','''                    CopyTextButton(orderCopyText,"نسخ تفاصيل الطلب",Modifier.testTag("copy_order_details_btn"))
                    IconButton(onClick = onDismiss, modifier = Modifier.testTag("close_order_detail_btn")) {
''',"order copy button")
patch(O,'''                                        Text(
                                            text = order.customerName,
                                            fontWeight = FontWeight.Bold,
                                            style = MaterialTheme.typography.bodyLarge
                                        )
''','''                                        Row(verticalAlignment=Alignment.CenterVertically){
                                            Text(order.customerName,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.bodyLarge,modifier=Modifier.weight(1f))
                                            CopyTextButton(order.customerName,"نسخ اسم العميل")
                                        }
''',"customer name")
patch(O,'''                                        Text(
                                            text = "الهاتف: @@{order.customerPhone}",
                                            style = MaterialTheme.typography.bodyMedium,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
''','''                                        Row(verticalAlignment=Alignment.CenterVertically){
                                            Text("الهاتف: @@{order.customerPhone}",style=MaterialTheme.typography.bodyMedium,color=MaterialTheme.colorScheme.onSurfaceVariant,modifier=Modifier.weight(1f))
                                            CopyTextButton(order.customerPhone,"نسخ رقم الهاتف")
                                        }
''',"customer phone")
patch(O,'''                            Text(
                                text = "رمز العميل: @@{order.customerOrderCode}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
''','''                            Row(verticalAlignment=Alignment.CenterVertically){
                                Text("رمز العميل: @@{order.customerOrderCode}",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant,modifier=Modifier.weight(1f))
                                CopyTextButton(order.customerOrderCode,"نسخ كود العميل")
                            }
''',"customer code")

P="app/src/main/java/com/pinky/dashboard/ui/screens/products/ProductsScreen.kt"
patch(P,"import com.pinky.dashboard.ui.components.OwnerDataResetControls\n","import com.pinky.dashboard.ui.components.OwnerDataResetControls\nimport com.pinky.dashboard.ui.components.CopyTextButton\n","product imports")
patch(P,'''    Card(
        modifier = Modifier
            .fillMaxWidth()
            .testTag("product_card_@@{product.id}"),
''','''    val productCopyText=buildString{
      appendLine("المنتج: @@{product.name}")
      appendLine("كود المنتج: @@{product.id}")
      appendLine("القسم: @@{product.categoryName}")
      appendLine("السعر: @@{product.price} | السابق: @@{product.oldPrice ?: "غير متوفر"}")
      appendLine("المخزون: @@{product.stock}")
      appendLine("الألوان: @@{product.colors.joinToString()} | المقاسات: @@{product.sizes.joinToString()}")
      appendLine("الحالة: @@{if(product.isActive) "نشط" else "غير نشط"}")
      if(currentUser?.canViewWholesale==true)appendLine("سعر الجملة: @@{product.wholesalePrice ?: "غير محدد"}")
      if(currentUser?.canViewInternalCode==true)appendLine("SKU: @@{product.internalCode ?: "—"}")
      if(product.description.isNotBlank())appendLine("الوصف: @@{product.description}")
    }
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .testTag("product_card_@@{product.id}"),
''',"product copy text")
patch(P,'''            Text(
                text = product.name,
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
''','''            Row(verticalAlignment=Alignment.CenterVertically){
                Text(product.name,style=MaterialTheme.typography.titleMedium.copy(fontWeight=FontWeight.Bold),color=MaterialTheme.colorScheme.onSurface,modifier=Modifier.weight(1f))
                CopyTextButton(productCopyText,"نسخ بيانات المنتج",Modifier.testTag("copy_product_@@{product.id}"))
            }
''',"product copy action")

N="app/src/main/java/com/pinky/dashboard/ui/screens/notifications/NotificationsScreen.kt"
patch(N,"import androidx.compose.runtime.Composable\n","import androidx.compose.runtime.Composable\nimport androidx.compose.runtime.getValue\nimport androidx.compose.runtime.mutableStateOf\nimport androidx.compose.runtime.remember\nimport androidx.compose.runtime.setValue\n","notification imports")
patch(N,"    Column(\n        modifier = modifier\n",'''    var selectedFilter by remember{mutableStateOf("all")}
    val unreadCount=notifications.count{!it.isRead}
    val visibleNotifications=when(selectedFilter){"unread"->notifications.filter{!it.isRead};"read"->notifications.filter{it.isRead};else->notifications}
    Column(
        modifier = modifier
''',"notification state")
patch(N,"        if (notifications.isEmpty()) {\n",'''        if(notifications.isNotEmpty()){
            Row(Modifier.fillMaxWidth().padding(horizontal=16.dp,vertical=2.dp),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                FilterChip(selectedFilter=="all",{selectedFilter="all"},label={Text("الكل @@{notifications.size}")})
                FilterChip(selectedFilter=="unread",{selectedFilter="unread"},label={Text("جديدة @@{unreadCount}")})
                FilterChip(selectedFilter=="read",{selectedFilter="read"},label={Text("مقروءة @@{notifications.size-unreadCount}")})
            }
        }
        if (notifications.isEmpty()) {
''',"notification filters")
patch(N,"                items(notifications, key = { it.id }) { notif ->\n","                items(visibleNotifications, key = { it.id }) { notif ->\n","notification filter list")
patch(N,"            LazyColumn(\n                modifier = Modifier\n",'''            if(visibleNotifications.isEmpty()){
                EmptyStateCard(title=if(selectedFilter=="unread")"لا توجد إشعارات جديدة" else "لا توجد إشعارات مقروءة",message="غيّر الفلتر لعرض باقي الإشعارات",icon=Icons.Outlined.NotificationsNone,modifier=Modifier.padding(16.dp))
            } else LazyColumn(
                modifier = Modifier
''',"notification empty state")

S="app/src/main/java/com/pinky/dashboard/ui/screens/shipping/ShippingScreen.kt"
patch(S,'    var searchQuery by remember { mutableStateOf("") }\n','    var searchQuery by remember { mutableStateOf("") }\n    var showAccountingNote by remember { mutableStateOf(false) }\n',"shipping note state")
patch(S,'''                        Text(
                            text = "تعديل وإضافة أسعار شحن المحافظات ومندوبين التوصيل لكل المراكز الفرعية التابعة لها.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = "ملاحظة محاسبية: السعر هنا هو كامل المبلغ المستحق لشركة الشحن، وليس إيرادًا للمتجر. يُحفظ كسعر تكلفة على الطلب وقت إنشائه ويُخصم من الربح، بما في ذلك الشحن المجاني في Prime. تغيير السعر لاحقًا لا يغيّر تكلفة الطلبات القديمة.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
''','''                        Text("إدارة أسعار الشحن والمحافظات والمراكز التابعة لها.",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                        TextButton(onClick={showAccountingNote=!showAccountingNote},contentPadding=PaddingValues(0.dp)){
                            Icon(if(showAccountingNote)Icons.Outlined.ExpandLess else Icons.Outlined.Info,contentDescription=null,modifier=Modifier.size(16.dp))
                            Spacer(Modifier.width(4.dp));Text("معلومة محاسبية",fontSize=12.sp)
                        }
                        if(showAccountingNote)Text("السعر هو تكلفة شركة الشحن وليس إيراداً للمتجر، ويُحفظ على الطلب وقت إنشائه ويُخصم من الربح، بما في ذلك الشحن المجاني في Prime. تغيير السعر لاحقاً لا يغيّر تكلفة الطلبات القديمة.",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
''',"shipping compact header")
patch(S,"                        Spacer(modifier = Modifier.height(16.dp))\n\n                        // Search Input\n",'''                        Spacer(modifier=Modifier.height(8.dp))
                        Row(horizontalArrangement=Arrangement.spacedBy(8.dp),modifier=Modifier.fillMaxWidth()){
                            val activeCount=governorates.count{it.isActive};val centerCount=shippingCenters.count{it.isActive}
                            Surface(Modifier.weight(1f),shape=RoundedCornerShape(10.dp),color=MaterialTheme.colorScheme.primary.copy(alpha=.08f)){
                                Column(Modifier.padding(10.dp)){Text("المحافظات",style=MaterialTheme.typography.labelSmall);Text("@@{governorates.size} إجمالي • @@{activeCount} نشطة",fontWeight=FontWeight.Bold,fontSize=12.sp)}
                            }
                            Surface(Modifier.weight(1f),shape=RoundedCornerShape(10.dp),color=MaterialTheme.colorScheme.secondaryContainer.copy(alpha=.55f)){
                                Column(Modifier.padding(10.dp)){Text("مراكز الشحن",style=MaterialTheme.typography.labelSmall);Text("@@{shippingCenters.size} إجمالي • @@{centerCount} نشط",fontWeight=FontWeight.Bold,fontSize=12.sp)}
                            }
                        }
                        Spacer(modifier=Modifier.height(8.dp))
                        // Search Input
''',"shipping governorate visibility")
print("Dashboard quality changes applied.")
