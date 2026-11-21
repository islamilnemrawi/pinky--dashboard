from session_isolation_common import *

vm_path = JAVA + "ui/PinkyViewModel.kt"
vm = read(vm_path)
vm = add_import(vm, "import com.pinky.dashboard.core.notification.PinkyNotificationManager", "import com.pinky.dashboard.core.notification.EloryPushTokenRegistrar\n")
vm = add_import(vm, "import kotlinx.coroutines.Job", "import kotlinx.coroutines.Dispatchers\n")
vm = add_import(vm, "import kotlinx.coroutines.cancelAndJoin", "import kotlinx.coroutines.Job\n")
vm = replace(vm,
'''    private var autoRefreshJob: kotlinx.coroutines.Job? = null

    init {
        viewModelScope.launch {
            // 1. Load, restore or refresh the local/silent Owner session completely sequentially
            val isAuthenticated = authRepository.initializeAuthSession()
            android.util.Log.i("SupabaseAuth", "AUTH_SESSION_READY - authenticated = $isAuthenticated")

            // 2. Start background periodic sync
            syncManager.startPeriodicSync()

            // 3. Perform the initial data sync only when authenticated/sandbox is ready
            if (isAuthenticated) {
                performCentralizedSync()
            }

            // 4. Start the 60-second background automatic refresh and sync timer
            startAutoRefreshTimer()
        }
    }

    suspend fun login(email: String, pass: String): Result<AdminUser> {
        val result = authRepository.login(email, pass)
        if (result.isSuccess) {
            // Immediately sync data upon a manual successful login
            performCentralizedSync()
        }
        return result
    }

    fun logout() {
        viewModelScope.launch {
            authRepository.logout()
        }
    }

    fun performCentralizedSync() {
        if (_isRefreshing.value) return
        _isRefreshing.value = true
        _syncError.value = null

        // Reset/restart the 60-second automatic refresh timer to ensure manual clicks reset the countdown
        startAutoRefreshTimer()

        viewModelScope.launch {''',
'''    private var autoRefreshJob: Job? = null
    private var centralSyncJob: Job? = null
    @Volatile private var sessionActive = false
    private val initialPaymentMethods = _paymentMethods.value

    init {
        viewModelScope.launch {
            syncManager.stopPeriodicSync()
            val isAuthenticated = authRepository.initializeAuthSession()
            android.util.Log.i("SupabaseAuth", "AUTH_SESSION_READY - authenticated = $isAuthenticated")
            if (isAuthenticated && SupabaseClient.isAuthenticated) {
                startAuthenticatedBackgroundWork()
                performCentralizedSync()
            } else {
                resetSessionBoundState()
            }
        }
    }

    private fun startAuthenticatedBackgroundWork() {
        if (!SupabaseClient.isAuthenticated) return
        sessionActive = true
        syncManager.startPeriodicSync()
        startAutoRefreshTimer()
    }

    private fun resetSessionBoundState() {
        _currentSection.value = DashboardSection.HOME
        _selectedOrder.value = null
        _isPrimaryOwner.value = false
        _coupons.value = emptyList()
        _primeSubscribers.value = emptyList()
        _profitDashboard.value = null
        _profitDashboardLoading.value = false
        _profitDashboardError.value = null
        _staffMembers.value = emptyList()
        _websiteConfig.value = WebsiteConfig()
        _websiteDraftSaveState.value = "idle"
        _websiteSaveState.value = "idle"
        _notifications.value = emptyList()
        _paymentMethods.value = initialPaymentMethods
        _lastPersistedPaymentMethods.value = initialPaymentMethods
        _isRefreshing.value = false
        _lastSyncTimestamp.value = null
        _syncError.value = null
    }

    private suspend fun stopAuthenticatedBackgroundWork(cancelRefreshTimer: Boolean = true) {
        sessionActive = false
        if (cancelRefreshTimer) {
            autoRefreshJob?.cancelAndJoin()
            autoRefreshJob = null
        }
        centralSyncJob?.cancelAndJoin()
        centralSyncJob = null
        syncManager.stopPeriodicSync()
        _isRefreshing.value = false
        resetSessionBoundState()
    }

    suspend fun login(email: String, pass: String): Result<AdminUser> {
        stopAuthenticatedBackgroundWork()
        val result = authRepository.login(email, pass)
        if (result.isSuccess) {
            startAuthenticatedBackgroundWork()
            performCentralizedSync()
        }
        return result
    }

    fun logout() {
        viewModelScope.launch {
            appContext.getSharedPreferences("elory_push_registration", Context.MODE_PRIVATE).edit().clear().apply()
            SupabaseClient.clearSession()
            runCatching { PinkyNotificationManager(appContext).cancelAllNotifications() }
            stopAuthenticatedBackgroundWork()
            runCatching { authRepository.logout() }
                .onFailure { error ->
                    android.util.Log.e("EloryAuth", "Logout cleanup failed.", error)
                    notifyUser("تعذر إكمال تنظيف بيانات الجلسة المحلية. أعد فتح التطبيق قبل تسجيل الدخول مرة أخرى.")
                }
        }
    }

    fun performCentralizedSync() {
        if (!sessionActive || !SupabaseClient.isAuthenticated || _isRefreshing.value) return
        _isRefreshing.value = true
        _syncError.value = null
        centralSyncJob = viewModelScope.launch {''', "Bind ViewModel lifecycle to authenticated session")
vm = replace(vm,
'''            } catch (e: Exception) {
                _syncError.value = "خطأ غير متوقع: ${e.message}"
                android.util.Log.e("SupabaseSync", "Unexpected sync exception", e)
            } finally {
                _isRefreshing.value = false
            }
        }
    }

    private fun startAutoRefreshTimer() {
        autoRefreshJob?.cancel()
        autoRefreshJob = viewModelScope.launch {
            while (isActive) {
                kotlinx.coroutines.delay(60000L) // 60 seconds
                try {
                    android.util.Log.d("SupabaseAuth", "Periodic check: verifying session expiry...")
                    authRepository.refreshAuthSessionIfNeeded()
                } catch (e: Exception) {
                    android.util.Log.e("SupabaseAuth", "Background session refresh check failed: ${e.message}")
                }
                performCentralizedSync()
            }
        }
    }''',
'''            } catch (e: kotlinx.coroutines.CancellationException) {
                throw e
            } catch (e: Exception) {
                _syncError.value = "خطأ غير متوقع: ${e.message}"
                android.util.Log.e("SupabaseSync", "Unexpected sync exception", e)
            } finally {
                _isRefreshing.value = false
                centralSyncJob = null
            }
        }
    }

    private fun startAutoRefreshTimer() {
        if (!sessionActive) return
        autoRefreshJob?.cancel()
        autoRefreshJob = viewModelScope.launch {
            while (isActive && sessionActive) {
                kotlinx.coroutines.delay(60000L)
                if (!sessionActive) break
                try {
                    val refreshed = authRepository.refreshAuthSessionIfNeeded()
                    if (!refreshed && !SupabaseClient.isAuthenticated) {
                        stopAuthenticatedBackgroundWork(cancelRefreshTimer = false)
                        break
                    }
                } catch (e: kotlinx.coroutines.CancellationException) {
                    throw e
                } catch (e: Exception) {
                    android.util.Log.e("SupabaseAuth", "Background session refresh check failed: ${e.message}")
                    if (!SupabaseClient.isAuthenticated) {
                        stopAuthenticatedBackgroundWork(cancelRefreshTimer = false)
                        break
                    }
                }
                if (sessionActive && SupabaseClient.isAuthenticated) performCentralizedSync()
            }
        }
    }''', "Stop background work after session revocation")
vm = replace(vm,
'''    fun manualSync() {
        viewModelScope.launch {
            syncManager.performSync()
        }
    }''',
'''    fun manualSync() {
        if (!sessionActive || !SupabaseClient.isAuthenticated) return
        viewModelScope.launch {
            if (sessionActive && SupabaseClient.isAuthenticated) syncManager.performSync()
        }
    }''', "Gate manual sync")
vm = replace(vm,
'''    fun triggerTestNotification() {
        syncManager.triggerTestNotification()''',
'''    fun triggerTestNotification() {
        if (!sessionActive || !SupabaseClient.isAuthenticated) return
        syncManager.triggerTestNotification()''', "Gate test notification")
vm = replace(vm,
'''    fun updateSyncInterval(interval: SyncInterval) {
        syncManager.updateInterval(interval)
    }''',
'''    fun updateSyncInterval(interval: SyncInterval) {
        if (sessionActive && SupabaseClient.isAuthenticated) syncManager.updateInterval(interval)
    }''', "Gate sync interval updates")
vm = replace(vm,
'''        autoRefreshJob?.cancel()
        syncManager.destroy()''',
'''        autoRefreshJob?.cancel()
        centralSyncJob?.cancel()
        syncManager.destroy()''', "Cancel central sync when ViewModel is cleared")
write(vm_path, vm)
