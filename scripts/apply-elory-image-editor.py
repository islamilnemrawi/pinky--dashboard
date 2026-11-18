import os
from pathlib import Path

root = Path(os.environ["PROJECT_DIR"]).resolve()

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
edit_state = '''    var selectedProductImageUris by remember { mutableStateOf<List<Uri>>(emptyList()) }
    var isSaving by remember { mutableStateOf(false) }'''
state_new = '''    var selectedProductImageUris by remember { mutableStateOf<List<Uri>>(emptyList()) }
    var cropTargetUri by remember { mutableStateOf<Uri?>(null) }
    var isSaving by remember { mutableStateOf(false) }'''
if source.count(edit_state) != 1:
    raise SystemExit("Product crop state anchor mismatch.")
source = source.replace(edit_state, state_new, 1)
thumb_old = '''Box(Modifier.size(76.dp).clip(RoundedCornerShape(10.dp)).border(1.dp, PinkPrimary, RoundedCornerShape(10.dp)))'''
thumb_new = '''Box(Modifier.size(76.dp).clip(RoundedCornerShape(10.dp)).border(1.dp, PinkPrimary, RoundedCornerShape(10.dp)).clickable { cropTargetUri = uri })'''
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
end_marker = "\n}\n\n@Composable"
end = source.find(end_marker, start)
if end < 0:
    raise SystemExit("Could not locate ProductEditDialog end.")
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
source = source.replace(
    "import com.pinky.dashboard.ui.theme.PinkPrimary",
    "import com.pinky.dashboard.ui.theme.PinkPrimary\nimport com.pinky.dashboard.ui.components.ImageCropEditorDialog",
    1
)
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
                        onUrlsChanged = { desktopUrl, mobileUrl ->
                            updateSlide(slide.id, activateUploadedSlideIfOnlyActiveIsEmpty = true) {
                                it.copy(
                                    fullBleed = true,
                                    mediaType = "image",
                                    mediaUrl = desktopUrl,
                                    imageUrl = desktopUrl,
                                    mobileMediaUrl = mobileUrl,
                                    useSeparateMobileMedia = true,
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
    onUrlsChanged: (String, String) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var isUploading by remember { mutableStateOf(false) }
    var uploadError by remember { mutableStateOf<String?>(null) }
    var uploadSuccess by remember { mutableStateOf(false) }
    var sourceUri by remember { mutableStateOf<Uri?>(null) }
    var desktopCropUri by remember { mutableStateOf<Uri?>(null) }
    var mobileCropUri by remember { mutableStateOf<Uri?>(null) }
    var cropStep by remember { mutableIntStateOf(0) }

    val picker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia()
    ) { uri: Uri? ->
        if (uri != null && !isUploading) {
            sourceUri = uri
            desktopCropUri = null
            mobileCropUri = null
            cropStep = 1
            uploadError = null
            uploadSuccess = false
        }
    }

    Column(modifier = Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, fontWeight = FontWeight.SemiBold)
        if (mediaUrl.isNotBlank()) {
            AsyncImage(
                model = mediaUrl,
                contentDescription = "معاينة صورة الهيرو للكمبيوتر",
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
                enabled = !isUploading && cropStep == 0,
                modifier = Modifier.weight(1f),
                colors = ButtonDefaults.buttonColors(containerColor = PinkPrimary, contentColor = Color(0xFF381528))
            ) {
                if (isUploading) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                    Spacer(Modifier.width(7.dp))
                    Text("جاري رفع النسختين...")
                } else {
                    Text(if (mediaUrl.isBlank()) "اختيار صورة وقصّها" else "تغيير الصورة وقصّها")
                }
            }
            if (mediaUrl.isNotBlank()) {
                OutlinedButton(onClick = { onUrlsChanged("", ""); uploadSuccess = false }, enabled = !isUploading && cropStep == 0) {
                    Text("إزالة الصورة")
                }
            }
        }
        if (uploadSuccess) Text("تم رفع نسختي الكمبيوتر والموبايل بنجاح", color = Color(0xFF16834A), style = MaterialTheme.typography.bodySmall)
        uploadError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
        Text(
            "سيتم تجهيز قصّة عريضة للكمبيوتر وقصّة طولية للموبايل تلقائياً، مع إمكانية تحريك الصورة وتكبيرها قبل الاعتماد.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }

    val original = sourceUri
    if (original != null && cropStep == 1) {
        ImageCropEditorDialog(
            imageUri = original,
            aspectRatio = 2.43f,
            title = "قص صورة الهيرو — الكمبيوتر",
            onDismiss = { cropStep = 0; sourceUri = null },
            onCropped = { uri -> desktopCropUri = uri; cropStep = 2 }
        )
    }
    if (original != null && cropStep == 2) {
        ImageCropEditorDialog(
            imageUri = original,
            aspectRatio = 0.79f,
            title = "قص صورة الهيرو — الموبايل",
            onDismiss = { cropStep = 0; sourceUri = null; desktopCropUri = null },
            onCropped = { uri ->
                mobileCropUri = uri
                cropStep = 0
                val desktop = desktopCropUri
                val mobile = mobileCropUri
                if (desktop == null) {
                    uploadError = "تعذر تجهيز نسخة الكمبيوتر. أعد اختيار الصورة."
                } else {
                    isUploading = true
                    scope.launch {
                        try {
                            val desktopUrl = HeroAdMediaUploader.upload(context.contentResolver, desktop, isVideo = false)
                            val mobileUrl = HeroAdMediaUploader.upload(context.contentResolver, uri, isVideo = false)
                            onUrlsChanged(desktopUrl, mobileUrl)
                            uploadSuccess = true
                            sourceUri = null
                            desktopCropUri = null
                            mobileCropUri = null
                        } catch (error: Exception) {
                            uploadError = error.message ?: "تعذر رفع صور الهيرو."
                            android.util.Log.e("EloryHeroCampaign", "Hero image upload failed", error)
                        } finally {
                            isUploading = false
                        }
                    }
                }
            }
        )
    }
}
'''
source = source[:function_start] + new_function + source[function_end:]
path.write_text(source, encoding="utf-8")

# The storefront uses this flag to select the mobile crop in its <picture> element.
model = "app/src/main/java/com/pinky/dashboard/domain/model/WebsiteCustomizationConfig.kt"
edit(model,
'''    @Json(name = "mobileMediaUrl") val mobileMediaUrl: String = "",
    @Json(name = "posterUrl") val posterUrl: String = "",''',
'''    @Json(name = "mobileMediaUrl") val mobileMediaUrl: String = "",
    @Json(name = "useSeparateMobileMedia") val useSeparateMobileMedia: Boolean = false,
    @Json(name = "posterUrl") val posterUrl: String = "",''',
"Hero mobile media model")

# Cropped temporary files use file:// URIs; infer MIME and file size for these uploads.
uploader = "app/src/main/java/com/pinky/dashboard/data/remote/HeroAdMediaUploader.kt"
edit(uploader,
'''        val mimeType = contentResolver.getType(uri)?.lowercase()
            ?: throw IllegalArgumentException("تعذر تحديد نوع الملف. اختر صورة أو فيديو بصيغة مدعومة.")''',
'''        val mimeType = contentResolver.getType(uri)?.lowercase() ?: when (uri.lastPathSegment?.substringAfterLast('.', "")?.lowercase()) {
            "jpg", "jpeg" -> "image/jpeg"
            "png" -> "image/png"
            "webp" -> "image/webp"
            "avif" -> "image/avif"
            "mp4" -> "video/mp4"
            "webm" -> "video/webm"
            else -> throw IllegalArgumentException("تعذر تحديد نوع الملف. اختر صورة أو فيديو بصيغة مدعومة.")
        }''',
"Hero upload MIME fallback")

print("PASS: shared crop editor wired into product images and desktop/mobile hero campaign uploads.")
