import os
from pathlib import Path
root = Path(os.environ["PROJECT_DIR"])

def replace(path, old, new, count=1):
    p=root/path
    s=p.read_text(encoding='utf-8')
    n=s.count(old)
    if n < count:
        raise SystemExit(f'Expected {count} occurrence(s) in {path}, found {n}: {old[:100]!r}')
    s=s.replace(old,new,count)
    p.write_text(s,encoding='utf-8')

# Structured JSON models: sections, dynamic slides, and custom page sections.
replace(Path('app/src/main/java/com/pinky/dashboard/domain/model/WebsiteCustomizationConfig.kt'),
'''    @Json(name = "navigation") val navigation: List<NavigationConfig>? = null,
    @Json(name = "hero") val hero: HeroConfig? = null,''',
'''    @Json(name = "navigation") val navigation: List<NavigationConfig>? = null,
    @Json(name = "sections") val sections: List<SiteSectionConfig>? = null,
    @Json(name = "hero") val hero: HeroConfig? = null,''')
replace(Path('app/src/main/java/com/pinky/dashboard/domain/model/WebsiteCustomizationConfig.kt'),
'''    @Json(name = "customSections") val customSections: List<String>? = null
)''',
'''    @Json(name = "customSections") val customSections: List<CustomSiteSectionConfig>? = null
)

@JsonClass(generateAdapter = true)
data class SiteSectionConfig(
    @Json(name = "id") val id: String,
    @Json(name = "title") val title: String,
    @Json(name = "isVisible") val isVisible: Boolean = true,
    @Json(name = "sortOrder") val sortOrder: Int = 0
)

@JsonClass(generateAdapter = true)
data class CustomSiteSectionConfig(
    @Json(name = "id") val id: String,
    @Json(name = "title") val title: String,
    @Json(name = "text") val text: String = "",
    @Json(name = "imageUrl") val imageUrl: String = "",
    @Json(name = "buttonText") val buttonText: String = "",
    @Json(name = "buttonUrl") val buttonUrl: String = "",
    @Json(name = "backgroundColor") val backgroundColor: String = "#FFF0F7",
    @Json(name = "isVisible") val isVisible: Boolean = true,
    @Json(name = "sortOrder") val sortOrder: Int = 0
)''')
replace(Path('app/src/main/java/com/pinky/dashboard/domain/model/WebsiteCustomizationConfig.kt'),
'''    @Json(name = "title") val title: String = "",
    @Json(name = "description") val description: String = "",
    @Json(name = "buttonText") val buttonText: String = "تسوقي الآن",''',
'''    @Json(name = "title") val title: String = "",
    @Json(name = "arabicTitle") val arabicTitle: String = "",
    @Json(name = "description") val description: String = "",
    @Json(name = "buttonText") val buttonText: String = "تسوقي الآن",''')
replace(Path('app/src/main/java/com/pinky/dashboard/domain/model/WebsiteCustomizationConfig.kt'),
'''    @Json(name = "backgroundColor") val backgroundColor: String = "#121212",
    @Json(name = "textColor") val textColor: String = "#FFFFFF",''',
'''    // Empty means: preserve the storefront's own theme defaults.
    @Json(name = "backgroundColor") val backgroundColor: String = "",
    @Json(name = "textColor") val textColor: String = "",''')
replace(Path('app/src/main/java/com/pinky/dashboard/domain/model/WebsiteCustomizationConfig.kt'),
'''    @Json(name = "announcementColor") val announcementColor: String = "#381528",
    @Json(name = "favicon") val favicon: String = ""''',
'''    @Json(name = "announcementColor") val announcementColor: String = "#381528",
    @Json(name = "favicon") val favicon: String = "",
    @Json(name = "fontFamily") val fontFamily: String = ""''')

# WebsiteConfig defaults and CMS editable data.
replace(Path('app/src/main/java/com/pinky/dashboard/domain/model/StoreModels.kt'),
'''        SectionDisplayConfig("sec_announcement", "شريط التنبيهات العلوي", true, 1),
        SectionDisplayConfig("sec_hero", "البنر الرئيسي (Hero Section)", true, 2),
        SectionDisplayConfig("sec_categories", "أقسام المتجر الدائرية", true, 3),
        SectionDisplayConfig("sec_best_sellers", "المنتجات الأكثر مبيعاً", true, 4),
        SectionDisplayConfig("sec_offers", "عروض وتخفيضات Elory الحصرية", true, 5),
        SectionDisplayConfig("sec_prime_promo", "بنر الاشتراك في Elory Prime", true, 6),
        SectionDisplayConfig("sec_reviews", "آراء وتقييمات العملاء", true, 7),
        SectionDisplayConfig("sec_footer", "معلومات المتجر والتواصل والشحن", true, 8)
    ),''',
'''        SectionDisplayConfig("sec_announcement", "شريط التنبيهات العلوي", true, 1),
        SectionDisplayConfig("sec_hero", "البنر الرئيسي المتحرك", true, 2),
        SectionDisplayConfig("sec_categories", "أقسام المتجر الدائرية", true, 3),
        SectionDisplayConfig("sec_best_sellers", "المنتجات المميزة", true, 4),
        SectionDisplayConfig("sec_prime_promo", "بنر الاشتراك في Elory Prime", true, 5),
        SectionDisplayConfig("sec_features", "لماذا Elory؟", true, 6),
        SectionDisplayConfig("sec_final_cta", "الدعوة لاتخاذ إجراء", true, 7),
        SectionDisplayConfig("sec_footer", "معلومات المتجر والتواصل والشحن", true, 8)
    ),
    val heroSlides: List<HeroSlideConfig> = listOf(
        HeroSlideConfig("hero_1", "", "Your Style", "Discover", "أناقتكِ تبدأ من هنا", "اكتشفي أحدث صيحات الموضة والجمال", "تسوقي الآن", "#featured", 1, true),
        HeroSlideConfig("hero_2", "", "Elory COLLECTION", "Luxury Everyday", "", "شنط وإكسسوارات تضيف لمسة فاخرة إلى يومك.", "اكتشفي الشنط", "#featured", 2, true),
        HeroSlideConfig("hero_3", "", "NEW COLLECTION", "Your Style", "", "تفاصيل صغيرة تصنع إطلالة مختلفة.", "اكتشفي المجموعة", "#featured", 3, true)
    ),
    val customSections: List<CustomSiteSectionConfig> = emptyList(),''')

# Fix bucket identifiers to match the real project bucket.
replace(Path('app/src/main/java/com/pinky/dashboard/data/remote/SupabaseConfig.kt'),
'''    const val BUCKET_PRODUCT_IMAGES = "pinky-products"
    const val BUCKET_BANNERS = "pinky-banners"''',
'''    const val BUCKET_PRODUCT_IMAGES = "product-images"
    const val BUCKET_BANNERS = BUCKET_PRODUCT_IMAGES''')

# Replace save model mapping to persist hero, section visibility/order, and custom blocks.
pv = root / Path('app/src/main/java/com/pinky/dashboard/ui/PinkyViewModel.kt')
s = pv.read_text(encoding='utf-8')
old='''                val sectionsStr = config.sections.joinToString(";") { "${it.id}:${it.title}:${it.isVisible}:${it.sortOrder}" }
                
                val siteConfigObj = SiteCustomizationConfig(
                    announcement = AnnouncementConfig('''
new='''                val siteConfigObj = SiteCustomizationConfig(
                    announcement = AnnouncementConfig('''
if old not in s: raise SystemExit('PinkyViewModel sectionsStr anchor missing')
s=s.replace(old,new,1)
old='''                    navigation = config.navigationItems,
                    categories = CategoriesConfig('''
new='''                    navigation = config.navigationItems,
                    sections = config.sections.sortedBy { it.sortOrder }.map {
                        SiteSectionConfig(it.id, it.title, it.isVisible, it.sortOrder)
                    },
                    hero = HeroConfig(
                        slides = config.heroSlides.sortedBy { it.sortOrder }
                    ),
                    customSections = config.customSections.sortedBy { it.sortOrder },
                    categories = CategoriesConfig('''
if old not in s: raise SystemExit('PinkyViewModel navigation anchor missing')
s=s.replace(old,new,1)
old='''                        backgroundColor = "#121212",
                        textColor = "#FFFFFF",
                        announcementColor = config.announcementBgColor'''
new='''                        backgroundColor = "",
                        textColor = "",
                        announcementColor = config.announcementBgColor,
                        fontFamily = config.fontFamily'''
if old not in s: raise SystemExit('PinkyViewModel global colors anchor missing')
s=s.replace(old,new,1)
# Load CMS data from the JSONB config, using old defaults when fields aren't present.
old='''                            sections = parsedSections ?: currentConfig.sections,

                            // Top Bar Announcement Multi-Messages'''
new='''                            sections = cfgObj?.sections?.map {
                                SectionDisplayConfig(it.id, it.title, it.isVisible, it.sortOrder)
                            } ?: parsedSections ?: currentConfig.sections,
                            heroSlides = cfgObj?.hero?.slides?.takeIf { it.isNotEmpty() } ?: currentConfig.heroSlides,
                            customSections = cfgObj?.customSections ?: currentConfig.customSections,

                            // Top Bar Announcement Multi-Messages'''
if old not in s: raise SystemExit('PinkyViewModel load sections anchor missing')
s=s.replace(old,new,1)
pv.write_text(s,encoding='utf-8')

# Wire the new controls into the existing editor UI.
pe = root / Path('app/src/main/java/com/pinky/dashboard/ui/screens/website/WebsiteEditorScreen.kt')
s=pe.read_text(encoding='utf-8')
old='''                    item {
                        SectionCard(
                            title = "إعدادات عامة وألوان وهوية الموقع",
                            description = "اسم المتجر، تفاصيل السيو والبحث، والخطوط ولون الهوية الأساسي",
                            icon = Icons.Outlined.SettingsSuggest,
                            isActive = true,
                            onToggleActive = null,
                            onClick = { activeEditingDialog = 11 }
                        )
                    }

                    item {
                        Spacer(modifier = Modifier.height(80.dp))
                    }'''
new='''                    item {
                        SectionCard(
                            title = "إعدادات عامة وألوان وهوية الموقع",
                            description = "اسم المتجر، تفاصيل السيو والبحث، والخطوط ولون الهوية الأساسي",
                            icon = Icons.Outlined.SettingsSuggest,
                            isActive = true,
                            onToggleActive = null,
                            onClick = { activeEditingDialog = 11 }
                        )
                    }

                    item {
                        SectionCard(
                            title = "مدير أقسام الصفحة الرئيسية",
                            description = "إخفاء وإظهار الأقسام، تغيير ترتيبها، وإضافة أقسام مخصصة دون تعديل ملفات الموقع",
                            icon = Icons.Outlined.ViewAgenda,
                            isActive = true,
                            onToggleActive = null,
                            onClick = { activeEditingDialog = 12 }
                        )
                    }

                    item {
                        Spacer(modifier = Modifier.height(80.dp))
                    }'''
if old not in s: raise SystemExit('WebsiteEditor card 11 anchor missing')
s=s.replace(old,new,1)
s=s.replace('''                    11 -> "هوية وإعدادات الموقع العامة" to Icons.Outlined.SettingsSuggest
                    else ->''','''                    11 -> "هوية وإعدادات الموقع العامة" to Icons.Outlined.SettingsSuggest
                    12 -> "مدير أقسام الصفحة الرئيسية" to Icons.Outlined.ViewAgenda
                    else ->''',1)
s=s.replace('''                        4 -> HeroBannersForm(bannersList, onSaveBanner, onDeleteBanner, categoriesList)''','''                        4 -> HeroBannersForm(dialogConfig, onUpdate = { dialogConfig = it })''',1)
s=s.replace('''                        11 -> GlobalSettingsForm(dialogConfig, onUpdate = { dialogConfig = it })''','''                        11 -> GlobalSettingsForm(dialogConfig, onUpdate = { dialogConfig = it })
                        12 -> SectionsLayoutForm(dialogConfig, onUpdate = { dialogConfig = it })''',1)
start=s.index('@Composable\nfun HeroBannersForm(')
end=s.index('\n@Composable\nfun CategoriesLayoutForm',start)
new_hero='''@Composable
fun HeroBannersForm(
    config: WebsiteConfig,
    onUpdate: (WebsiteConfig) -> Unit
) {
    val slides = config.heroSlides.sortedBy { it.sortOrder }
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("شرائح الهيرو المتحرك", fontWeight = FontWeight.Bold, fontSize = 16.sp)
        Text(
            "كل شريحة يمكن تعديل صورتها ونصوصها وزرها ورابطها وترتيبها. اترك الصورة فارغة للاحتفاظ بالصورة الافتراضية الحالية.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        slides.forEachIndexed { index, slide ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("الشريحة ${index + 1}", fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
                        Switch(checked = slide.isActive, onCheckedChange = { active ->
                            val updated = slides.map { if (it.id == slide.id) it.copy(isActive = active) else it }
                            onUpdate(config.copy(heroSlides = updated))
                        })
                        IconButton(enabled = index > 0, onClick = {
                            val mutable = slides.toMutableList()
                            val item = mutable.removeAt(index); mutable.add(index - 1, item)
                            onUpdate(config.copy(heroSlides = mutable.mapIndexed { i, v -> v.copy(sortOrder = i + 1) }))
                        }) { Icon(Icons.Filled.ArrowUpward, contentDescription = "تحريك لأعلى") }
                        IconButton(enabled = index < slides.lastIndex, onClick = {
                            val mutable = slides.toMutableList()
                            val item = mutable.removeAt(index); mutable.add(index + 1, item)
                            onUpdate(config.copy(heroSlides = mutable.mapIndexed { i, v -> v.copy(sortOrder = i + 1) }))
                        }) { Icon(Icons.Filled.ArrowDownward, contentDescription = "تحريك لأسفل") }
                        IconButton(onClick = {
                            onUpdate(config.copy(heroSlides = slides.filterNot { it.id == slide.id }.mapIndexed { i, v -> v.copy(sortOrder = i + 1) }))
                        }) { Icon(Icons.Filled.Delete, contentDescription = "حذف الشريحة", tint = MaterialTheme.colorScheme.error) }
                    }
                    ImageUploadSelector(
                        imageUrl = slide.imageUrl,
                        onUrlChanged = { url -> onUpdate(config.copy(heroSlides = slides.map { if (it.id == slide.id) it.copy(imageUrl = url) else it })) },
                        bucket = "product-images",
                        placeholderText = "اختيار صورة الشريحة"
                    )
                    OutlinedTextField(value = slide.smallText, onValueChange = { v -> onUpdate(config.copy(heroSlides = slides.map { if(it.id==slide.id) it.copy(smallText=v) else it })) }, label = { Text("النص الصغير") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = slide.title, onValueChange = { v -> onUpdate(config.copy(heroSlides = slides.map { if(it.id==slide.id) it.copy(title=v) else it })) }, label = { Text("العنوان الرئيسي") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = slide.arabicTitle, onValueChange = { v -> onUpdate(config.copy(heroSlides = slides.map { if(it.id==slide.id) it.copy(arabicTitle=v) else it })) }, label = { Text("العنوان العربي") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = slide.description, onValueChange = { v -> onUpdate(config.copy(heroSlides = slides.map { if(it.id==slide.id) it.copy(description=v) else it })) }, label = { Text("الوصف") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
                    OutlinedTextField(value = slide.buttonText, onValueChange = { v -> onUpdate(config.copy(heroSlides = slides.map { if(it.id==slide.id) it.copy(buttonText=v) else it })) }, label = { Text("نص الزر") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = slide.actionUrl, onValueChange = { v -> onUpdate(config.copy(heroSlides = slides.map { if(it.id==slide.id) it.copy(actionUrl=v) else it })) }, label = { Text("رابط الزر (مثل #featured)") }, modifier = Modifier.fillMaxWidth())
                }
            }
        }
        Button(
            onClick = {
                val updated = slides + HeroSlideConfig(
                    id = "hero_${System.currentTimeMillis()}", imageUrl = "", smallText = "NEW COLLECTION",
                    title = "عنوان جديد", arabicTitle = "", description = "اكتب وصف الشريحة هنا",
                    buttonText = "اكتشفي الآن", actionUrl = "#featured", sortOrder = slides.size + 1, isActive = true
                )
                onUpdate(config.copy(heroSlides = updated))
            },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = PinkPrimary, contentColor = Color(0xFF381528))
        ) { Icon(Icons.Filled.Add, contentDescription = null); Spacer(Modifier.width(6.dp)); Text("إضافة شريحة جديدة") }
    }
}
'''
s=s[:start]+new_hero+s[end:]
# Add section layout form before CategoriesLayoutForm.
anchor='\n@Composable\nfun CategoriesLayoutForm'
layout='''
@Composable
fun SectionsLayoutForm(config: WebsiteConfig, onUpdate: (WebsiteConfig) -> Unit) {
    var editingCustom by remember { mutableStateOf<CustomSiteSectionConfig?>(null) }
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("ترتيب وأقسام الصفحة الرئيسية", fontWeight = FontWeight.Bold, fontSize = 16.sp)
        Text("استخدم مفاتيح الظهور لإخفاء الأقسام، والأسهم لتغيير ترتيبها. الحفظ ينشر الإعدادات إلى الموقع.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        val sections = config.sections.sortedBy { it.sortOrder }
        sections.forEachIndexed { index, section ->
            Card(border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)) {
                Row(Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text(section.title, fontWeight = FontWeight.SemiBold)
                        if (section.id.startsWith("custom_")) Text("قسم مخصص", style = MaterialTheme.typography.labelSmall, color = PinkPrimary)
                    }
                    Switch(checked = section.isVisible, onCheckedChange = { visible ->
                        onUpdate(config.copy(sections = sections.map { if(it.id==section.id) it.copy(isVisible=visible) else it }))
                    })
                    IconButton(enabled = index > 0, onClick = {
                        val list=sections.toMutableList(); val item=list.removeAt(index); list.add(index-1,item)
                        onUpdate(config.copy(sections=list.mapIndexed { i,v -> v.copy(sortOrder=i+1) }))
                    }) { Icon(Icons.Filled.ArrowUpward, contentDescription = "لأعلى") }
                    IconButton(enabled = index < sections.lastIndex, onClick = {
                        val list=sections.toMutableList(); val item=list.removeAt(index); list.add(index+1,item)
                        onUpdate(config.copy(sections=list.mapIndexed { i,v -> v.copy(sortOrder=i+1) }))
                    }) { Icon(Icons.Filled.ArrowDownward, contentDescription = "لأسفل") }
                    if (section.id.startsWith("custom_")) {
                        IconButton(onClick = { editingCustom = config.customSections.find { it.id == section.id.removePrefix("custom_") } }) {
                            Icon(Icons.Filled.Edit, contentDescription = "تعديل القسم", tint = PinkPrimary)
                        }
                        IconButton(onClick = {
                            val id = section.id.removePrefix("custom_")
                            onUpdate(config.copy(sections=sections.filterNot { it.id==section.id }.mapIndexed { i,v -> v.copy(sortOrder=i+1) }, customSections=config.customSections.filterNot { it.id==id }))
                        }) { Icon(Icons.Filled.Delete, contentDescription = "حذف القسم", tint = MaterialTheme.colorScheme.error) }
                    }
                }
            }
        }
        Button(onClick = {
            editingCustom = CustomSiteSectionConfig(
                id = "${System.currentTimeMillis()}", title = "قسم جديد", text = "اكتب محتوى القسم هنا",
                sortOrder = sections.size + 1
            )
        }, modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = PinkPrimary, contentColor = Color(0xFF381528))) {
            Icon(Icons.Filled.Add, contentDescription = null); Spacer(Modifier.width(6.dp)); Text("إضافة قسم مخصص")
        }
    }

    editingCustom?.let { initial ->
        var local by remember(initial.id) { mutableStateOf(initial) }
        AlertDialog(
            onDismissRequest = { editingCustom = null },
            title = { Text("إعداد القسم المخصص") },
            text = {
                Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(local.title, { local=local.copy(title=it) }, label={ Text("عنوان القسم") }, modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(local.text, { local=local.copy(text=it) }, label={ Text("النص") }, modifier=Modifier.fillMaxWidth(), minLines=3)
                    OutlinedTextField(local.imageUrl, { local=local.copy(imageUrl=it) }, label={ Text("رابط الصورة (اختياري)") }, modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(local.buttonText, { local=local.copy(buttonText=it) }, label={ Text("نص الزر (اختياري)") }, modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(local.buttonUrl, { local=local.copy(buttonUrl=it) }, label={ Text("رابط الزر") }, modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(local.backgroundColor, { local=local.copy(backgroundColor=it) }, label={ Text("لون الخلفية Hex") }, modifier=Modifier.fillMaxWidth())
                    Row(verticalAlignment=Alignment.CenterVertically) { Text("إظهار القسم", modifier=Modifier.weight(1f)); Switch(local.isVisible, { local=local.copy(isVisible=it) }) }
                }
            },
            confirmButton = { TextButton(onClick = {
                val exists = config.customSections.any { it.id == local.id }
                val custom = if(exists) config.customSections.map { if(it.id==local.id) local else it } else config.customSections + local.copy(sortOrder=config.sections.size+1)
                val secId = "custom_${local.id}"
                val section = SectionDisplayConfig(secId, local.title, local.isVisible, local.sortOrder.coerceAtLeast(1))
                val sections = if(config.sections.any { it.id==secId }) config.sections.map { if(it.id==secId) section else it } else config.sections + section
                onUpdate(config.copy(customSections=custom, sections=sections.mapIndexed { i,v -> v.copy(sortOrder = if(v.id==secId) section.sortOrder else v.sortOrder) }))
                editingCustom=null
            }) { Text("حفظ القسم") } },
            dismissButton = { TextButton(onClick={ editingCustom=null }) { Text("إلغاء") } }
        )
    }
}
'''
if anchor not in s: raise SystemExit('CategoriesLayoutForm anchor missing')
s=s.replace(anchor, '\n'+layout+anchor, 1)
# Replace wrong bucket parameters globally in WebsiteEditorScreen.
s=s.replace('bucket = "pinky-products"','bucket = "product-images"')
s=s.replace('bucket = "pinky-banners"','bucket = "product-images"')
# Replace direct Supabase image uploader implementation with shared compressed uploader.
s=s.replace('import com.pinky.dashboard.data.remote.SupabaseClient','import com.pinky.dashboard.data.remote.SupabaseClient\nimport com.pinky.dashboard.data.remote.SupabaseStorageUploader')
start=s.index('@Composable\nfun ImageUploadSelector(')
# replace function through EOF? function is last. verify last closing
new_img='''@Composable
fun ImageUploadSelector(
    imageUrl: String,
    onUrlChanged: (String) -> Unit,
    bucket: String,
    placeholderText: String
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var isUploading by remember { mutableStateOf(false) }
    var uploadError by remember { mutableStateOf<String?>(null) }
    var uploadSuccess by remember { mutableStateOf(false) }

    val photoPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia()
    ) { uri: Uri? ->
        if (uri != null && !isUploading) {
            isUploading = true
            uploadError = null
            uploadSuccess = false
            scope.launch {
                try {
                    val uploadedUrl = SupabaseStorageUploader.uploadProductImage(
                        contentResolver = context.contentResolver,
                        uri = uri,
                        productId = "site-assets",
                        label = "website"
                    )
                    onUrlChanged(uploadedUrl)
                    uploadSuccess = true
                } catch (e: Exception) {
                    uploadError = e.message ?: "تعذر رفع الصورة. تحقق من صلاحية الحساب والاتصال."
                    android.util.Log.e("EloryWebsiteUpload", "Image upload failed", e)
                } finally {
                    isUploading = false
                }
            }
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        if (imageUrl.isNotBlank()) {
            AsyncImage(
                model = imageUrl,
                contentDescription = null,
                modifier = Modifier.fillMaxWidth().height(150.dp).clip(RoundedCornerShape(10.dp)),
                contentScale = ContentScale.Crop
            )
        }
        OutlinedButton(
            onClick = { photoPickerLauncher.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) },
            enabled = !isUploading,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(8.dp)
        ) {
            if (isUploading) CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
            else Icon(Icons.Outlined.CloudUpload, contentDescription = null)
            Spacer(Modifier.width(8.dp))
            Text(if (isUploading) "جاري ضغط ورفع الصورة..." else placeholderText)
        }
        if (uploadSuccess) Text("تم رفع الصورة بنجاح", color = Color(0xFF2E8B57), style = MaterialTheme.typography.bodySmall)
        uploadError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
        OutlinedTextField(
            value = imageUrl,
            onValueChange = onUrlChanged,
            label = { Text("رابط الصورة (اختياري)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
    }
}
'''
s=s[:start]+new_img
pe.write_text(s,encoding='utf-8')

# Persist and display the actual result of the asynchronous website save.
pv = root / Path('app/src/main/java/com/pinky/dashboard/ui/PinkyViewModel.kt')
s = pv.read_text(encoding='utf-8')
old = '''    private val _websiteConfig = MutableStateFlow(WebsiteConfig())
    val websiteConfig: StateFlow<WebsiteConfig> = _websiteConfig.asStateFlow()'''
new = old + '''
    private val _websiteSaveState = MutableStateFlow("idle")
    val websiteSaveState: StateFlow<String> = _websiteSaveState.asStateFlow()'''
assert s.count(old)==1
s=s.replace(old,new,1)
old='''    fun updateWebsiteConfig(config: WebsiteConfig) {
        viewModelScope.launch {
            try {'''
new='''    fun updateWebsiteConfig(config: WebsiteConfig) {
        viewModelScope.launch {
            _websiteSaveState.value = "saving"
            try {'''
assert s.count(old)==1
s=s.replace(old,new,1)
old='''                    )
                    return@launch
                }
                _websiteConfig.value = config
            } catch (e: Exception) {
                android.util.Log.e("PinkyViewModel", "Exception in updateWebsiteConfig", e)
                e.printStackTrace()
            }
        }
    }'''
new='''                    )
                    _websiteSaveState.value = "error"
                    return@launch
                }
                _websiteConfig.value = config
                _websiteSaveState.value = "success"
            } catch (e: Exception) {
                android.util.Log.e("PinkyViewModel", "Exception in updateWebsiteConfig", e)
                e.printStackTrace()
                _websiteSaveState.value = "error"
            }
        }
    }'''
assert s.count(old)==1
s=s.replace(old,new,1)
pv.write_text(s,encoding='utf-8')

app_file = root / Path('app/src/main/java/com/pinky/dashboard/ui/PinkyApp.kt')
app_source = app_file.read_text(encoding='utf-8')
old='''    val websiteConfig by viewModel.websiteConfig.collectAsStateWithLifecycle()'''
assert app_source.count(old)==1
app_source=app_source.replace(old,old+'''\n    val websiteSaveState by viewModel.websiteSaveState.collectAsStateWithLifecycle()''',1)
old='''                                    onSaveConfig = { viewModel.updateWebsiteConfig(it) },'''
assert app_source.count(old)==1
app_source=app_source.replace(old,old+'''\n                                    saveState = websiteSaveState,''',1)
app_file.write_text(app_source,encoding='utf-8')

pe = root / Path('app/src/main/java/com/pinky/dashboard/ui/screens/website/WebsiteEditorScreen.kt')
s=pe.read_text(encoding='utf-8')
old='''    onSaveCategory: (Category) -> Unit,
    modifier: Modifier = Modifier
) {'''
assert s.count(old)==1
s=s.replace(old,'''    onSaveCategory: (Category) -> Unit,
    saveState: String = "idle",
    modifier: Modifier = Modifier
) {''',1)
old='''    Scaffold(
        floatingActionButton = {'''
assert s.count(old)==1
s=s.replace(old,'''    LaunchedEffect(saveState) {
        showSavedMessage = saveState == "success" || saveState == "error"
    }

    Scaffold(
        floatingActionButton = {''',1)
s=s.replace('''                onClick = {
                    onSaveConfig(config)
                    showSavedMessage = true
                },''','''                onClick = {
                    onSaveConfig(config)
                },''',1)
s=s.replace('''                text = { Text("حفظ ونشر التعديلات", fontWeight = FontWeight.Bold) },''','''                text = { Text(if (saveState == "saving") "جارٍ حفظ التعديلات..." else "حفظ ونشر التعديلات", fontWeight = FontWeight.Bold) },''',1)
s=s.replace('''                    Text("تم حفظ إعدادات موقع Elory بنجاح وستنعكس للمتسوقين فوراً.")''','''                    Text(if (saveState == "success") "تم حفظ إعدادات الموقع بنجاح." else "تعذر حفظ جميع إعدادات الموقع. راجع الاتصال والصلاحيات ثم أعد المحاولة.")''',1)
s=s.replace('import com.pinky.dashboard.data.remote.SupabaseClient\n','')
s=s.replace('import okhttp3.MediaType.Companion.toMediaTypeOrNull\n','')
pe.write_text(s,encoding='utf-8')

cat_file = root / Path('app/src/main/java/com/pinky/dashboard/ui/screens/categories/CategoriesScreen.kt')
cat_source=cat_file.read_text(encoding='utf-8')
assert cat_source.count('val bucket = "pinky-products"')==1
cat_file.write_text(cat_source.replace('val bucket = "pinky-products"','val bucket = "product-images"',1),encoding='utf-8')
print('Android CMS patches applied.')