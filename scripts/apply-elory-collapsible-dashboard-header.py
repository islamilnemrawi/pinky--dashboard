from pathlib import Path
import os

ROOT = Path(os.environ["PROJECT_DIR"]).resolve()
APP = ROOT / "app/src/main/java/com/pinky/dashboard/ui/PinkyApp.kt"
TOP = ROOT / "app/src/main/java/com/pinky/dashboard/ui/components/PinkyNavigationComponents.kt"

def one(path, old, new, label):
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

# One shared scroll behavior belongs to the app shell, so every scrollable
# dashboard section can collapse the same app header consistently.
one(APP,
'''import androidx.compose.ui.Modifier
''',
'''import androidx.compose.ui.Modifier
import androidx.compose.ui.input.nestedscroll.nestedScroll
''',
"Import nested scroll support")

one(APP,
'''@Composable
fun PinkyApp(
''',
'''@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PinkyApp(
''',
"Opt into Material 3 app-bar scroll APIs")

one(APP,
'''    val snackbarHostState = remember { SnackbarHostState() }
''',
'''    val snackbarHostState = remember { SnackbarHostState() }
    val dashboardAppBarState = rememberTopAppBarState()
    val dashboardAppBarScrollBehavior =
        TopAppBarDefaults.exitUntilCollapsedScrollBehavior(dashboardAppBarState)

    // Every section starts with its full header; scrolling then collapses it
    // to the compact toolbar instead of removing navigation or actions.
    LaunchedEffect(currentSection) {
        dashboardAppBarState.heightOffset = 0f
        dashboardAppBarState.contentOffset = 0f
    }
''',
"Create shared collapsible app bar state")

one(APP,
'''                            onRefreshClick = { viewModel.performCentralizedSync() }
''',
'''                            onRefreshClick = { viewModel.performCentralizedSync() },
                            scrollBehavior = dashboardAppBarScrollBehavior
''',
"Connect app bar scroll behavior")

one(APP,
'''                    modifier = Modifier
                        .fillMaxSize()
                        .testTag("pinky_app_scaffold")
''',
'''                    modifier = Modifier
                        .fillMaxSize()
                        .nestedScroll(dashboardAppBarScrollBehavior.nestedScrollConnection)
                        .testTag("pinky_app_scaffold")
''',
"Connect all dashboard section scrolling")

one(TOP,
'''    onRefreshClick: () -> Unit = {},
    modifier: Modifier = Modifier
''',
'''    onRefreshClick: () -> Unit = {},
    scrollBehavior: TopAppBarScrollBehavior,
    modifier: Modifier = Modifier
''',
"Expose shared scroll behavior")

one(TOP,
'''    TopAppBar(
''',
'''    MediumTopAppBar(
''',
"Use expanding and compact app bar")

one(TOP,
'''        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = MaterialTheme.colorScheme.surface,
            titleContentColor = MaterialTheme.colorScheme.onSurface
        ),
''',
'''        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = MaterialTheme.colorScheme.surface,
            titleContentColor = MaterialTheme.colorScheme.onSurface
        ),
        scrollBehavior = scrollBehavior,
''',
"Attach scroll behavior to app bar")

# Guard the behavior contract and the essential controls that must remain visible.
app = APP.read_text(encoding="utf-8")
top = TOP.read_text(encoding="utf-8")
checks = {
    "shared nested-scroll connection is installed on app shell":
        ".nestedScroll(dashboardAppBarScrollBehavior.nestedScrollConnection)" in app,
    "PinkyApp opts into experimental Material 3 app-bar APIs":
        "@OptIn(ExperimentalMaterial3Api::class)" in app and "@Composable\\nfun PinkyApp(" in app,
    "section changes restore the expanded header":
        "LaunchedEffect(currentSection)" in app and "dashboardAppBarState.heightOffset = 0f" in app,
    "app bar uses exit-until-collapsed behavior":
        "exitUntilCollapsedScrollBehavior(dashboardAppBarState)" in app,
    "app bar remains a MediumTopAppBar with compact state":
        "MediumTopAppBar(" in top and "scrollBehavior = scrollBehavior" in top,
    "navigation menu remains present":
        'testTag("top_bar_menu_btn")' in top,
    "refresh action remains present":
        'testTag("top_bar_refresh_btn")' in top,
    "notification action remains present":
        'testTag("top_bar_notif_btn")' in top,
}
for label, passed in checks.items():
    if not passed:
        raise SystemExit("Collapsible header regression: " + label)
    print("PASS:", label)

print("PASS: shared dashboard header collapses across nested-scroll sections while preserving essential toolbar actions.")
