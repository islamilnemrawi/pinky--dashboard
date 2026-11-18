import os
from pathlib import Path

root = Path(os.environ["PROJECT_DIR"]).resolve()

def patch(path, old, new, label):
    file = root / path
    source = file.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one source anchor, found {count}")
    file.write_text(source.replace(old, new, 1), encoding="utf-8")

# Keep saved remote URLs separate from newly selected local URIs. This avoids
# trying to upload already-hosted images again and lets removals persist.
product = "app/src/main/java/com/pinky/dashboard/ui/screens/products/ProductEditDialog.kt"
patch(
    product,
    '    var selectedProductImageUris by remember { mutableStateOf<List<Uri>>(emptyList()) }',
    '''    var selectedProductImageUris by remember { mutableStateOf<List<Uri>>(emptyList()) }
    var existingProductImageUrls by remember(initialProduct?.id) {
        mutableStateOf(
            (listOfNotNull(initialProduct?.imageUrl?.takeIf { it.isNotBlank() }) +
                initialProduct?.gallery.orEmpty())
                .filter { it.isNotBlank() }
                .distinct()
        )
    }''',
    "Saved product gallery state"
)

saved_gallery_ui = '''                                if (existingProductImageUrls.isNotEmpty()) {
                                    Text("الصور المحفوظة حاليًا — اضغط علامة × لحذف أي صورة", style = MaterialTheme.typography.labelSmall, color = PinkPrimary)
                                    LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                                        items(existingProductImageUrls, key = { it }) { image ->
                                            Box(Modifier.size(76.dp).clip(RoundedCornerShape(10.dp)).border(1.dp, PinkPrimary, RoundedCornerShape(10.dp))) {
                                                AsyncImage(model = image, contentDescription = "صورة محفوظة للمنتج", contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
                                                Surface(Modifier.align(Alignment.TopEnd).padding(3.dp), shape = RoundedCornerShape(50), color = MaterialTheme.colorScheme.surface.copy(alpha = 0.92f)) {
                                                    IconButton(onClick = { existingProductImageUrls = existingProductImageUrls.filterNot { it == image } }, modifier = Modifier.size(25.dp)) {
                                                        Icon(Icons.Outlined.Close, contentDescription = "حذف الصورة المحفوظة", tint = MaterialTheme.colorScheme.error, modifier = Modifier.size(16.dp))
                                                    }
                                                }
                                            }
                                        }
                                    }
                                    Text(existingProductImageUrls.size.toString() + " صورة محفوظة", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }

'''
patch(
    product,
    '                                if (selectedProductImageUris.isNotEmpty()) {',
    saved_gallery_ui + '                                if (selectedProductImageUris.isNotEmpty()) {',
    "Saved gallery thumbnails and per-image deletion"
)

old_save = '''                                        val finalImageUrl = uploadedProductImages.firstOrNull() ?: imageUrl
                                        val finalGallery = if (uploadedProductImages.isNotEmpty()) {
                                            val previousCover = initialProduct?.imageUrl?.takeIf { it.isNotBlank() && it != finalImageUrl }
                                            (initialProduct?.gallery.orEmpty() + listOfNotNull(previousCover) + uploadedProductImages.drop(1)).distinct()
                                        } else initialProduct?.gallery ?: emptyList()
'''
new_save = '''                                        val finalImageUrl = existingProductImageUrls.firstOrNull()
                                            ?: uploadedProductImages.firstOrNull()
                                            ?: ""
                                        val newGalleryImages = uploadedProductImages.drop(
                                            if (existingProductImageUrls.isEmpty()) 1 else 0
                                        )
                                        val finalGallery = (existingProductImageUrls.drop(1) + newGalleryImages).distinct()
'''
patch(product, old_save, new_save, "Non-duplicating gallery persistence")

# Show the complete UUID on each product card and provide a dedicated copy action.
products = "app/src/main/java/com/pinky/dashboard/ui/screens/products/ProductsScreen.kt"
copy_anchor = '''            CopyTextButton(value = productCopyText, contentDescription = "نسخ بيانات المنتج", modifier = Modifier.testTag("copy_product_${product.id}"))'''
copy_row = copy_anchor + '''
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("معرّف المنتج: ${product.id}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                CopyTextButton(
                    value = product.id,
                    contentDescription = "نسخ معرّف المنتج",
                    modifier = Modifier.testTag("copy_product_id_${product.id}")
                )
            }'''
patch(products, copy_anchor, copy_row, "Visible product ID and copy action")

# Static source-level guards: fail the APK build if a future patch drops any behavior.
dialog_source = (root / product).read_text(encoding="utf-8")
list_source = (root / products).read_text(encoding="utf-8")
checks = {
    "saved gallery is hydrated from cover and gallery": "initialProduct?.gallery.orEmpty()" in dialog_source,
    "saved images can be removed": "existingProductImageUrls = existingProductImageUrls.filterNot" in dialog_source,
    "saved images remain URLs, not re-uploaded": "existingProductImageUrls.firstOrNull()" in dialog_source,
    "gallery is de-duplicated on save": "existingProductImageUrls.drop(1) + newGalleryImages).distinct()" in dialog_source,
    "full product ID is visible": 'Text("معرّف المنتج: ${product.id}"' in list_source,
    "product ID has its own copy action": 'contentDescription = "نسخ معرّف المنتج"' in list_source,
}
for label, passed in checks.items():
    if not passed:
        raise SystemExit("Product media/ID regression: " + label)
    print("PASS:", label)
