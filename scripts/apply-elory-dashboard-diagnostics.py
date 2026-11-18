from pathlib import Path
import os
R=Path(os.environ["PROJECT_DIR"]).resolve()
p=R/"app/src/main/java/com/pinky/dashboard/ui/screens/health/HealthCheckScreen.kt"
s=p.read_text(encoding="utf-8")
def replace(old,new,label):
 global s
 old=old.replace("@@","$")
 new=new.replace("@@","$")
 if new in s:return
 if old not in s:raise SystemExit("Missing health diagnostic anchor: "+label)
 s=s.replace(old,new,1)
replace("                for ((tableName, queryFunc) in tablesToTest) {\n","""                for ((tableName, queryFunc) in tablesToTest) {
                    var tableStatus = TestStatus.FAILED
                    var tableError: DiagnosticError? = null
                    val tableLogs = mutableListOf<String>()
""","table loop")
replace('                            rlsLogs.add("- جدول $tableName: قراءة ناجحة ✓")\n                            succeededTables++\n','''                            rlsLogs.add("- جدول $tableName: قراءة ناجحة ✓")
                            tableLogs.add("تم تنفيذ استعلام القراءة الفعلي بنجاح.")
                            tableStatus = TestStatus.WORKING
                            succeededTables++
''',"success")
replace('                                rlsLogs.add("- جدول $tableName: حماية الـ RLS تفرض قيوداً لهذا الحساب (HTTP 403/42501) ✓")\n                                restrictedTables++\n','''                                rlsLogs.add("- جدول $tableName: حماية الـ RLS تفرض قيوداً لهذا الحساب (HTTP 403/42501) ✓")
                                tableLogs.add("رفضت قاعدة البيانات القراءة لهذا الحساب؛ راجع دور المستخدم وسياسة RLS.")
                                tableStatus = TestStatus.PARTIAL
                                tableError = DiagnosticError("select", tableName, response.code(), "42501", errorStr.ifBlank { "RLS restricted this role" }, "RLS / Authorization")
                                restrictedTables++
''',"RLS detail")
replace('                                rlsLogs.add("- جدول $tableName: فشل الاستعلام (@@{response.code()}): $errorStr ✗")\n                                failedTables++\n','''                                rlsLogs.add("- جدول $tableName: فشل الاستعلام (@@{response.code()}): $errorStr ✗")
                                tableLogs.add("فشل HTTP @@{response.code()}: @@{errorStr.take(700)}")
                                tableStatus = TestStatus.FAILED
                                tableError = DiagnosticError("select", tableName, response.code(), "HTTP_@@{response.code()}", errorStr.take(700), "Database / RLS")
                                failedTables++
''',"HTTP failure")
replace('                        rlsLogs.add("- جدول $tableName: فشل الاتصال (@@{e.message}) ✗")\n                        failedTables++\n','''                        rlsLogs.add("- جدول $tableName: فشل الاتصال (@@{e.message}) ✗")
                        tableLogs.add("تعذر تنفيذ طلب الشبكة: @@{e.message ?: "Network error"}")
                        tableStatus = TestStatus.FAILED
                        tableError = DiagnosticError("select", tableName, 0, "NET_ERR", e.message ?: "Network error", "Network / Repository")
                        failedTables++
''',"network failure")
replace("""                    }
                }

                rlsLogs.add("ملخص الفحص: الجداول المقروءة بنجاح: $succeededTables، الجداول الخاضعة لقيود RLS: $restrictedTables، جداول فاشلة: $failedTables")
""","""                    }
                    updatedResults["section_$tableName"] = ModuleTestResult(
                        name = tableName,
                        arabicName = when (tableName) {
                            "orders" -> "قسم الطلبات"
                            "products" -> "قسم المنتجات والمخزون"
                            "categories" -> "قسم الأقسام"
                            "offers" -> "قسم العروض"
                            "banners" -> "قسم البنرات"
                            "coupons" -> "قسم الكوبونات"
                            "shipping_governorates" -> "قسم المحافظات والشحن"
                            "shipping_centers" -> "قسم مراكز الشحن"
                            "prime_subscriptions" -> "قسم اشتراكات Prime"
                            "site_customizations" -> "قسم تحرير الموقع"
                            "store_settings" -> "قسم إعدادات المتجر"
                            "staff_profiles" -> "قسم الموظفين والصلاحيات"
                            else -> "قسم $tableName"
                        },
                        dashboardToWebsite = tableStatus,
                        websiteToDashboard = tableStatus,
                        supabaseStatus = tableStatus,
                        logs = tableLogs,
                        error = tableError
                    )
                    testResults = updatedResults.toMap()
                }

                rlsLogs.add("ملخص الفحص: الجداول المقروءة بنجاح: $succeededTables، الجداول الخاضعة لقيود RLS: $restrictedTables، جداول فاشلة: $failedTables")
""","individual section cards")
replace("            items(testResults.values.toList()) { result ->\n","            items(testResults.values.toList(), key = { it.name }) { result ->\n","stable card keys")
p.write_text(s,encoding="utf-8")
print("Per-section live diagnostics added.")
