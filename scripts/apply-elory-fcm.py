from session_isolation_common import *

fcm_path = JAVA + "core/notification/EloryFirebaseMessagingService.kt"
fcm = read(fcm_path)
fcm = add_import(fcm, "import com.pinky.dashboard.data.local.AuthDataStoreManager", "import com.pinky.dashboard.data.local.PinkyDatabase\n")
fcm = add_import(fcm, "import com.pinky.dashboard.data.repository.AuthRepositoryImpl", "import com.pinky.dashboard.data.repository.OrderRepositoryImpl\n")
fcm = add_import(fcm, "import com.pinky.dashboard.data.remote.SupabaseClient", "import com.pinky.dashboard.data.repository.AuthRepositoryImpl\n")
fcm = add_import(fcm, "import kotlinx.coroutines.runBlocking", "import kotlinx.coroutines.launch\n")
fcm = add_import(fcm, "import kotlinx.coroutines.withTimeoutOrNull", "import kotlinx.coroutines.runBlocking\n")
old_fcm = """        PinkyNotificationManager(applicationContext).showNewOrderNotification(
            title = title,
            body = body,
            orderId = orderId.ifBlank { orderNumber }
        )

        // Refresh the authoritative Supabase order list immediately after the verified
        // Paymob webhook push. Room Flow updates the open Orders screen without waiting
        // for the periodic sync interval or requiring a manual refresh.
        serviceScope.launch {
            try {
                val database = PinkyDatabase.getInstance(applicationContext)
                val result = OrderRepositoryImpl(database).syncOrders()
                if (result.isFailure) {
                    android.util.Log.w("EloryPush", "New-order push received but order sync failed", result.exceptionOrNull())
                }
            } catch (error: Exception) {
                android.util.Log.w("EloryPush", "Unable to refresh orders after push", error)
            }
        }"""
new_fcm = """        val registeredUserId = getSharedPreferences("elory_push_registration", android.content.Context.MODE_PRIVATE)
            .getString("registered_user_id", null)
        val activeUserId = try {
            runBlocking(Dispatchers.IO) {
                val authenticated = withTimeoutOrNull(10_000L) {
                    AuthRepositoryImpl(applicationContext).initializeAuthSession()
                } ?: false
                if (!authenticated) null else AuthDataStoreManager(applicationContext).getSession().userId
            }
        } catch (error: Exception) {
            android.util.Log.w("EloryPush", "Unable to validate staff session for order notification", error)
            null
        }
        val currentRegisteredUserId = getSharedPreferences("elory_push_registration", android.content.Context.MODE_PRIVATE)
            .getString("registered_user_id", null)
        if (!SupabaseClient.isAuthenticated || activeUserId.isNullOrBlank() || activeUserId != registeredUserId || activeUserId != currentRegisteredUserId) return

        // Keep notification delivery synchronous with this FCM callback; the session
        // verification above is bounded so the service can finish without losing it.
        PinkyNotificationManager(applicationContext).showNewOrderNotification(
            title = title,
            body = body,
            orderId = orderId.ifBlank { orderNumber }
        )
        serviceScope.launch {
            try {
                val database = PinkyDatabase.getInstance(applicationContext)
                val result = OrderRepositoryImpl(database).syncOrders()
                if (result.isFailure) {
                    android.util.Log.w("EloryPush", "New-order push received but order sync failed", result.exceptionOrNull())
                }
            } catch (error: Exception) {
                android.util.Log.w("EloryPush", "Unable to refresh orders after push", error)
            }
        }"""
fcm = replace(fcm, old_fcm, new_fcm, "Require active matching staff session for push notifications")
write(fcm_path, fcm)
