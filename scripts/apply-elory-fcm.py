from session_isolation_common import *

fcm_path = JAVA + "core/notification/EloryFirebaseMessagingService.kt"
fcm = read(fcm_path)
fcm = add_import(fcm, "import com.pinky.dashboard.data.local.AuthDataStoreManager", "import com.pinky.dashboard.data.local.PinkyDatabase\n")
fcm = add_import(fcm, "import com.pinky.dashboard.data.repository.AuthRepositoryImpl", "import com.pinky.dashboard.data.repository.OrderRepositoryImpl\n")
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
new_fcm = """        serviceScope.launch {
            try {
                // A push token can outlive a logout on the provider side. Revalidate the
                // saved staff session and match the locally registered account before
                // displaying an order notification or refreshing the local order cache.
                val authenticated = AuthRepositoryImpl(applicationContext).initializeAuthSession()
                if (!authenticated) return@launch
                val session = AuthDataStoreManager(applicationContext).getSession()
                val registeredUserId = getSharedPreferences("elory_push_registration", android.content.Context.MODE_PRIVATE)
                    .getString("registered_user_id", null)
                if (session.userId.isNullOrBlank() || session.userId != registeredUserId) return@launch

                PinkyNotificationManager(applicationContext).showNewOrderNotification(
                    title = title,
                    body = body,
                    orderId = orderId.ifBlank { orderNumber }
                )
                val database = PinkyDatabase.getInstance(applicationContext)
                val result = OrderRepositoryImpl(database).syncOrders()
                if (result.isFailure) {
                    android.util.Log.w("EloryPush", "New-order push received but order sync failed", result.exceptionOrNull())
                }
            } catch (error: Exception) {
                android.util.Log.w("EloryPush", "Unable to validate session or refresh orders after push", error)
            }
        }"""
fcm = replace(fcm, old_fcm, new_fcm, "Require active matching staff session for push notifications")
write(fcm_path, fcm)
