# Dashboard Session Isolation Implementation Plan

> **For agentic workers:** Use the existing GitHub Actions build workflow to validate each task before updating the pull request.

**Goal:** Prevent cached dashboard data and background synchronization from crossing staff-account boundaries.

**Architecture:** Keep the existing Room schema and remote Supabase data unchanged. Add a small Room cache-cleaner abstraction that clears only local cached tables at authentication boundaries, and make ViewModel-owned background sync start only for an authenticated session and stop before logout cleanup.

**Tech Stack:** Kotlin, AndroidX Room, Kotlin coroutines/Flow, Robolectric, Gradle, GitHub Actions.

**Spec:** Phase 1 approved by the user: session isolation and dashboard permissions, without deleting cloud data or removing features.

## Global Constraints
- Do not change Supabase tables, RLS, Edge Functions, payment flows, or cloud records.
- Do not use Room destructive migrations or change the Room schema version.
- Do not alter existing feature behavior except blocking cross-account cached data exposure.
- Keep the existing permission-aware navigation overlay and its checks intact.
- Never run periodic or central data sync after the authenticated session ends.
- Fail closed if local cache cleanup fails; do not allow a new account to use stale local rows.

## Review Focus
- A Room cache clear removes all cached user data but leaves the database schema usable.
- Logout waits for in-flight central sync cancellation before clearing the cache.
- A rejected/expired restored session clears local cached rows before the login screen can expose them.
- A failed login cannot reveal the previous account's cached records.
- Background periodic sync does not restart while logged out and restarts after successful login.

---

### Task 1: Test the account-boundary cache cleaner

**Files:**
- Create: `app/src/test/java/com/pinky/dashboard/SessionCacheIsolationTest.kt`
- Create later: `app/src/main/java/com/pinky/dashboard/data/local/SessionCacheCleaner.kt`

- [ ] Write a Robolectric Room test that inserts one row into each of the eight Room tables, invokes `SessionCacheCleaner.clear()`, asserts all tables are empty, then inserts a new row to prove the schema remains usable.
- [ ] Run the GitHub Actions unit-test workflow and confirm the test fails because `SessionCacheCleaner` is not yet implemented.

### Task 2: Implement the local cache boundary

**Files:**
- Create: `app/src/main/java/com/pinky/dashboard/data/local/SessionCacheCleaner.kt`
- Modify: `app/src/main/java/com/pinky/dashboard/ui/PinkyViewModel.kt`

- [ ] Implement `SessionCacheCleaner(database: PinkyDatabase).clear()` using Room's non-destructive `clearAllTables()` on `Dispatchers.IO`.
- [ ] Invoke it after cancelling in-flight sync when logging out, before a new login attempt, and when restoring or refreshing a session fails.
- [ ] Clear session-bound in-memory state (selected order, staff, notifications, coupons, Prime subscribers, reports, website settings, payment settings and sync status) at the same boundaries.

### Task 3: Stop background work outside authenticated sessions

**Files:**
- Modify: `app/src/main/java/com/pinky/dashboard/core/sync/OrderSyncManager.kt`
- Modify: `app/src/main/java/com/pinky/dashboard/ui/PinkyViewModel.kt`

- [ ] Add an idempotent `stopPeriodicSync()` method.
- [ ] Track the central sync job so logout can cancel and join it before cache cleanup.
- [ ] Start periodic and automatic refresh only after session restoration or login succeeds.
- [ ] Stop periodic work and clear local session state when token refresh invalidates the current user.

### Task 4: Verify

- [ ] Run `:app:testDebugUnitTest`.
- [ ] Run `:app:assembleDebug`.
- [ ] Inspect the generated source and APK artifacts and verify that only local cache rows are cleared; no Supabase migrations, cloud data, or existing features changed.
