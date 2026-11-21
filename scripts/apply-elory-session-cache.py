from pathlib import Path
import shutil
from session_isolation_common import *

test_source = Path(__file__).with_name("SessionCacheIsolationTest.kt")
if not test_source.is_file():
    raise SystemExit("SessionCacheIsolationTest.kt overlay is missing")
test_content = test_source.read_text(encoding="utf-8")
if TEST_DEST.exists() and TEST_DEST.read_text(encoding="utf-8") != test_content:
    raise SystemExit("Existing SessionCacheIsolationTest.kt differs; refusing to overwrite")
TEST_DEST.parent.mkdir(parents=True, exist_ok=True)
if not TEST_DEST.exists():
    shutil.copyfile(test_source, TEST_DEST)

cleaner_path = JAVA + "data/local/SessionCacheCleaner.kt"
cleaner = '''package com.pinky.dashboard.data.local

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Clears account-bound local cache rows without dropping or recreating the Room schema. */
class SessionCacheCleaner(private val database: PinkyDatabase) {
    suspend fun clear() = withContext(Dispatchers.IO) {
        database.clearAllTables()
    }
}
'''
if ROOT.joinpath("app/src/main/java/com/pinky/dashboard/data/local/SessionCacheCleaner.kt").exists():
    if read(cleaner_path) != cleaner:
        raise SystemExit("SessionCacheCleaner already exists with unexpected contents")
else:
    write(cleaner_path, cleaner)

repo_path = JAVA + "data/repository/RepositoriesImpl.kt"
repo = read(repo_path)
repo = add_import(repo, "import com.pinky.dashboard.data.local.SessionCacheCleaner", "import com.pinky.dashboard.data.local.PinkyDatabase\n")
repo = add_import(repo, "import com.pinky.dashboard.core.notification.PinkyNotificationManager", "import com.pinky.dashboard.data.local.SessionCacheCleaner\n")
repo = replace(repo,
'''    private val dataStoreManager = com.pinky.dashboard.data.local.AuthDataStoreManager(context)
    private val _currentUser = MutableStateFlow<AdminUser?>(null)''',
'''    private val dataStoreManager = com.pinky.dashboard.data.local.AuthDataStoreManager(context)
    private val sessionCacheCleaner = SessionCacheCleaner(PinkyDatabase.getInstance(context))
    private val _currentUser = MutableStateFlow<AdminUser?>(null)''', "Create session cache cleaner")
repo = replace(repo,
'''    private suspend fun clearLocalSession() {
        SupabaseClient.clearSession()
        dataStoreManager.clearSession()
        prefs.edit().clear().apply()
        _currentUser.value = null
    }''',
'''    private suspend fun clearLocalSession() {
        SupabaseClient.clearSession()
        dataStoreManager.clearSession()
        prefs.edit().clear().apply()
        context.getSharedPreferences("elory_push_registration", android.content.Context.MODE_PRIVATE).edit().clear().apply()
        PinkyNotificationManager(context).cancelAllNotifications()
        _currentUser.value = null
        // Local Room rows only; remote products, orders and customers are untouched.
        sessionCacheCleaner.clear()
    }''', "Clear cache at auth boundary")
repo = replace(repo,
'''            if (token.isNullOrBlank() || id.isNullOrBlank() || email.isNullOrBlank()) {
                SupabaseClient.isSessionReady = true
                SupabaseClient.isAuthenticated = false
                _currentUser.value = null
                return@withContext false
            }
            if (!SupabaseClient.hasValidConfiguration) {
                SupabaseClient.isSessionReady = true
                SupabaseClient.isAuthenticated = false
                return@withContext false
            }''',
'''            if (token.isNullOrBlank() || id.isNullOrBlank() || email.isNullOrBlank()) {
                clearLocalSession()
                SupabaseClient.isSessionReady = true
                return@withContext false
            }
            if (!SupabaseClient.hasValidConfiguration) {
                clearLocalSession()
                SupabaseClient.isSessionReady = true
                return@withContext false
            }''', "Clear cache without a valid restored session")
repo = replace(repo,
'''        } catch (e: Exception) {
            android.util.Log.e("EloryAuth", "Session initialization failed (${e.javaClass.simpleName}).")
            SupabaseClient.isSessionReady = true
            SupabaseClient.isAuthenticated = false
            false
        }''',
'''        } catch (e: Exception) {
            android.util.Log.e("EloryAuth", "Session initialization failed (${e.javaClass.simpleName}).")
            runCatching { clearLocalSession() }
                .onFailure { cleanupError -> android.util.Log.e("EloryAuth", "Local session cache cleanup failed.", cleanupError) }
            SupabaseClient.isSessionReady = true
            SupabaseClient.isAuthenticated = false
            false
        }''', "Fail closed after restore errors")
repo = replace(repo,
'''        val refreshed = SupabaseClient.performTokenRefresh()
        if (!refreshed) return@withContext false
        val current = _currentUser.value ?: return@withContext false
        val session = dataStoreManager.getSession()
        val response = SupabaseClient.service.getStaffProfileById("eq.${current.id}", "*")
        if (!response.isSuccessful) return@withContext false
        val profile = response.body()?.firstOrNull() ?: return@withContext false''',
'''        val refreshed = SupabaseClient.performTokenRefresh()
        if (!refreshed) {
            if (!SupabaseClient.isAuthenticated) clearLocalSession()
            return@withContext false
        }
        val current = _currentUser.value ?: return@withContext false
        val session = dataStoreManager.getSession()
        val response = SupabaseClient.service.getStaffProfileById("eq.${current.id}", "*")
        if (!response.isSuccessful) {
            if (response.code() in 401..403) clearLocalSession()
            return@withContext false
        }
        val profile = response.body()?.firstOrNull() ?: run {
            clearLocalSession()
            return@withContext false
        }''', "Clear cache when staff session is revoked")
repo = replace(repo,
'''        if (email.isBlank() || pass.isBlank()) {
            return@withContext Result.failure(Exception("اكتب البريد الإلكتروني وكلمة المرور."))
        }

        try {''',
'''        if (email.isBlank() || pass.isBlank()) {
            return@withContext Result.failure(Exception("اكتب البريد الإلكتروني وكلمة المرور."))
        }
        try {
            // Never let a new account inherit rows cached by the previous account.
            clearLocalSession()
        } catch (cleanupError: Exception) {
            return@withContext Result.failure(Exception("تعذر تأمين بيانات الحساب السابق على هذا الجهاز. أعد المحاولة بعد إغلاق التطبيق وفتحه."))
        }

        try {''', "Clear previous account cache before login")
write(repo_path, repo)

notification_path = JAVA + "core/notification/PinkyNotificationManager.kt"
notification = read(notification_path)
if "fun cancelAllNotifications()" not in notification:
    notification = replace(notification,
        "    fun showNewOrderNotification(order: Order) {",
        "    fun cancelAllNotifications() {\n        notificationManager.cancelAll()\n    }\n\n    fun showNewOrderNotification(order: Order) {",
        "Add app notification cleanup")
write(notification_path, notification)
