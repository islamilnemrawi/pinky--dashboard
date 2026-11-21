#!/usr/bin/env python3
"""Apply and verify all Elory session-isolation overlays."""
from pathlib import Path
import subprocess
import sys
from session_isolation_common import ROOT, JAVA, read

for name in (
    "apply-elory-session-cache.py",
    "apply-elory-sync-manager.py",
    "apply-elory-fcm.py",
    "apply-elory-viewmodel.py",
):
    subprocess.run([sys.executable, str(Path(__file__).with_name(name))], check=True)

checks = {
    "Room cache cleaner installed": "database.clearAllTables()" in read(JAVA + "data/local/SessionCacheCleaner.kt"),
    "Auth clears local cache": "sessionCacheCleaner.clear()" in read(JAVA + "data/repository/RepositoriesImpl.kt"),
    "Logout clears order notifications": "cancelAllNotifications()" in read(JAVA + "data/repository/RepositoriesImpl.kt") and "notificationManager.cancelAll()" in read(JAVA + "core/notification/PinkyNotificationManager.kt"),
    "Login clears prior cache": "clearLocalSession()" in read(JAVA + "data/repository/RepositoriesImpl.kt").split("override suspend fun login(", 1)[1],
    "Central sync is cancellable": "centralSyncJob?.cancelAndJoin()" in read(JAVA + "ui/PinkyViewModel.kt"),
    "Central sync requires active auth": "if (!sessionActive || !SupabaseClient.isAuthenticated) return" in read(JAVA + "ui/PinkyViewModel.kt"),
    "Logout immediately invalidates push registration": "elory_push_registration" in read(JAVA + "ui/PinkyViewModel.kt"),
    "Periodic sync can stop": "suspend fun stopPeriodicSync()" in read(JAVA + "core/sync/OrderSyncManager.kt"),
    "Notification jobs stop at logout": "notificationJob?.cancel()" in read(JAVA + "core/sync/OrderSyncManager.kt"),
    "Sync rejects logged-out work": "if (!sessionActive) false else activeSyncJobs.add(callerJob)" in read(JAVA + "core/sync/OrderSyncManager.kt"),
    "Push notifications verify the saved staff account": "registered_user_id" in read(JAVA + "core/notification/EloryFirebaseMessagingService.kt") and "initializeAuthSession()" in read(JAVA + "core/notification/EloryFirebaseMessagingService.kt"),
    "Push handler rechecks logout marker before posting": "currentRegisteredUserId" in read(JAVA + "core/notification/EloryFirebaseMessagingService.kt"),
    "Push handler requires the live Supabase session": "!SupabaseClient.isAuthenticated" in read(JAVA + "core/notification/EloryFirebaseMessagingService.kt"),
    "Push auth check is time-bounded": "withTimeoutOrNull(10_000L)" in read(JAVA + "core/notification/EloryFirebaseMessagingService.kt"),
    "Session initialization propagates cancellation": "catch (e: kotlinx.coroutines.CancellationException)" in read(JAVA + "data/repository/RepositoriesImpl.kt") and "SupabaseClient.isSessionReady = true\\n            throw e" in read(JAVA + "data/repository/RepositoriesImpl.kt"),
    "Room regression test installed": (ROOT / "app/src/test/java/com/pinky/dashboard/SessionCacheIsolationTest.kt").is_file(),
}
for label, passed in checks.items():
    if not passed:
        raise SystemExit("Session isolation validation failed: " + label)
    print("PASS:", label)
print("Applied Elory account-boundary cache isolation and authenticated-only sync.")
