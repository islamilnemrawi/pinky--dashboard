from __future__ import annotations
import os
from pathlib import Path
ROOT = Path(os.environ["PROJECT_DIR"]).resolve()
def patch(relative: str, old: str, new: str, label: str) -> None:
    path = ROOT / relative
    if not path.is_file(): raise SystemExit(f"Missing required source file for {label}: {relative}")
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count == 0 and new in source:
        print(f"Already applied: {label}"); return
    if count != 1: raise SystemExit(f"Expected exactly one anchor for {label}; found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")
    print(f"PASS: {label}")
MODEL = "app/src/main/java/com/pinky/dashboard/domain/model/StoreModels.kt"
JSON = "app/src/main/java/com/pinky/dashboard/domain/model/WebsiteCustomizationConfig.kt"
VM = "app/src/main/java/com/pinky/dashboard/ui/PinkyViewModel.kt"
EDITOR = "app/src/main/java/com/pinky/dashboard/ui/screens/website/WebsiteEditorScreen.kt"
MOCKUP = "app/src/main/java/com/pinky/dashboard/ui/screens/website/PhoneMockupView.kt"
patch(MODEL,
    '    val primeThemeFeature: String = "ثيم برونزي فخم",\n    val primeButtonText: String = "اشتركي الآن",',
    '    val primeThemeFeature: String = "ثيم برونزي فخم",\n    val primeExtraFeatures: List<String> = emptyList(),\n    val primeButtonText: String = "اشتركي الآن",',
    "Prime extra-features model")
patch(JSON,
    '    @Json(name = "freeShippingOrdersCount") val freeShippingOrdersCount: Int = 4,\n    @Json(name = "packagingFeature") val packagingFeature: String = "تغليف مميز مجاني",\n    @Json(name = "themeFeature") val themeFeature: String = "ثيم برونزي فخم",',
    '    @Json(name = "freeShippingOrdersCount") val freeShippingOrdersCount: Int = 6,\n    @Json(name = "packagingFeature") val packagingFeature: String = "تغليف مميز مجاني",\n    @Json(name = "themeFeature") val themeFeature: String = "ثيم برونزي فخم",\n    @Json(name = "features") val features: List<String> = emptyList(),',
    "Prime features JSON model and consistent shipping default")
patch(VM,
    '                        packagingFeature = config.primePackagingFeature,\n                        themeFeature = config.primeThemeFeature,\n                        buttonText = config.primeButtonText,',
    '                        packagingFeature = config.primePackagingFeature,\n                        themeFeature = config.primeThemeFeature,\n                        features = config.primeExtraFeatures.map { it.trim() }.filter { it.isNotEmpty() }.take(12),\n                        buttonText = config.primeButtonText,',
    "persist Prime feature list")
patch(VM,
    '                            primeThemeFeature = cfgObj?.prime?.themeFeature ?: currentConfig.primeThemeFeature,\n                            primeButtonText = cfgObj?.prime?.buttonText ?: currentConfig.primeButtonText,',
    '                            primeThemeFeature = cfgObj?.prime?.themeFeature ?: currentConfig.primeThemeFeature,\n                            primeExtraFeatures = cfgObj?.prime?.features ?: currentConfig.primeExtraFeatures,\n                            primeButtonText = cfgObj?.prime?.buttonText ?: currentConfig.primeButtonText,',
    "restore Prime feature list from Supabase")
patch(EDITOR,
'''        OutlinedTextField(
            value = config.primeThemeFeature,
            onValueChange = { onUpdate(config.copy(primeThemeFeature = it)) },
            label = { Text("ميزة الهوية والمظهر للأعضاء") },
            modifier = Modifier.fillMaxWidth()
        )

        OutlinedTextField(
            value = config.primeButtonText,''',
'''        OutlinedTextField(
            value = config.primeThemeFeature,
            onValueChange = { onUpdate(config.copy(primeThemeFeature = it)) },
            label = { Text("ميزة الهوية والمظهر للأعضاء (اتركيها فارغة لإيقافها)") },
            modifier = Modifier.fillMaxWidth()
        )

        OutlinedTextField(
            value = config.primeExtraFeatures.joinToString("\\n"),
            onValueChange = { raw ->
                onUpdate(config.copy(primeExtraFeatures = raw.lines().map { it.trim() }.filter { it.isNotEmpty() }.take(12)))
            },
            label = { Text("مميزات إضافية (كل ميزة في سطر مستقل)") },
            supportingText = { Text("يمكنك إضافة أو حذف المميزات بتعديل السطور. الحد الأقصى 12 ميزة.") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 3
        )

        OutlinedTextField(
            value = config.primeButtonText,''',
    "Prime add/remove feature editor")
patch(EDITOR,
    'onValueChange = { onUpdate(config.copy(primeFreeShippingOrdersCount = it.toIntOrNull() ?: 4)) },',
    'onValueChange = { onUpdate(config.copy(primeFreeShippingOrdersCount = it.toIntOrNull() ?: 6)) },',
    "Prime shipping editor default")
patch(VM,
'''        viewModelScope.launch {
            _websiteSaveState.value = "saving"
            try {
                // 1. Store settings''',
'''        viewModelScope.launch {
            val validPrime = config.primePrice.isFinite() && config.primePrice > 0.0 &&
                config.primeDurationDays in 1..3650 &&
                config.primeDiscountPercent.isFinite() && config.primeDiscountPercent in 0.0..100.0 &&
                config.primeFreeShippingOrdersCount in 0..100 &&
                config.primeExtraFeatures.size <= 12 &&
                config.primeExtraFeatures.all { it.isNotBlank() && it.length <= 100 }
            if (!validPrime) {
                _websiteSaveState.value = "error"
                notifyUser("راجعي إعدادات Prime: السعر أكبر من صفر، المدة 1–3650 يومًا، الخصم 0–100%، والشحن 0–100.")
                return@launch
            }
            _websiteSaveState.value = "saving"
            try {
                // 1. Store settings''',
    "Prime settings validation before saving")
patch(MOCKUP,
'''                        Text(config.primeName, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        Text(config.primeDescription, color = Color.White.copy(alpha = .8f), fontSize = 10.sp)
                    }''',
'''                        Text(config.primeName, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        Text(config.primeDescription, color = Color.White.copy(alpha = .8f), fontSize = 10.sp)
                        config.primeExtraFeatures.forEach { feature ->
                            Text("• $feature", color = Color.White.copy(alpha = .9f), fontSize = 9.sp)
                        }
                    }''',
    "Prime feature list in phone preview")
vm_text = (ROOT / VM).read_text(encoding="utf-8")
if "isStoreOpen = config.isStoreOpen" not in vm_text or "isStoreOpen = cfgObj?.global?.isStoreOpen" not in vm_text:
    raise SystemExit("Store open/close persistence was altered or is missing")
for relative, markers in {
    MODEL: ("primeExtraFeatures: List<String>",),
    JSON: ('@Json(name = "features") val features: List<String>',),
    VM: ("features = config.primeExtraFeatures", "primeExtraFeatures = cfgObj?.prime?.features", "config.primePrice.isFinite()"),
    EDITOR: ("مميزات إضافية (كل ميزة في سطر مستقل)", "primeExtraFeatures = raw.lines()"),
    MOCKUP: ("config.primeExtraFeatures.forEach",)
}.items():
    source = (ROOT / relative).read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in source]
    if missing: raise SystemExit(f"Prime settings verification failed in {relative}: {missing}")
print("PASS: Prime controls and feature list are wired; store open/close remains intact.")
