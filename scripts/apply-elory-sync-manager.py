from session_isolation_common import *

sync_path = JAVA + "core/sync/OrderSyncManager.kt"
sync = read(sync_path)
sync = replace(sync,
'''    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var syncJob: Job? = null''',
'''    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val syncLock = Any()
    private val activeSyncJobs = mutableSetOf<Job>()
    @Volatile private var sessionActive = false
    private var syncJob: Job? = null
    private var notificationJob: Job? = null''', "Track sync session and active jobs")
sync = replace(sync,
'''    fun updateInterval(interval: SyncInterval) {
        _syncInterval.value = interval
        startPeriodicSync()
    }

    fun startPeriodicSync() {
        syncJob?.cancel()
        val interval = _syncInterval.value
        if (interval == SyncInterval.MANUAL) return

        syncJob = scope.launch {
            while (isActive) {
                delay(interval.minutes * 60 * 1000L)
                performSync()
            }
        }
    }

    suspend fun performSync(): Result<Unit> {
        _isSyncing.value = true
        return try {
            val result = orderRepository.syncOrders()
            _lastSyncTime.value = System.currentTimeMillis()
            result
        } finally {
            _isSyncing.value = false
        }
    }''',
'''    fun updateInterval(interval: SyncInterval) {
        _syncInterval.value = interval
        if (sessionActive) startPeriodicSync()
    }

    fun startPeriodicSync() {
        val interval = _syncInterval.value
        synchronized(syncLock) {
            sessionActive = true
            syncJob?.cancel()
            syncJob = if (interval == SyncInterval.MANUAL) null else scope.launch {
                while (isActive && sessionActive) {
                    delay(interval.minutes * 60 * 1000L)
                    if (sessionActive) performSync()
                }
            }
        }
    }

    suspend fun stopPeriodicSync() {
        val jobs = synchronized(syncLock) {
            sessionActive = false
            val periodic = syncJob
            periodic?.cancel()
            syncJob = null
            val notification = notificationJob
            notification?.cancel()
            notificationJob = null
            (activeSyncJobs.toList() + listOfNotNull(periodic, notification)).distinct()
        }
        jobs.forEach { it.cancelAndJoin() }
        _isSyncing.value = false
    }

    suspend fun performSync(): Result<Unit> {
        val callerJob = currentCoroutineContext()[Job]
            ?: return Result.failure(IllegalStateException("No active sync job"))
        val registered = synchronized(syncLock) {
            if (!sessionActive) false else activeSyncJobs.add(callerJob)
        }
        if (!registered) return Result.failure(IllegalStateException("Dashboard session is not active"))
        _isSyncing.value = true
        return try {
            if (!sessionActive) throw CancellationException("Dashboard session ended")
            val result = orderRepository.syncOrders()
            if (sessionActive) _lastSyncTime.value = System.currentTimeMillis()
            result
        } finally {
            synchronized(syncLock) { activeSyncJobs.remove(callerJob) }
            if (synchronized(syncLock) { activeSyncJobs.isEmpty() }) _isSyncing.value = false
        }
    }''', "Gate and cancel sync outside active sessions")
sync = replace(sync,
'''    fun triggerTestNotification() {
        scope.launch {
            val orders = orderRepository.getOrdersFlow().first()
            val sampleOrder = orders.firstOrNull { it.status == OrderStatus.NEW } ?: orders.firstOrNull()
            if (sampleOrder != null) {
                notificationManager.showNewOrderNotification(sampleOrder)
            }
        }
    }''',
'''    fun triggerTestNotification() {
        notificationJob?.cancel()
        notificationJob = scope.launch {
            if (!sessionActive) return@launch
            val orders = orderRepository.getOrdersFlow().first()
            val sampleOrder = orders.firstOrNull { it.status == OrderStatus.NEW } ?: orders.firstOrNull()
            if (sessionActive && sampleOrder != null) {
                notificationManager.showNewOrderNotification(sampleOrder)
            }
        }
    }''', "Gate notification lookup")
sync = replace(sync,
'''    fun destroy() {
        syncJob?.cancel()
    }''',
'''    fun destroy() {
        synchronized(syncLock) {
            sessionActive = false
            syncJob?.cancel()
            syncJob = null
            notificationJob?.cancel()
            notificationJob = null
            activeSyncJobs.forEach { it.cancel() }
        }
        scope.cancel()
    }''', "Stop all sync work when manager is destroyed")
write(sync_path, sync)
