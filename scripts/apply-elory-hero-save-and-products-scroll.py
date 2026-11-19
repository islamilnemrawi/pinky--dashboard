from pathlib import Path
import os
root = Path(os.environ["PROJECT_DIR"])

remote = root / "app/src/main/java/com/pinky/dashboard/data/remote/SupabaseClient.kt"
s = remote.read_text(encoding="utf-8")
for method in ("getSiteCustomizationDraft", "clearSiteCustomizationDraft"):
    old = "suspend fun " + method + "(@Body params: Map<String, Any>)"
    new = "suspend fun " + method + "(@Body params: Map<String, @JvmSuppressWildcards Any>)"
    if old in s:
        s = s.replace(old, new, 1)
    elif new not in s:
        raise SystemExit("Missing expected RPC method: " + method)
remote.write_text(s, encoding="utf-8")

# Replace the fixed header + nested list with one LazyColumn so all header
# controls scroll away together and the product cards gain the freed space.
p = root / "app/src/main/java/com/pinky/dashboard/ui/screens/products/ProductsScreen.kt"
s = p.read_text(encoding="utf-8")
old = """        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            if (products.isNotEmpty()) {"""
new = """        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(innerPadding).testTag("products_list"),
            contentPadding = PaddingValues(bottom = 96.dp),
            verticalArrangement = Arrangement.spacedBy(0.dp)
        ) {
            item {
            if (products.isNotEmpty()) {"""
if old not in s:
    raise SystemExit("Products root Column did not match")
s = s.replace(old, new, 1)

old = """                }
            }
            // Header: Search, Bulk Mode, Import Excel"""
new = """                }
            }
            }
            // Header: Search, Bulk Mode, Import Excel
            item {"""
if old not in s:
    raise SystemExit("Stock summary boundary did not match")
s = s.replace(old, new, 1)

old = """                }
            }

            if (isPrimaryOwner) {
                OwnerDataResetControls("""
new = """                }
            }
            }

            if (isPrimaryOwner) {
                item {
                OwnerDataResetControls("""
if old not in s:
    raise SystemExit("Search header boundary did not match")
s = s.replace(old, new, 1)

old = """                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                )
            }
            productOperationError?.let { message ->
                Text(message, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(horizontal = 16.dp))
            }

            // Products List
            if (filteredProducts.isEmpty()) {
                EmptyStateCard("""
new = """                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                )
                }
            }
            productOperationError?.let { message ->
                item {
                    Text(message, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(horizontal = 16.dp))
                }
            }

            // Products List
            if (filteredProducts.isEmpty()) {
                item {
                EmptyStateCard("""
if old not in s:
    raise SystemExit("Owner tools / empty state boundary did not match")
s = s.replace(old, new, 1)

old = """                    modifier = Modifier.padding(16.dp)
                )
            } else {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .testTag("products_list"),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(filteredProducts, key = { it.id }) { product ->"""
new = """                    modifier = Modifier.padding(16.dp)
                )
                }
            } else {
                    items(filteredProducts, key = { it.id }) { product ->"""
if old not in s:
    raise SystemExit("Nested products LazyColumn boundary did not match")
s = s.replace(old, new, 1)

old = """                    }
                }
            }
        }
    }

    if (showAddEditDialog) {"""
new = """                    }
            }
    }
    }

    if (showAddEditDialog) {"""
if old not in s:
    raise SystemExit("Nested products LazyColumn closing boundary did not match")
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# Assertions are deliberately narrow: no backend schema or cloud config is touched.
remoteText = remote.read_text(encoding="utf-8")
productText = p.read_text(encoding="utf-8")
for method in ("getSiteCustomizationDraft", "clearSiteCustomizationDraft"):
    if method + "(@Body params: Map<String, @JvmSuppressWildcards Any>)" not in remoteText:
        raise SystemExit("Retrofit wildcard fix missing for " + method)
if "contentPadding = PaddingValues(bottom = 96.dp)" not in productText:
    raise SystemExit("Collapsing products LazyColumn was not applied")
if productText.count("items(filteredProducts, key = { it.id })") != 1:
    raise SystemExit("Product cards are not in the shared scrolling list")
print("PASS: Retrofit RPC wildcard signatures")
print("PASS: shared collapsing products list")
