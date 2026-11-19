import os
import re
from pathlib import Path

root = Path(os.environ["PROJECT_DIR"]).resolve()
repo_root = Path(__file__).resolve().parents[1]
cropper_overlay = repo_root / "scripts/android-feature-overlay/app/src/main/java/com/pinky/dashboard/ui/components/ImageCropEditorDialog.kt"
cropper_target = root / "app/src/main/java/com/pinky/dashboard/ui/components/ImageCropEditorDialog.kt"
if not cropper_overlay.is_file():
    raise SystemExit("Image crop editor source is missing from the Android feature overlay.")
cropper_source = cropper_overlay.read_text(encoding="utf-8")
for marker in ("maxDecodeDimension = 2048", "decoder.setTargetSize", "inJustDecodeBounds = true", "catch (e: OutOfMemoryError)"):
    if marker not in cropper_source:
        raise SystemExit("Image crop editor memory-safety regression: missing " + marker)
cropper_target.parent.mkdir(parents=True, exist_ok=True)
cropper_target.write_text(cropper_source, encoding="utf-8")

def edit(relative, old, new, label):
    path = root / relative
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

# Product images: the image thumbnail itself opens the crop editor.
product = "app/src/main/java/com/pinky/dashboard/ui/screens/products/ProductEditDialog.kt"
source = (root / product).read_text(encoding="utf-8")
if "ImageCropEditorDialog" in source:
    raise SystemExit("Product image editor is already integrated; refusing duplicate patch.")
source = source.replace(
    "import com.pinky.dashboard.ui.components.ProtectedFieldPlaceholder",
    "import com.pinky.dashboard.ui.components.ProtectedFieldPlaceholder\nimport com.pinky.dashboard.ui.components.ImageCropEditorDialog",
    1
)
state_anchor = '''    var selectedProductImageUris by remember { mutableStateOf<List<Uri>>(emptyList()) }'''
state_new = '''    var selectedProductImageUris by remember { mutableStateOf<List<Uri>>(emptyList()) }
    var cropTargetUri by remember { mutableStateOf<Uri?>(null) }'''
if source.count(state_anchor) != 1:
    raise SystemExit("Product crop state anchor mismatch.")
source = source.replace(state_anchor, state_new, 1)
thumb_old = '''AsyncImage(model = uri, contentDescription = "صورة محددة للمنتج", contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())'''
thumb_new = '''AsyncImage(model = uri, contentDescription = "صورة محددة للمنتج", contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize().clickable { cropTargetUri = uri })'''
if source.count(thumb_old) != 1:
    raise SystemExit("Product image thumbnail anchor mismatch.")
source = source.replace(thumb_old, thumb_new, 1)
hint_old = '''Text(selectedProductImageUris.size.toString() + " صورة محددة — أول صورة هي الغلاف", style = MaterialTheme.typography.labelSmall, color = PinkPrimary)'''
hint_new = '''Text(selectedProductImageUris.size.toString() + " صورة محددة — أول صورة هي الغلاف", style = MaterialTheme.typography.labelSmall, color = PinkPrimary)
                                    Text("اضغط على أي صورة لقصّها وضبط الجزء الظاهر داخل صفحة المنتج.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)'''
if source.count(hint_old) != 1:
    raise SystemExit("Product crop hint anchor mismatch.")
source = source.replace(hint_old, hint_new, 1)
# Insert the dialog immediately after the ProductEditDialog's outer Dialog.
start = source.index("@Composable\nfun ProductEditDialog(")
end_match = re.search(r"\n}\s*\n@Composable", source[start:])
if end_match is None:
    raise SystemExit("Could not locate ProductEditDialog end.")
end = start + end_match.start()
dialog = '''
    cropTargetUri?.let { target ->
        ImageCropEditorDialog(
            imageUri = target,
            aspectRatio = 0.8f,
            title = "ضبط صورة المنتج",
            onDismiss = { cropTargetUri = null },
            onCropped = { croppedUri ->
                selectedProductImageUris = selectedProductImageUris.map { if (it == target) croppedUri else it }
                cropTargetUri = null
            }
        )
    }
'''
source = source[:end] + dialog + source[end:]
(root / product).write_text(source, encoding="utf-8")

# Hero campaigns: produce a landscape desktop crop and a portrait mobile crop.
website = "app/src/main/java/com/pinky/dashboard/ui/screens/website/WebsiteEditorScreen.kt"
path = root / website
source = path.read_text(encoding="utf-8")
if "onUrlsChanged" in source or "نسخة الكمبيوتر ونسخة الموبايل" in source:
    raise SystemExit("Hero crop editor is already integrated; refusing duplicate patch.")
call_old = '''                    HeroCampaignMediaSelector(
                        label = "صورة البانر",
                        mediaUrl = currentImage,
                        onUrlChanged = { url ->
                            updateSlide(slide.id, activateUploadedSlideIfOnlyActiveIsEmpty = true) {
                                it.copy(
                                    fullBleed = true,
                                    mediaType = "image",
                                    mediaUrl = url,
                                    imageUrl = url,
                                    mobileMediaUrl = "",
                                    posterUrl = ""
                                )
                            }
                        }
                    )'''
call_new = '''                    HeroCampaignMediaSelector(
                        label = "صورة البانر",
                        mediaUrl = currentImage,
                        onUrlChanged = { url ->
                            updateSlide(slide.id, activateUploadedSlideIfOnlyActiveIsEmpty = true) {
                                it.copy(
                                    fullBleed = true,
                                    mediaType = "image",
                                    mediaUrl = url,
                                    imageUrl = url,
                                    mobileMediaUrl = "",
                                    posterUrl = ""
                                )
                            }
                        }
                    )'''
if source.count(call_old) != 1:
    raise SystemExit("Hero campaign selector call anchor mismatch.")
source = source.replace(call_old, call_new, 1)
function_start = source.index("@Composable\nfun HeroCampaignMediaSelector(")
function_end = source.index("\n@Composable\nfun HeroBannersForm(", function_start)
new_function = '''@Composable
fun HeroCampaignMediaSelector(
    label: String,
    mediaUrl: String,
    onUrlChanged: (String) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var isUploading by remember { mutableStateOf(false) }
    var uploadError by remember { mutableStateOf<String?>(null) }
    var uploadSuccess by remember { mutableStateOf(false) }

    val picker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia()
    ) { uri: Uri? ->
        if (uri != null && !isUploading) {
            isUploading = true
            uploadError = null
            uploadSuccess = false
            scope.launch {
                try {
                    // Keep hero uploads on the original URI-to-storage path.
                    // The crop editor is intentionally not part of this flow.
                    val uploadedUrl = HeroAdMediaUploader.upload(context.contentResolver, uri, isVideo = false)
                    onUrlChanged(uploadedUrl)
                    uploadSuccess = true
                } catch (error: Exception) {
                    uploadError = error.message ?: "تعذر رفع صورة الهيرو."
                    android.util.Log.e("EloryHeroCampaign", "Hero image upload failed", error)
                } finally {
                    isUploading = false
                }
            }
        }
    }

    Column(modifier = Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, fontWeight = FontWeight.SemiBold)
        if (mediaUrl.isNotBlank()) {
            AsyncImage(
                model = mediaUrl,
                contentDescription = "معاينة صورة الهيرو",
                modifier = Modifier.fillMaxWidth().height(155.dp).clip(RoundedCornerShape(10.dp)),
                contentScale = ContentScale.Crop
            )
        } else {
            Box(
                modifier = Modifier.fillMaxWidth().height(105.dp).clip(RoundedCornerShape(10.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant),
                contentAlignment = Alignment.Center
            ) {
                Text("لم يتم رفع صورة لهذا الإعلان بعد", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                onClick = { picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) },
                enabled = !isUploading,
                modifier = Modifier.weight(1f),
                colors = ButtonDefaults.buttonColors(containerColor = PinkPrimary, contentColor = Color(0xFF381528))
            ) {
                if (isUploading) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                    Spacer(Modifier.width(7.dp))
                    Text("جاري رفع الصورة...")
                } else {
                    Text(if (mediaUrl.isBlank()) "اختيار صورة" else "تغيير الصورة")
                }
            }
            if (mediaUrl.isNotBlank()) {
                OutlinedButton(onClick = { onUrlChanged(""); uploadSuccess = false }, enabled = !isUploading) {
                    Text("إزالة الصورة")
                }
            }
        }
        if (uploadSuccess) Text("تم رفع صورة الهيرو بنجاح", color = Color(0xFF16834A), style = MaterialTheme.typography.bodySmall)
        uploadError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
    }
}
'''
source = source[:function_start] + new_function + source[function_end:]
path.write_text(source, encoding="utf-8")


# Guard the exact regression boundary: crop stays available for product images,
# while hero image selection and upload never instantiate the crop editor.
hero_source = (root / website).read_text(encoding="utf-8")
product_source = (root / product).read_text(encoding="utf-8")
if "ImageCropEditorDialog" in hero_source or "cropStep" in hero_source or "onUrlsChanged" in hero_source:
    raise SystemExit("Hero image upload must remain independent from the crop editor.")
if "ImageCropEditorDialog" not in product_source:
    raise SystemExit("Product image crop editor was unexpectedly removed.")
if "HeroAdMediaUploader.upload(context.contentResolver, uri, isVideo = false)" not in hero_source:
    raise SystemExit("Hero image direct upload path is missing.")
print("PASS: hero upload bypasses crop editor; product crop editor remains enabled.")
