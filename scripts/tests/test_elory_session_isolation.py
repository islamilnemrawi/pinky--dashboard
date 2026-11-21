import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ElorySessionIsolationPatchTest(unittest.TestCase):
    def setUp(self):
        source_root = Path(os.environ["PROJECT_DIR"]).resolve()
        self.temp_dir = tempfile.TemporaryDirectory(prefix="elory-session-isolation-")
        self.project = Path(self.temp_dir.name) / "project"
        shutil.copytree(
            source_root,
            self.project,
            ignore=shutil.ignore_patterns(".gradle", "build", ".kotlin", "*.zip", ".env", "debug.keystore"),
        )
        self.script = Path(__file__).resolve().parents[1] / "apply-elory-session-isolation.py"

    def tearDown(self):
        self.temp_dir.cleanup()

    def apply_patch(self):
        env = os.environ.copy()
        env["PROJECT_DIR"] = str(self.project)
        return subprocess.run(
            [sys.executable, str(self.script)],
            cwd=self.script.parents[1],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_patch_adds_account_scoped_cache_cleanup_and_session_gates(self):
        result = self.apply_patch()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        cleaner = self.project / "app/src/main/java/com/pinky/dashboard/data/local/SessionCacheCleaner.kt"
        self.assertTrue(cleaner.is_file())
        self.assertIn("database.clearAllTables()", cleaner.read_text(encoding="utf-8"))

        auth = (self.project / "app/src/main/java/com/pinky/dashboard/data/repository/RepositoriesImpl.kt").read_text(encoding="utf-8")
        self.assertIn("sessionCacheCleaner.clear()", auth)
        self.assertIn("cancelAllNotifications()", auth)
        notification_manager = (self.project / "app/src/main/java/com/pinky/dashboard/core/notification/PinkyNotificationManager.kt").read_text(encoding="utf-8")
        self.assertIn("notificationManager.cancelAll()", notification_manager)
        self.assertIn("clearLocalSession()", auth[auth.index("override suspend fun login("):])

        view_model = (self.project / "app/src/main/java/com/pinky/dashboard/ui/PinkyViewModel.kt").read_text(encoding="utf-8")
        self.assertIn("centralSyncJob?.cancelAndJoin()", view_model)
        self.assertIn("syncManager.stopPeriodicSync()", view_model)
        self.assertIn("if (!sessionActive || !SupabaseClient.isAuthenticated) return", view_model)

        sync_manager = (self.project / "app/src/main/java/com/pinky/dashboard/core/sync/OrderSyncManager.kt").read_text(encoding="utf-8")
        self.assertIn("suspend fun stopPeriodicSync()", sync_manager)
        self.assertIn("if (!sessionActive)", sync_manager)
        self.assertIn("notificationJob?.cancel()", sync_manager)

        fcm = (self.project / "app/src/main/java/com/pinky/dashboard/core/notification/EloryFirebaseMessagingService.kt").read_text(encoding="utf-8")
        self.assertIn("registered_user_id", fcm)
        self.assertIn("initializeAuthSession()", fcm)

        regression = self.project / "app/src/test/java/com/pinky/dashboard/SessionCacheIsolationTest.kt"
        self.assertTrue(regression.is_file())
        kotlin_test = regression.read_text(encoding="utf-8")
        self.assertIn("syncManagerRejectsReadsOutsideAnActiveSession", kotlin_test)
        self.assertIn("must remain reusable after a ViewModel is cleared", kotlin_test)
        self.assertIn("clearRemovesEveryCachedTableAndKeepsTheRoomSchemaUsable", kotlin_test)

    def test_patch_is_idempotent(self):
        first = self.apply_patch()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        tracked = [
            self.project / "app/src/main/java/com/pinky/dashboard/data/local/SessionCacheCleaner.kt",
            self.project / "app/src/main/java/com/pinky/dashboard/data/repository/RepositoriesImpl.kt",
            self.project / "app/src/main/java/com/pinky/dashboard/ui/PinkyViewModel.kt",
            self.project / "app/src/main/java/com/pinky/dashboard/core/sync/OrderSyncManager.kt",
            self.project / "app/src/main/java/com/pinky/dashboard/core/notification/EloryFirebaseMessagingService.kt",
            self.project / "app/src/main/java/com/pinky/dashboard/core/notification/PinkyNotificationManager.kt",
        ]
        before = {path: path.read_bytes() for path in tracked}
        second = self.apply_patch()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        after = {path: path.read_bytes() for path in tracked}
        self.assertEqual(before, after, "Reapplying the session-isolation patch changed files twice")


if __name__ == "__main__":
    unittest.main()
