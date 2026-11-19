from pathlib import Path
import os

root = Path(os.environ["PROJECT_DIR"]).resolve()

product = root / "app/src/main/java/com/pinky/dashboard/ui/screens/products/ProductEditDialog.kt"
source = product.read_text(encoding="utf-8")

def replace_once(old, new, label):
    global source
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    source = source.replace(old, new, 1)

# Make the two independent switches' effects explicit without changing their state
# or save semantics.
replace_once(
    'Text("المنتج نشط ومتاح للشراء في الموقع", fontWeight = FontWeight.SemiBold)',
    '''Column(Modifier.weight(1f)) {
                                Text("المنتج نشط ومتاح للشراء في الموقع", fontWeight = FontWeight.SemiBold)
                                Text("إيقافه يخفي المنتج من المتجر ويمنع إتمام شرائه.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }''',
    "Product availability helper"
)
replace_once(
    'Text("عرض كمنتج مميز بالصفحة الرئيسية ⭐", fontWeight = FontWeight.SemiBold)',
    '''Column(Modifier.weight(1f)) {
                                Text("عرض كمنتج مميز بالصفحة الرئيسية ⭐", fontWeight = FontWeight.SemiBold)
                                Text("إيقافه يخفيه من الرئيسية فقط، ويظل ظاهرًا داخل قسمه.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }''',
    "Homepage featured helper"
)
product.write_text(source, encoding="utf-8")

# Regression guards across editor, domain model, persistence and remote sync.
model = root / "app/src/main/java/com/pinky/dashboard/domain/model/Product.kt"
repository = root / "app/src/main/java/com/pinky/dashboard/data/repository/RepositoriesImpl.kt"
model_source = model.read_text(encoding="utf-8")
repo_source = repository.read_text(encoding="utf-8")
checks = {
    "availability and featured flags are independent domain fields":
        "val isActive: Boolean = true" in model_source and "val isFeatured: Boolean = false" in model_source,
    "editor restores availability from the saved product":
        "initialProduct?.isActive ?: true" in source,
    "editor restores homepage-featured state from the saved product":
        "initialProduct?.isFeatured ?: false" in source,
    "editor saves availability":
        "isActive = isActive" in source,
    "editor saves homepage-featured state":
        "isFeatured = isFeatured" in source,
    "Supabase upsert persists availability":
        "active = product.isActive" in repo_source,
    "Supabase upsert persists homepage-featured state":
        "featured = product.isFeatured" in repo_source,
    "Supabase sync restores availability":
        "isActive = dto.active ?: true" in repo_source,
    "Supabase sync restores homepage-featured state":
        "isFeatured = dto.featured ?: false" in repo_source,
}
for label, passed in checks.items():
    if not passed:
        raise SystemExit("Product visibility regression: " + label)
    print("PASS:", label)

print("PASS: product availability and homepage-featured controls remain independent and persisted.")
