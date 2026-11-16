import os
from pathlib import Path
root = Path(os.environ["PROJECT_DIR"])
def read(rel):
    p=root/rel
    if not p.is_file(): raise SystemExit("Missing "+rel)
    return p,p.read_text(encoding="utf-8")
def once(s,a,b,label):
    if s.count(a)!=1: raise SystemExit(label+" anchor count "+str(s.count(a)))
    return s.replace(a,b,1)


model_path, model_text = read("app/src/main/java/com/pinky/dashboard/domain/model/WebsiteCustomizationConfig.kt")
if "data class SiteCustomizationDraftRequest(" not in model_text:
    model_text += '''

@JsonClass(generateAdapter = true)
data class SiteCustomizationDraftRequest(
    @Json(name = "p_config") val config: SiteCustomizationConfig
)
'''
if "data class SiteCustomizationVersion(" not in model_text:
    model_text += '''

@JsonClass(generateAdapter = true)
data class SiteCustomizationVersion(
    @Json(name = "id") val id: Long,
    @Json(name = "label") val label: String,
    @Json(name = "createdAt") val createdAt: String
)
'''



model_path.write_text(model_text, encoding="utf-8")

p,s=read("app/src/main/java/com/pinky/dashboard/data/remote/SupabaseClient.kt")
if "import retrofit2.http.POST" not in s:
    s=s.replace("import retrofit2.http.PUT\n","import retrofit2.http.PUT\nimport retrofit2.http.POST\n",1)
if "fun saveSiteCustomizationDraft(" not in s:
    st=s.find("interface SupabaseService"); br=s.find("{",st); depth=0; en=-1
    if st<0 or br<0: raise SystemExit("SupabaseService missing")
    for i in range(br,len(s)):
        if s[i]=="{": depth+=1
        elif s[i]=="}":
            depth-=1
            if depth==0: en=i; break
    if en<0: raise SystemExit("SupabaseService end missing")
    s=s[:en]+'''
    @POST("rest/v1/rpc/admin_save_site_customization_draft")
    suspend fun saveSiteCustomizationDraft(@Body params: com.pinky.dashboard.domain.model.SiteCustomizationDraftRequest): Response<Boolean>

    @POST("rest/v1/rpc/admin_get_site_customization_draft")
    suspend fun getSiteCustomizationDraft(@Body params: Map<String, Any>): Response<com.pinky.dashboard.domain.model.SiteCustomizationConfig>

    @POST("rest/v1/rpc/admin_clear_site_customization_draft")
    suspend fun clearSiteCustomizationDraft(@Body params: Map<String, Any>): Response<Boolean>
'''+s[en:]
p.write_text(s,encoding="utf-8")


p,s=read("app/src/main/java/com/pinky/dashboard/data/remote/SupabaseClient.kt")
if "createSiteCustomizationSnapshot(" not in s:
    anchor = '''    @POST("rest/v1/rpc/admin_clear_site_customization_draft")
    suspend fun clearSiteCustomizationDraft(@Body params: Map<String, Any>): Response<Boolean>'''
    additions = anchor + '''
 
    @POST("rest/v1/rpc/admin_create_site_customization_snapshot")
    suspend fun createSiteCustomizationSnapshot(@Body params: Map<String, String>): Response<Long>

    @POST("rest/v1/rpc/admin_list_site_customization_versions")
    suspend fun listSiteCustomizationVersions(@Body params: Map<String, Any>): Response<List<com.pinky.dashboard.domain.model.SiteCustomizationVersion>>

    @POST("rest/v1/rpc/admin_restore_site_customization_version")
    suspend fun restoreSiteCustomizationVersion(@Body params: Map<String, Long>): Response<Boolean>'''
    s=once(s,anchor,additions,"CMS version RPC endpoints")
    p.write_text(s,encoding="utf-8")



p,s=read("app/src/main/java/com/pinky/dashboard/ui/PinkyViewModel.kt")
if "private fun buildWebsiteSiteConfig" not in s:
    a=s.find("                val siteConfigObj = SiteCustomizationConfig(")
    b=s.find("\n\n                val customizationsDto =",a)
    if a<0 or b<0: raise SystemExit("SiteCustomizationConfig mapping missing")
    mapping=s[a:b]
    helper="    private fun buildWebsiteSiteConfig(config: WebsiteConfig): SiteCustomizationConfig {\n"+"\n".join("    "+x for x in mapping.splitlines())+"\n        return siteConfigObj\n    }\n\n"
    at=s.find("    fun updateWebsiteConfig(config: WebsiteConfig)")
    if at<0: raise SystemExit("updateWebsiteConfig missing")
    s=s[:at]+helper+s[at:]
    a=s.find("                val siteConfigObj = SiteCustomizationConfig(",at+len(helper))
    b=s.find("\n\n                val customizationsDto =",a)
    if a<0 or b<0: raise SystemExit("mapping refind failed")
    s=s[:a]+"                val siteConfigObj = buildWebsiteSiteConfig(config)"+s[b:]
# Load the saved CMS draft before the published config, so it survives app restarts.
import re
cfg_matches = list(re.finditer(r'(?m)^(\s*)val cfgObj\s*=', s))
if len(cfg_matches) == 1 and "getSiteCustomizationDraft" not in s:
    match = cfg_matches[0]
    indent = match.group(1)
    prelude = (
        indent + "val draftConfig: com.pinky.dashboard.domain.model.SiteCustomizationConfig? = try {\n" +
        indent + "    val draftResponse = SupabaseClient.service.getSiteCustomizationDraft(emptyMap())\n" +
        indent + "    if (draftResponse.isSuccessful) draftResponse.body() else null\n" +
        indent + "} catch (_: Exception) { null }\n"
    )
    s = s[:match.start()] + prelude + s[match.start():]
    s = re.sub(r'(?m)^(\s*)val cfgObj\s*=', r'\1val cfgObj = draftConfig ?: ', s, count=1)
elif "getSiteCustomizationDraft" not in s:
    raise SystemExit("Could not uniquely locate CMS config loader for saved draft restoration")

state='''    private val _websiteConfig = MutableStateFlow(WebsiteConfig())
    val websiteConfig: StateFlow<WebsiteConfig> = _websiteConfig.asStateFlow()'''
if state in s and "_websiteDraftSaveState" not in s:
    s=once(s,state,state+'''
    private val _websiteDraftSaveState = MutableStateFlow("idle")
    val websiteDraftSaveState: StateFlow<String> = _websiteDraftSaveState.asStateFlow()''',"draft state")
if "fun saveWebsiteDraft(config: WebsiteConfig)" not in s:
    method='''
    fun saveWebsiteDraft(config: WebsiteConfig) {
        viewModelScope.launch {
            _websiteDraftSaveState.value = "saving"
            try {
                val siteConfigObj = buildWebsiteSiteConfig(config)
                val response = SupabaseClient.service.saveSiteCustomizationDraft(com.pinky.dashboard.domain.model.SiteCustomizationDraftRequest(siteConfigObj))
                if (!response.isSuccessful) {
                    android.util.Log.e("EloryWebsite", "Draft save failed: " + response.code())
                    _websiteDraftSaveState.value = "error"
                    return@launch
                }
                _websiteConfig.value = config
                _websiteDraftSaveState.value = "success"
            } catch (e: Exception) {
                android.util.Log.e("EloryWebsite", "Draft save failed", e)
                _websiteDraftSaveState.value = "error"
            }
        }
    }

'''
    at=s.find("    fun updateWebsiteConfig(config: WebsiteConfig)")
    if at<0: raise SystemExit("draft method insertion point missing")
    s=s[:at]+method+s[at:]
a=s.find("    fun updateWebsiteConfig(config: WebsiteConfig)"); b=s.find("\n    // Notification management",a)
if a<0 or b<0: raise SystemExit("publish method missing")
pub=s[a:b]
if "saveSiteCustomizationDraft" not in pub:
    pub=once(pub,
'''                val settingsResponse = SupabaseClient.service.upsertStoreSettings(settingsDto)
                val customizationsResponse = SupabaseClient.service.upsertSiteCustomizations(customizationsDto)''',
'''                val draftResponse = SupabaseClient.service.saveSiteCustomizationDraft(com.pinky.dashboard.domain.model.SiteCustomizationDraftRequest(siteConfigObj))
                if (!draftResponse.isSuccessful) {
                    android.util.Log.e("EloryWebsite", "Publish checkpoint failed: " + draftResponse.code())
                    _websiteSaveState.value = "error"
                    return@launch
                }
                val settingsResponse = SupabaseClient.service.upsertStoreSettings(settingsDto)
                val customizationsResponse = SupabaseClient.service.upsertSiteCustomizations(customizationsDto)''',"publish checkpoint")
    pub=once(pub,'                _websiteSaveState.value = "success"', '''                _websiteSaveState.value = "success"
                refreshWebsiteVersions()''',"refresh version history after publish")
    pub=once(pub,"                _websiteConfig.value = config",'''
                val clearDraftResponse = SupabaseClient.service.clearSiteCustomizationDraft(emptyMap())
                if (!clearDraftResponse.isSuccessful) {
                    android.util.Log.w("EloryWebsite", "Published, but draft cleanup failed: " + clearDraftResponse.code())
                }
                _websiteConfig.value = config''',"clear draft")
    s=s[:a]+pub+s[b:]
p.write_text(s,encoding="utf-8")

p,s=read("app/src/main/java/com/pinky/dashboard/ui/PinkyApp.kt")
if "websiteDraftSaveState" not in s:
    s=once(s,"    val websiteSaveState by viewModel.websiteSaveState.collectAsStateWithLifecycle()",
        "    val websiteSaveState by viewModel.websiteSaveState.collectAsStateWithLifecycle()\n    val websiteDraftSaveState by viewModel.websiteDraftSaveState.collectAsStateWithLifecycle()","draft state collect")
if "onSaveDraft = { viewModel.saveWebsiteDraft(it) }" not in s:
    s=once(s,"                                    onSaveConfig = { viewModel.updateWebsiteConfig(it) },",
        "                                    onSaveConfig = { viewModel.updateWebsiteConfig(it) },\n                                    onSaveDraft = { viewModel.saveWebsiteDraft(it) },\n                                    draftSaveState = websiteDraftSaveState,","draft callback")
if "websiteVersions by viewModel.websiteVersions.collectAsStateWithLifecycle()" not in s:
    s=once(s,"    val websiteDraftSaveState by viewModel.websiteDraftSaveState.collectAsStateWithLifecycle()",
        "    val websiteDraftSaveState by viewModel.websiteDraftSaveState.collectAsStateWithLifecycle()\n    val websiteVersions by viewModel.websiteVersions.collectAsStateWithLifecycle()\n    val websiteVersionsLoadState by viewModel.websiteVersionsLoadState.collectAsStateWithLifecycle()\n    val websiteVersionRestoreState by viewModel.websiteVersionRestoreState.collectAsStateWithLifecycle()","website versions state collect")
if "onRefreshWebsiteVersions = { viewModel.refreshWebsiteVersions() }" not in s:
    s=once(s,"                                    draftSaveState = websiteDraftSaveState,",
        "                                    draftSaveState = websiteDraftSaveState,\n                                    websiteVersions = websiteVersions,\n                                    websiteVersionsLoadState = websiteVersionsLoadState,\n                                    websiteVersionRestoreState = websiteVersionRestoreState,\n                                    onRefreshWebsiteVersions = { viewModel.refreshWebsiteVersions() },\n                                    onRestoreWebsiteVersion = { viewModel.restoreWebsiteVersion(it) },","website version callbacks")

p.write_text(s,encoding="utf-8")

p,s=read("app/src/main/java/com/pinky/dashboard/ui/screens/website/WebsiteEditorScreen.kt")
s=s.replace("    saveState: String = \"idle\",\n    modifier: Modifier = Modifier",
    "    saveState: String = \"idle\",\n    onSaveDraft: (WebsiteConfig) -> Unit = {},\n    draftSaveState: String = \"idle\",\n    websiteVersions: List<SiteCustomizationVersion> = emptyList(),\n    websiteVersionsLoadState: String = \"idle\",\n    websiteVersionRestoreState: String = \"idle\",\n    onRefreshWebsiteVersions: () -> Unit = {},\n    onRestoreWebsiteVersion: (Long) -> Unit = {},\n    modifier: Modifier = Modifier",1)
s=s.replace("1-11 = section dialog index","1-12 = section dialog index",1)
if "onRefreshWebsiteVersions()" not in s:
    s=once(s,'''    LaunchedEffect(initialConfig) {
        config = initialConfig
    }''','''    LaunchedEffect(initialConfig) {
        config = initialConfig
    }

    LaunchedEffect(Unit) {
        onRefreshWebsiteVersions()
    }''',"load version history on screen entry")
card='''                    // Card 11: الإعدادات العامة والألوان
                    item {
                        SectionCard(
                            title = "إعدادات عامة وألوان وهوية الموقع",
                            description = "اسم المتجر، تفاصيل السيو والبحث، والخطوط ولون الهوية الأساسي",
                            icon = Icons.Outlined.SettingsSuggest,
                            isActive = true,
                            onToggleActive = null,
                            onClick = { activeEditingDialog = 11 }
                        )
                    }
'''
if "activeEditingDialog = 12" not in s:
    s=once(s,card,card+'''
                    item {
                        SectionCard(
                            title = "ترتيب وظهور أقسام الصفحة",
                            description = "إخفاء الأقسام وترتيبها وإنشاء أقسام مخصصة",
                            icon = Icons.Outlined.ViewList,
                            isActive = true,
                            onToggleActive = null,
                            onClick = { activeEditingDialog = 12 }
                        )
                    }
''',"sections card")
s=s.replace('                    11 -> "هوية وإعدادات الموقع العامة" to Icons.Outlined.SettingsSuggest\n                    else ->',
'                    11 -> "هوية وإعدادات الموقع العامة" to Icons.Outlined.SettingsSuggest\n                    12 -> "ترتيب وظهور أقسام الصفحة" to Icons.Outlined.ViewList\n                    else ->',1)
s=s.replace("                        11 -> GlobalSettingsForm(dialogConfig, onUpdate = { dialogConfig = it })",
"                        11 -> GlobalSettingsForm(dialogConfig, onUpdate = { dialogConfig = it })\n                        12 -> SectionsLayoutForm(dialogConfig, onUpdate = { dialogConfig = it })",1)
s=once(s,'''            onSaveConfig = { updated ->
                config = updated
                onSaveConfig(updated)
            },''','''            onSaveConfig = { updated ->
                config = updated
            },''',"local dialog apply")
if "حفظ مسودة" not in s:
    s=once(s,"            // Mode Tabs: Edit vs Live Preview Mockup",'''
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedButton(onClick = { onSaveDraft(config) }, enabled = draftSaveState != "saving", modifier = Modifier.weight(1f)) {
                    Icon(Icons.Outlined.Save, contentDescription = null)
                    Spacer(Modifier.width(6.dp))
                    Text(if (draftSaveState == "saving") "جارٍ حفظ المسودة..." else "حفظ مسودة")
                }
                Text(
                    when (draftSaveState) {
                        "success" -> "المسودة محفوظة"
                        "error" -> "فشل حفظ المسودة"
                        else -> "التعديلات لا تظهر قبل النشر"
                    },
                    style = MaterialTheme.typography.labelSmall,
                    color = if (draftSaveState == "error") MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            // Mode Tabs: Edit vs Live Preview Mockup''',"draft row")
if "selectedPreviewDevice" not in s:
    s=once(s,"    var selectedTab by remember { mutableIntStateOf(0) } // 0 = Editor, 1 = Live Preview Mockup",
        "    var selectedTab by remember { mutableIntStateOf(0) } // 0 = Editor, 1 = Live Preview Mockup\n    var selectedPreviewDevice by remember { mutableIntStateOf(0) }","preview state")
old='''                // Live Mockup rendering
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp),
                    contentAlignment = Alignment.TopCenter
                ) {
                    PhoneMockupView(
                        config = config,
                        categories = categories,
                        banners = banners
                    )
                }'''
new='''                Column(Modifier.fillMaxSize().padding(12.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        if (selectedPreviewDevice == 0) Button(onClick = { selectedPreviewDevice = 0 }) { Text("معاينة الموبايل") }
                        else OutlinedButton(onClick = { selectedPreviewDevice = 0 }) { Text("معاينة الموبايل") }
                        if (selectedPreviewDevice == 1) Button(onClick = { selectedPreviewDevice = 1 }) { Text("معاينة الكمبيوتر") }
                        else OutlinedButton(onClick = { selectedPreviewDevice = 1 }) { Text("معاينة الكمبيوتر") }
                    }
                    Spacer(Modifier.height(10.dp))
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.TopCenter) {
                        if (selectedPreviewDevice == 0) PhoneMockupView(config = config, categories = categories, banners = banners)
                        else DesktopMockupView(config = config, categories = categories, banners = banners)
                    }
                }'''
if old in s: s=once(s,old,new,"responsive preview")
elif "DesktopMockupView(config = config" not in s: raise SystemExit("phone preview block missing")
s=s.replace('text = { Text("حفظ ونشر التعديلات", fontWeight = FontWeight.Bold) }',
            'text = { Text("نشر التعديلات", fontWeight = FontWeight.Bold) }',1)
p.write_text(s,encoding="utf-8")

desktop=root/"app/src/main/java/com/pinky/dashboard/ui/screens/website/DesktopMockupView.kt"
desktop.write_text(r'''package com.pinky.dashboard.ui.screens.website

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.pinky.dashboard.domain.model.Category
import com.pinky.dashboard.domain.model.Offer
import com.pinky.dashboard.domain.model.WebsiteConfig

@Composable
fun DesktopMockupView(config: WebsiteConfig, categories: List<Category>, banners: List<Offer>) {
    val hero = config.heroSlides.firstOrNull { it.isActive }
    Card(Modifier.fillMaxWidth().fillMaxHeight(.96f), shape=RoundedCornerShape(14.dp),
        border=androidx.compose.foundation.BorderStroke(1.dp,MaterialTheme.colorScheme.outlineVariant)) {
        Column(Modifier.fillMaxSize()) {
            Row(Modifier.fillMaxWidth().background(Color(0xFFF9F5F7)).padding(24.dp),
                verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.SpaceBetween) {
                Text(config.storeName,fontWeight=FontWeight.ExtraBold,fontSize=22.sp,color=Color(0xFF381528))
                Row(horizontalArrangement=Arrangement.spacedBy(18.dp)) {
                    Text("الرئيسية"); Text("الأقسام"); Text("المنتجات"); Text("تواصل معنا")
                }
                Text("♡   🛍",color=Color(0xFFC96F92))
            }
            Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(26.dp),
                verticalArrangement=Arrangement.spacedBy(18.dp)) {
                if(config.showAnnouncementBar) Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(Color(0xFF381528)).padding(9.dp),contentAlignment=Alignment.Center) {
                    Text(config.announcementMsg1,color=Color.White,fontSize=12.sp)
                }
                if(config.showHeroBanner && hero!=null) Row(Modifier.fillMaxWidth().heightIn(min=210.dp).clip(RoundedCornerShape(16.dp)).background(Color(0xFFFFF0F5)),verticalAlignment=Alignment.CenterVertically) {
                    Column(Modifier.weight(1f).padding(24.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
                        Text(hero.smallText,color=Color(0xFF9D5574),fontWeight=FontWeight.Bold)
                        Text(hero.title,color=Color(0xFF381528),fontSize=28.sp,fontWeight=FontWeight.ExtraBold)
                        if(hero.arabicTitle.isNotBlank()) Text(hero.arabicTitle,color=Color(0xFF381528),fontSize=18.sp,fontWeight=FontWeight.Bold)
                        Text(hero.description,color=Color.DarkGray)
                        if(hero.buttonVisible) Text(hero.buttonText,color=Color(0xFFC96F92),fontWeight=FontWeight.Bold)
                    }
                    if(hero.imageUrl.isNotBlank()) AsyncImage(model=hero.mediaUrl.ifBlank{hero.imageUrl},contentDescription=null,
                        modifier=Modifier.weight(1.2f).fillMaxHeight(),contentScale=ContentScale.Crop)
                }
                if(config.categoriesIsVisible) Column(verticalArrangement=Arrangement.spacedBy(10.dp)) {
                    Text(config.categoriesTitle,fontSize=20.sp,fontWeight=FontWeight.Bold)
                    Row(horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                        categories.filter{it.isActive}.take(7).forEach { c ->
                            Column(Modifier.weight(1f),horizontalAlignment=Alignment.CenterHorizontally) {
                                if(c.imageUrl.isNotBlank()) AsyncImage(c.imageUrl,c.name,Modifier.size(70.dp).clip(RoundedCornerShape(35.dp)),contentScale=ContentScale.Crop)
                                else Box(Modifier.size(70.dp).clip(RoundedCornerShape(35.dp)).background(Color(0xFFF8E8EF)))
                                Text(c.name,fontSize=11.sp,textAlign=TextAlign.Center,maxLines=2)
                            }
                        }
                    }
                }
                Column(verticalArrangement=Arrangement.spacedBy(6.dp)) {
                    Text(config.productsSectionTitle,fontSize=20.sp,fontWeight=FontWeight.Bold)
                    Text(config.productsSectionSubtitle,color=Color.Gray,fontSize=12.sp)
                    if(banners.isNotEmpty()) Text("عروض متاحة: "+banners.size,color=Color(0xFFC96F92),fontSize=12.sp)
                }
                if(config.primeIsVisible) Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(Color(0xFF381528)).padding(18.dp)) {
                    Text(config.primeName,color=Color.White,fontWeight=FontWeight.Bold,fontSize=20.sp)
                    Text(config.primeDescription,color=Color.White.copy(alpha=.85f),fontSize=13.sp)
                }
                config.customSections.filter{it.isVisible}.sortedBy{it.sortOrder}.forEach { block ->
                    Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(Color(0xFFFFF0F5)).padding(18.dp)) {
                        if(block.imageUrl.isNotBlank()) AsyncImage(block.imageUrl,null,Modifier.fillMaxWidth().height(170.dp).clip(RoundedCornerShape(10.dp)),contentScale=ContentScale.Crop)
                        Text(block.title,fontSize=18.sp,fontWeight=FontWeight.Bold)
                        Text(block.text,fontSize=13.sp)
                        if(block.buttonText.isNotBlank()) Text(block.buttonText,color=Color(0xFFC96F92),fontWeight=FontWeight.Bold)
                    }
                }
                Text("معاينة تقريبية لتخطيط الكمبيوتر",color=Color.Gray,fontSize=10.sp)
            }
        }
    }
}
''',encoding="utf-8")
print("CMS draft/publish and responsive preview patch applied.")


# 6) Give custom content sections first-class FAQ and trust layouts, and separate SEO title/description.
model_path = root / "app/src/main/java/com/pinky/dashboard/domain/model/WebsiteCustomizationConfig.kt"
model_text = model_path.read_text(encoding="utf-8")
custom_start = model_text.find("data class CustomSiteSectionConfig(")
if custom_start < 0:
    raise SystemExit("CustomSiteSectionConfig was not found")
custom_end = model_text.find("\n)", custom_start)
if custom_end < 0:
    raise SystemExit("CustomSiteSectionConfig closing parenthesis was not found")
custom_block = model_text[custom_start:custom_end+2]
if '@Json(name = "sectionType")' not in custom_block:
    custom_block = custom_block[:-2].rstrip()
    if not custom_block.endswith(","):
        custom_block += ","
    custom_block += '''
    @Json(name = "sectionType") val sectionType: String = "content",
    @Json(name = "faqItems") val faqItems: List<SiteFaqEntry> = emptyList(),
    @Json(name = "trustItems") val trustItems: List<SiteTrustEntry> = emptyList()
)'''
    model_text = model_text[:custom_start] + custom_block + model_text[custom_end+2:]
if "data class SiteFaqEntry(" not in model_text:
    model_text += '''

@JsonClass(generateAdapter = true)
data class SiteFaqEntry(
    @Json(name = "question") val question: String = "",
    @Json(name = "answer") val answer: String = ""
)

@JsonClass(generateAdapter = true)
data class SiteTrustEntry(
    @Json(name = "icon") val icon: String = "✓",
    @Json(name = "title") val title: String = "",
    @Json(name = "description") val description: String = ""
)
'''
model_path.write_text(model_text, encoding="utf-8")

store_model_path = root / "app/src/main/java/com/pinky/dashboard/domain/model/StoreModels.kt"
store_model_text = store_model_path.read_text(encoding="utf-8")
if "val metaTitle: String = \"\"" not in store_model_text:
    store_model_text = once(
        store_model_text,
        '    val storeName: String = "Elory Store",',
        '    val storeName: String = "Elory Store",\n    val metaTitle: String = "",\n    val metaDescription: String = "",',
        "independent SEO fields"
    )
store_model_path.write_text(store_model_text, encoding="utf-8")

vm_path = root / "app/src/main/java/com/pinky/dashboard/ui/PinkyViewModel.kt"
vm_text = vm_path.read_text(encoding="utf-8")
vm_text = vm_text.replace("metaTitle = config.storeName,", "metaTitle = config.metaTitle.ifBlank { config.storeName },", 1)
vm_text = vm_text.replace("metaDescription = config.aboutText,", "metaDescription = config.metaDescription.ifBlank { config.aboutText },", 1)
load_anchor = "                            isStoreOpen = cfgObj?.global?.isStoreOpen ?: currentConfig.isStoreOpen,"
if load_anchor in vm_text and "metaTitle = cfgObj?.global?.metaTitle" not in vm_text:
    vm_text = once(
        vm_text,
        load_anchor,
        load_anchor + '''
                            metaTitle = cfgObj?.global?.metaTitle ?: currentConfig.metaTitle,
                            metaDescription = cfgObj?.global?.metaDescription ?: currentConfig.metaDescription,''',
        "load separate SEO metadata"
    )

# A published snapshot is required before either independently-written settings row is changed.
if "fun refreshWebsiteVersions()" not in vm_text:
    state_anchor = '''    private val _websiteDraftSaveState = MutableStateFlow("idle")
    val websiteDraftSaveState: StateFlow<String> = _websiteDraftSaveState.asStateFlow()'''
    state_add = state_anchor + '''
    private val _websiteVersions = MutableStateFlow<List<com.pinky.dashboard.domain.model.SiteCustomizationVersion>>(emptyList())
    val websiteVersions: StateFlow<List<com.pinky.dashboard.domain.model.SiteCustomizationVersion>> = _websiteVersions.asStateFlow()
    private val _websiteVersionsLoadState = MutableStateFlow("idle")
    val websiteVersionsLoadState: StateFlow<String> = _websiteVersionsLoadState.asStateFlow()
    private val _websiteVersionRestoreState = MutableStateFlow("idle")
    val websiteVersionRestoreState: StateFlow<String> = _websiteVersionRestoreState.asStateFlow()'''
    vm_text = once(vm_text,state_anchor,state_add,"website version state")
    methods = '''
    fun refreshWebsiteVersions() {
        viewModelScope.launch {
            _websiteVersionsLoadState.value = "loading"
            try {
                val response = SupabaseClient.service.listSiteCustomizationVersions(emptyMap())
                if (response.isSuccessful) {
                    _websiteVersions.value = response.body().orEmpty()
                    _websiteVersionsLoadState.value = "success"
                } else {
                    _websiteVersionsLoadState.value = "error"
                    android.util.Log.e("EloryWebsite", "Version history load failed: " + response.code())
                }
            } catch (e: Exception) {
                _websiteVersionsLoadState.value = "error"
                android.util.Log.e("EloryWebsite", "Version history load failed", e)
            }
        }
    }

    fun restoreWebsiteVersion(versionId: Long) {
        viewModelScope.launch {
            _websiteVersionRestoreState.value = "saving"
            try {
                val response = SupabaseClient.service.restoreSiteCustomizationVersion(mapOf("p_version_id" to versionId))
                if (!response.isSuccessful || response.body() != true) {
                    _websiteVersionRestoreState.value = "error"
                    android.util.Log.e("EloryWebsite", "Website version restore failed: " + response.code())
                    return@launch
                }
                val clearDraftResponse = SupabaseClient.service.clearSiteCustomizationDraft(emptyMap())
                if (!clearDraftResponse.isSuccessful) {
                    _websiteVersionRestoreState.value = "error"
                    android.util.Log.e("EloryWebsite", "Version restored but draft cleanup failed: " + clearDraftResponse.code())
                    return@launch
                }
                syncRemainingSupabaseData()
                refreshWebsiteVersions()
                _websiteVersionRestoreState.value = "success"
            } catch (e: Exception) {
                _websiteVersionRestoreState.value = "error"
                android.util.Log.e("EloryWebsite", "Website version restore failed", e)
            }
        }
    }

'''
    insert_at = vm_text.find("    fun saveWebsiteDraft(config: WebsiteConfig)")
    if insert_at < 0:
        raise SystemExit("Website draft method insertion point missing for version history")
    vm_text = vm_text[:insert_at] + methods + vm_text[insert_at:]

publish_start = vm_text.find("    fun updateWebsiteConfig(config: WebsiteConfig)")
publish_end = vm_text.find("\n    // Notification management", publish_start)
if publish_start < 0 or publish_end < 0:
    raise SystemExit("Website publish method bounds missing for version snapshot")
publish = vm_text[publish_start:publish_end]
if "createSiteCustomizationSnapshot(" not in publish:
    snapshot_anchor = "                val settingsResponse = SupabaseClient.service.upsertStoreSettings(settingsDto)"
    snapshot_code = '''                val snapshotResponse = SupabaseClient.service.createSiteCustomizationSnapshot(mapOf("p_label" to "قبل نشر إعدادات الموقع"))
                if (!snapshotResponse.isSuccessful || snapshotResponse.body() == null) {
                    android.util.Log.e("EloryWebsite", "Publish aborted: could not create a recovery snapshot (code=" + snapshotResponse.code() + ").")
                    _websiteSaveState.value = "error"
                    return@launch
                }
                val snapshotId = snapshotResponse.body()!!
                val settingsResponse = SupabaseClient.service.upsertStoreSettings(settingsDto)'''
    publish = once(publish,snapshot_anchor,snapshot_code,"pre-publish snapshot")
if "restoreSiteCustomizationVersion(" not in publish:
    failure_match = re.search(
        r"if\s*\([^)]*settingsResponse\.isSuccessful[^)]*customizationsResponse\.isSuccessful[^)]*\)\s*\{",
        publish
    )
    if failure_match is None:
        raise SystemExit("Website publish response-check block missing for automatic rollback")
    return_pos = publish.find("return@launch", failure_match.start())
    if return_pos < 0:
        raise SystemExit("Website publish failure return missing for automatic rollback")
    rollback_code = '''                    val rollbackResponse = SupabaseClient.service.restoreSiteCustomizationVersion(mapOf("p_version_id" to snapshotId))
                    if (!rollbackResponse.isSuccessful || rollbackResponse.body() != true) {
                        android.util.Log.e("EloryWebsite", "Publish failed and automatic rollback also failed: " + rollbackResponse.code())
                    } else {
                        android.util.Log.w("EloryWebsite", "Partial publish was rolled back to the pre-publish snapshot.")
                    }
'''
    publish = publish[:return_pos] + rollback_code + publish[return_pos:]
vm_text = vm_text[:publish_start] + publish + vm_text[publish_end:]

vm_path.write_text(vm_text, encoding="utf-8")

editor_path = root / "app/src/main/java/com/pinky/dashboard/ui/screens/website/WebsiteEditorScreen.kt"
editor_text = editor_path.read_text(encoding="utf-8")
seo_title_old = '''            value = config.storeName, // Bind or use helper
            onValueChange = { onUpdate(config.copy(storeName = it)) },
            label = { Text("عنوان السيو الترويجي (Meta Title)") },'''
seo_title_new = '''            value = config.metaTitle,
            onValueChange = { onUpdate(config.copy(metaTitle = it)) },
            label = { Text("عنوان السيو (Meta Title)") },'''
if seo_title_old in editor_text:
    editor_text = once(editor_text, seo_title_old, seo_title_new, "independent SEO title editor")
seo_desc_old = '''            value = config.aboutText,
            onValueChange = { onUpdate(config.copy(aboutText = it)) },
            label = { Text("الوصف لمحركات البحث (Meta Description)") },'''
seo_desc_new = '''            value = config.metaDescription,
            onValueChange = { onUpdate(config.copy(metaDescription = it)) },
            label = { Text("الوصف لمحركات البحث (Meta Description)") },'''
if seo_desc_old in editor_text:
    editor_text = once(editor_text, seo_desc_old, seo_desc_new, "independent SEO description editor")

# The promo-center patch owns the hero editor range and can replace the adjacent CMS section editor.
# Reinsert the exact previously reviewed SectionsLayoutForm implementation after all other patches.
if "fun SectionsLayoutForm(" not in editor_text:
    cms_source = (Path(__file__).resolve().parent / "apply-elory-cms-patch.py").read_text(encoding="utf-8")
    layout_marker = "layout='''"
    layout_start = cms_source.find(layout_marker)
    layout_end = cms_source.find("'''", layout_start + len(layout_marker))
    if layout_start < 0 or layout_end < 0:
        raise SystemExit("Could not recover the existing SectionsLayoutForm source")
    layout_source = cms_source[layout_start + len(layout_marker):layout_end].strip("\n")
    category_anchor = "\n@Composable\nfun CategoriesLayoutForm"
    if category_anchor not in editor_text:
        raise SystemExit("Could not find insertion point for SectionsLayoutForm")
    editor_text = editor_text.replace(category_anchor, "\n" + layout_source + category_anchor, 1)

# The custom-section editor can switch between generic content, FAQ accordions and trust cards.
custom_title_field = '''                    OutlinedTextField(local.title, { local=local.copy(title=it) }, label={ Text("عنوان القسم") }, modifier=Modifier.fillMaxWidth())'''
editor_text = editor_text.replace(
        "الحفظ ينشر الإعدادات إلى الموقع.",
        "حفظ المسودة لا يغير الموقع؛ راجع المعاينة ثم اختر نشر التعديلات.",
        1
    )
if custom_title_field in editor_text and "اختيار نوع القسم" not in editor_text:
    section_type_controls = custom_title_field + '''
                    Text("نوع القسم", fontWeight = FontWeight.SemiBold)
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        listOf("content" to "محتوى", "faq" to "أسئلة شائعة", "trust" to "عناصر ثقة").forEach { (kind, label) ->
                            if (local.sectionType == kind) {
                                Button(onClick = { local = local.copy(sectionType = kind) }, modifier = Modifier.weight(1f)) { Text(label) }
                            } else {
                                OutlinedButton(onClick = { local = local.copy(sectionType = kind) }, modifier = Modifier.weight(1f)) { Text(label) }
                            }
                        }
                    }
                    if (local.sectionType == "faq") {
                        Text("الأسئلة والأجوبة", fontWeight = FontWeight.SemiBold)
                        local.faqItems.forEachIndexed { index, entry ->
                            OutlinedTextField(
                                value = entry.question,
                                onValueChange = { value -> local = local.copy(faqItems = local.faqItems.mapIndexed { i, old -> if (i == index) old.copy(question = value) else old }) },
                                label = { Text("السؤال " + (index + 1)) },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = entry.answer,
                                onValueChange = { value -> local = local.copy(faqItems = local.faqItems.mapIndexed { i, old -> if (i == index) old.copy(answer = value) else old }) },
                                label = { Text("الإجابة") },
                                modifier = Modifier.fillMaxWidth(),
                                minLines = 2
                            )
                            TextButton(onClick = { local = local.copy(faqItems = local.faqItems.filterIndexed { i, _ -> i != index }) }) { Text("حذف السؤال") }
                        }
                        OutlinedButton(onClick = { local = local.copy(faqItems = local.faqItems + SiteFaqEntry()) }, modifier = Modifier.fillMaxWidth()) { Text("إضافة سؤال جديد") }
                    } else if (local.sectionType == "trust") {
                        Text("عناصر الثقة", fontWeight = FontWeight.SemiBold)
                        local.trustItems.forEachIndexed { index, entry ->
                            OutlinedTextField(
                                value = entry.icon,
                                onValueChange = { value -> local = local.copy(trustItems = local.trustItems.mapIndexed { i, old -> if (i == index) old.copy(icon = value) else old }) },
                                label = { Text("الرمز أو الأيقونة") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = entry.title,
                                onValueChange = { value -> local = local.copy(trustItems = local.trustItems.mapIndexed { i, old -> if (i == index) old.copy(title = value) else old }) },
                                label = { Text("عنوان عنصر الثقة") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = entry.description,
                                onValueChange = { value -> local = local.copy(trustItems = local.trustItems.mapIndexed { i, old -> if (i == index) old.copy(description = value) else old }) },
                                label = { Text("وصف عنصر الثقة") },
                                modifier = Modifier.fillMaxWidth(),
                                minLines = 2
                            )
                            TextButton(onClick = { local = local.copy(trustItems = local.trustItems.filterIndexed { i, _ -> i != index }) }) { Text("حذف العنصر") }
                        }
                        OutlinedButton(onClick = { local = local.copy(trustItems = local.trustItems + SiteTrustEntry()) }, modifier = Modifier.fillMaxWidth()) { Text("إضافة عنصر ثقة") }
                    }'''
    editor_text = once(editor_text, custom_title_field, section_type_controls, "FAQ and trust editor controls")
editor_path.write_text(editor_text, encoding="utf-8")

print("FAQ/trust section models, editors and independent SEO fields applied.")


# Keep both device previews faithful to the FAQ and trust section types.
phone_path = root / "app/src/main/java/com/pinky/dashboard/ui/screens/website/PhoneMockupView.kt"
if phone_path.is_file():
    phone_text = phone_path.read_text(encoding="utf-8")
    phone_text = once(
        phone_text,
        "                        Text(section.text, fontSize = 10.sp)",
        '''                        if (section.sectionType == "faq") {
                            section.faqItems.forEach { item ->
                                Column(Modifier.fillMaxWidth().padding(top = 6.dp)) {
                                    Text(item.question, fontWeight = FontWeight.Bold, fontSize = 10.sp)
                                    Text(item.answer, fontSize = 9.sp, color = Color.DarkGray)
                                }
                            }
                        } else if (section.sectionType == "trust") {
                            section.trustItems.forEach { item ->
                                Row(Modifier.fillMaxWidth().padding(top = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                                    Text(item.icon, fontSize = 15.sp, color = iconColor)
                                    Spacer(Modifier.width(7.dp))
                                    Column(Modifier.weight(1f)) {
                                        Text(item.title, fontWeight = FontWeight.Bold, fontSize = 10.sp)
                                        Text(item.description, fontSize = 9.sp, color = Color.DarkGray)
                                    }
                                }
                            }
                        } else Text(section.text, fontSize = 10.sp)''',
        "phone preview FAQ/trust rendering"
    )
    phone_path.write_text(phone_text, encoding="utf-8")

desktop_path = root / "app/src/main/java/com/pinky/dashboard/ui/screens/website/DesktopMockupView.kt"
if desktop_path.is_file():
    desktop_text = desktop_path.read_text(encoding="utf-8")
    desktop_text = once(
        desktop_text,
        '                        Text(block.text,fontSize=13.sp)',
        '''                        if (block.sectionType == "faq") {
                            block.faqItems.forEach { item ->
                                Column(Modifier.fillMaxWidth().padding(top = 8.dp)) {
                                    Text(item.question, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                    Text(item.answer, fontSize = 13.sp, color = Color.DarkGray)
                                }
                            }
                        } else if (block.sectionType == "trust") {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                block.trustItems.forEach { item ->
                                    Column(Modifier.weight(1f).padding(8.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                        Text(item.icon, fontSize = 22.sp, color = Color(0xFFC96F92))
                                        Text(item.title, fontWeight = FontWeight.Bold, fontSize = 13.sp, textAlign = TextAlign.Center)
                                        Text(item.description, fontSize = 12.sp, textAlign = TextAlign.Center)
                                    }
                                }
                            }
                        } else Text(block.text,fontSize=13.sp)''',
        "desktop preview FAQ/trust rendering"
    )
    desktop_path.write_text(desktop_text, encoding="utf-8")



# Integrated marketing, appearance and footer controls. These stay in the existing
# WebsiteConfig/site_customizations JSONB path; no duplicate tables or settings rows.
model_path, model_text = read("app/src/main/java/com/pinky/dashboard/domain/model/WebsiteCustomizationConfig.kt")

def append_fields_after_unique_anchor(source, class_name, anchor, fields, marker, label):
    class_start = source.find("data class " + class_name + "(")
    if class_start < 0:
        raise SystemExit(label + " model class missing")
    class_end = source.find("\n)", class_start)
    if class_end < 0:
        raise SystemExit(label + " model class terminator missing")
    class_block = source[class_start:class_end]
    marker_exists = marker in class_block
    anchor_count = source.count(anchor)

    if marker_exists:
        for field in fields:
            property_match = re.search(r"\bval\s+(\w+)", field)
            if property_match and not re.search(r"\bval\s+" + re.escape(property_match.group(1)) + r"\b", class_block):
                raise SystemExit(label + " marker matched but property missing: " + property_match.group(1))
        return source
    if anchor_count != 1:
        raise SystemExit(label + " anchor count " + str(anchor_count))
    updated = source.replace(anchor, anchor + ",\n" + ",\n".join(fields), 1)
    updated_start = updated.find("data class " + class_name + "(")
    updated_end = updated.find("\n)", updated_start)
    if updated_end < 0:
        raise SystemExit(label + " updated model terminator missing")
    updated_block = updated[updated_start:updated_end]
    for field in fields:
        property_match = re.search(r"\bval\s+(\w+)", field)
        if not property_match or not re.search(r"\bval\s+" + re.escape(property_match.group(1)) + r"\b", updated_block):
            raise SystemExit(label + " field was not inserted: " + field)
    return updated

model_text = append_fields_after_unique_anchor(
    model_text,
    "SiteCustomizationConfig",
    '    @Json(name = "customSections") val customSections: List<CustomSiteSectionConfig>? = null',
    [
        '    @Json(name = "productCards") val productCards: ProductCardsConfig? = null',
        '    @Json(name = "popup") val popup: SitePopupConfig? = null'
    ],
    '@Json(name = "productCards")',
    "SiteCustomizationConfig"
)
model_text = append_fields_after_unique_anchor(
    model_text,
    "AnnouncementConfig",
    '    @Json(name = "textColor") val textColor: String = "#FFFFFF"',
    [
        '    @Json(name = "actionUrl") val actionUrl: String = ""',
        '    @Json(name = "rotationSeconds") val rotationSeconds: Int = 3'
    ],
    '@Json(name = "rotationSeconds")',
    "AnnouncementConfig"
)
model_text = append_fields_after_unique_anchor(
    model_text,
    "GlobalConfig",
    '    @Json(name = "isStoreOpen") val isStoreOpen: Boolean = true',
    [
        '    @Json(name = "metaImage") val metaImage: String = ""',
        '    @Json(name = "canonicalUrl") val canonicalUrl: String = ""',
        '    @Json(name = "fontScale") val fontScale: Float = 1.0f',
        '    @Json(name = "sectionSpacingDp") val sectionSpacingDp: Int = 24',
        '    @Json(name = "buttonRadiusDp") val buttonRadiusDp: Int = 20',
        '    @Json(name = "cardRadiusDp") val cardRadiusDp: Int = 18'
    ],
    '@Json(name = "canonicalUrl")',
    "GlobalConfig"
)
model_text = append_fields_after_unique_anchor(
    model_text,
    "FooterConfig",
    '    @Json(name = "credits") val credits: String = "تم التطوير بواسطة Nemrawy"',
    [
        '    @Json(name = "customLinks") val customLinks: List<SiteFooterLink> = emptyList()'
    ],
    '@Json(name = "customLinks")',
    "FooterConfig"
)
if "data class ProductCardsConfig(" not in model_text:
    model_text += '''

@JsonClass(generateAdapter = true)
data class ProductCardsConfig(
    @Json(name = "mobileColumns") val mobileColumns: Int = 2,
    @Json(name = "desktopColumns") val desktopColumns: Int = 4,
    @Json(name = "showDiscountBadge") val showDiscountBadge: Boolean = true,
    @Json(name = "showOldPrice") val showOldPrice: Boolean = true,
    @Json(name = "showPrimePrice") val showPrimePrice: Boolean = true
)

@JsonClass(generateAdapter = true)
data class SitePopupConfig(
    @Json(name = "enabled") val enabled: Boolean = false,
    @Json(name = "title") val title: String = "",
    @Json(name = "message") val message: String = "",
    @Json(name = "imageUrl") val imageUrl: String = "",
    @Json(name = "buttonText") val buttonText: String = "",
    @Json(name = "buttonUrl") val buttonUrl: String = "",
    @Json(name = "delaySeconds") val delaySeconds: Int = 5,
    @Json(name = "cooldownDays") val cooldownDays: Int = 7,
    @Json(name = "showOnMobile") val showOnMobile: Boolean = true,
    @Json(name = "showOnDesktop") val showOnDesktop: Boolean = true
)

@JsonClass(generateAdapter = true)
data class SiteFooterLink(
    @Json(name = "label") val label: String = "",
    @Json(name = "url") val url: String = ""
)
'''

expected_models = {
    "SiteCustomizationConfig": ["productCards", "popup"],
    "AnnouncementConfig": ["actionUrl", "rotationSeconds"],
    "GlobalConfig": ["metaImage", "canonicalUrl", "fontScale", "sectionSpacingDp", "buttonRadiusDp", "cardRadiusDp"],
    "FooterConfig": ["customLinks"]
}
for model_name, property_names in expected_models.items():
    start = model_text.find("data class " + model_name + "(")
    end = model_text.find("\n)", start)
    if start < 0 or end < 0:
        raise SystemExit("CMS Kotlin model is incomplete: " + model_name)
    block = model_text[start:end]
    for property_name in property_names:
        if not re.search(r"\bval\s+" + re.escape(property_name) + r"\b", block):
            raise SystemExit("CMS Kotlin property missing from " + model_name + ": " + property_name)

model_path.write_text(model_text, encoding="utf-8")

# Extend the existing WebsiteConfig model with fields used by the dashboard form.
store_model_path, store_model_text = read("app/src/main/java/com/pinky/dashboard/domain/model/StoreModels.kt")

if "val popupEnabled: Boolean" not in store_model_text:
    store_model_text = append_fields_after_unique_anchor(
        store_model_text,
        "WebsiteConfig",
        '    val footerCredits: String = "تم التطوير بواسطة Nemrawy"',
        [
            '    val announcementActionUrl: String = ""',
            '    val announcementRotationSeconds: Int = 3',
            '    val popupEnabled: Boolean = false',
            '    val popupTitle: String = ""',
            '    val popupMessage: String = ""',
            '    val popupImageUrl: String = ""',
            '    val popupButtonText: String = ""',
            '    val popupButtonUrl: String = ""',
            '    val popupDelaySeconds: Int = 5',
            '    val popupCooldownDays: Int = 7',
            '    val popupShowOnMobile: Boolean = true',
            '    val popupShowOnDesktop: Boolean = true',
            '    val productCardsMobileColumns: Int = 2',
            '    val productCardsDesktopColumns: Int = 4',
            '    val productCardsShowDiscountBadge: Boolean = true',
            '    val productCardsShowOldPrice: Boolean = true',
            '    val productCardsShowPrimePrice: Boolean = true',
            '    val footerCustomLinks: List<SiteFooterLink> = emptyList()',
            '    val seoOgImage: String = ""',
            '    val canonicalUrl: String = ""',
            '    val visualFontScale: Float = 1.0f',
            '    val visualSectionSpacingDp: Int = 24',
            '    val visualButtonRadiusDp: Int = 20',
            '    val visualCardRadiusDp: Int = 18'
        ],
        "val popupEnabled: Boolean",
        "WebsiteConfig"
    )


    
website_start = store_model_text.find("data class WebsiteConfig(")
website_end = store_model_text.find("\n)", website_start)
if website_start < 0 or website_end < 0:
    raise SystemExit("WebsiteConfig model is incomplete")
website_block = store_model_text[website_start:website_end]
for property_name in [
    "announcementActionUrl", "announcementRotationSeconds", "popupEnabled", "popupTitle",
    "popupMessage", "popupImageUrl", "popupButtonText", "popupButtonUrl",
    "popupDelaySeconds", "popupCooldownDays", "popupShowOnMobile", "popupShowOnDesktop",
    "productCardsMobileColumns", "productCardsDesktopColumns", "productCardsShowDiscountBadge",
    "productCardsShowOldPrice", "productCardsShowPrimePrice", "footerCustomLinks",
    "seoOgImage", "canonicalUrl", "visualFontScale", "visualSectionSpacingDp",
    "visualButtonRadiusDp", "visualCardRadiusDp"
]:
    if not re.search(r"\bval\s+" + re.escape(property_name) + r"\b", website_block):
        raise SystemExit("WebsiteConfig property missing: " + property_name)

store_model_path.write_text(store_model_text, encoding="utf-8")

# Append the additional strongly typed fields to the already-centralized mapping.

vm_path, vm_text = read("app/src/main/java/com/pinky/dashboard/ui/PinkyViewModel.kt")
needed_model_imports = [
    "import com.pinky.dashboard.domain.model.ProductCardsConfig",
    "import com.pinky.dashboard.domain.model.SitePopupConfig",
    "import com.pinky.dashboard.domain.model.SiteFooterLink"
]
missing_model_imports = [line for line in needed_model_imports if line not in vm_text]
if missing_model_imports:
    import_matches = list(re.finditer(r"(?m)^import [^\n]+$", vm_text))
    if import_matches:
        insert_at = import_matches[-1].end()
    else:
        insert_at = vm_text.find("\n") + 1
    vm_text = vm_text[:insert_at] + "\n" + "\n".join(missing_model_imports) + vm_text[insert_at:]
helper_start = vm_text.find("private fun buildWebsiteSiteConfig(config: WebsiteConfig)")
if helper_start < 0:
    raise SystemExit("Central website config mapping helper was not found")
helper_end = vm_text.find("\n    fun saveWebsiteDraft", helper_start)
if helper_end < 0:
    raise SystemExit("Central website config mapping helper end was not found")
helper = vm_text[helper_start:helper_end]
if "productCards = ProductCardsConfig(" not in helper:
    old_return = "        return siteConfigObj"
    if helper.count(old_return) != 1:
        raise SystemExit("Central mapping return anchor count " + str(helper.count(old_return)))
    replacement = '''        return siteConfigObj.copy(
            announcement = siteConfigObj.announcement?.copy(
                actionUrl = config.announcementActionUrl,
                rotationSeconds = config.announcementRotationSeconds.coerceIn(1, 30)
            ),
            footer = siteConfigObj.footer?.copy(customLinks = config.footerCustomLinks),
            global = siteConfigObj.global?.copy(
                metaImage = config.seoOgImage,
                canonicalUrl = config.canonicalUrl,
                fontScale = config.visualFontScale.coerceIn(0.85f, 1.20f),
                sectionSpacingDp = config.visualSectionSpacingDp.coerceIn(8, 64),
                buttonRadiusDp = config.visualButtonRadiusDp.coerceIn(0, 36),
                cardRadiusDp = config.visualCardRadiusDp.coerceIn(0, 36)
            ),
            productCards = ProductCardsConfig(
                mobileColumns = config.productCardsMobileColumns.coerceIn(1, 3),
                desktopColumns = config.productCardsDesktopColumns.coerceIn(2, 6),
                showDiscountBadge = config.productCardsShowDiscountBadge,
                showOldPrice = config.productCardsShowOldPrice,
                showPrimePrice = config.productCardsShowPrimePrice
            ),
            popup = SitePopupConfig(
                enabled = config.popupEnabled,
                title = config.popupTitle,
                message = config.popupMessage,
                imageUrl = config.popupImageUrl,
                buttonText = config.popupButtonText,
                buttonUrl = config.popupButtonUrl,
                delaySeconds = config.popupDelaySeconds.coerceIn(0, 120),
                cooldownDays = config.popupCooldownDays.coerceIn(0, 90),
                showOnMobile = config.popupShowOnMobile,
                showOnDesktop = config.popupShowOnDesktop
            )
        )'''
    vm_text = vm_text[:helper_start] + helper.replace(old_return, replacement, 1) + vm_text[helper_end:]

# Restore these settings from the same JSONB config. The store-open mapping is intentionally untouched.
if "popupEnabled = cfgObj?.popup?.enabled" not in vm_text:
    anchor = "footerCredits = cfgObj?.footer?.credits ?: currentConfig.footerCredits"
    if vm_text.count(anchor) != 1:
        raise SystemExit("Website config load footer anchor count " + str(vm_text.count(anchor)))
    extra = '''footerCredits = cfgObj?.footer?.credits ?: currentConfig.footerCredits,
                            announcementActionUrl = cfgObj?.announcement?.actionUrl ?: currentConfig.announcementActionUrl,
                            announcementRotationSeconds = cfgObj?.announcement?.rotationSeconds ?: currentConfig.announcementRotationSeconds,
                            popupEnabled = cfgObj?.popup?.enabled ?: currentConfig.popupEnabled,
                            popupTitle = cfgObj?.popup?.title ?: currentConfig.popupTitle,
                            popupMessage = cfgObj?.popup?.message ?: currentConfig.popupMessage,
                            popupImageUrl = cfgObj?.popup?.imageUrl ?: currentConfig.popupImageUrl,
                            popupButtonText = cfgObj?.popup?.buttonText ?: currentConfig.popupButtonText,
                            popupButtonUrl = cfgObj?.popup?.buttonUrl ?: currentConfig.popupButtonUrl,
                            popupDelaySeconds = cfgObj?.popup?.delaySeconds ?: currentConfig.popupDelaySeconds,
                            popupCooldownDays = cfgObj?.popup?.cooldownDays ?: currentConfig.popupCooldownDays,
                            popupShowOnMobile = cfgObj?.popup?.showOnMobile ?: currentConfig.popupShowOnMobile,
                            popupShowOnDesktop = cfgObj?.popup?.showOnDesktop ?: currentConfig.popupShowOnDesktop,
                            productCardsMobileColumns = cfgObj?.productCards?.mobileColumns ?: currentConfig.productCardsMobileColumns,
                            productCardsDesktopColumns = cfgObj?.productCards?.desktopColumns ?: currentConfig.productCardsDesktopColumns,
                            productCardsShowDiscountBadge = cfgObj?.productCards?.showDiscountBadge ?: currentConfig.productCardsShowDiscountBadge,
                            productCardsShowOldPrice = cfgObj?.productCards?.showOldPrice ?: currentConfig.productCardsShowOldPrice,
                            productCardsShowPrimePrice = cfgObj?.productCards?.showPrimePrice ?: currentConfig.productCardsShowPrimePrice,
                            footerCustomLinks = cfgObj?.footer?.customLinks ?: currentConfig.footerCustomLinks,
                            seoOgImage = cfgObj?.global?.metaImage ?: currentConfig.seoOgImage,
                            canonicalUrl = cfgObj?.global?.canonicalUrl ?: currentConfig.canonicalUrl,
                            visualFontScale = cfgObj?.global?.fontScale ?: currentConfig.visualFontScale,
                            visualSectionSpacingDp = cfgObj?.global?.sectionSpacingDp ?: currentConfig.visualSectionSpacingDp,
                            visualButtonRadiusDp = cfgObj?.global?.buttonRadiusDp ?: currentConfig.visualButtonRadiusDp,
                            visualCardRadiusDp = cfgObj?.global?.cardRadiusDp ?: currentConfig.visualCardRadiusDp'''
    vm_text = vm_text.replace(anchor, extra, 1)
vm_path.write_text(vm_text, encoding="utf-8")

# Add one cohesive 13th editor panel, without changing the existing 11 forms or availability switch.
editor_path, editor_text = read("app/src/main/java/com/pinky/dashboard/ui/screens/website/WebsiteEditorScreen.kt")
card12 = '''                    item {
                        SectionCard(
                            title = "ترتيب وظهور أقسام الصفحة",
                            description = "إخفاء الأقسام وترتيبها وإنشاء أقسام مخصصة",
                            icon = Icons.Outlined.ViewList,
                            isActive = true,
                            onToggleActive = null,
                            onClick = { activeEditingDialog = 12 }
                        )
                    }
'''
if "activeEditingDialog = 13" not in editor_text:
    if editor_text.count(card12) != 1:
        raise SystemExit("Sections editor card anchor count " + str(editor_text.count(card12)))
    editor_text = editor_text.replace(card12, card12 + '''
                    item {
                        SectionCard(
                            title = "التسويق وتنسيق العرض",
                            description = "النوافذ الترويجية، شكل بطاقات المنتجات، وروابط وسياسات المتجر",
                            icon = Icons.Outlined.SettingsSuggest,
                            isActive = true,
                            onToggleActive = null,
                            onClick = { activeEditingDialog = 13 }
                        )
                    }
''', 1)
editor_text = editor_text.replace(
    '                    12 -> "ترتيب وظهور أقسام الصفحة" to Icons.Outlined.ViewList\n                    else ->',
    '                    12 -> "ترتيب وظهور أقسام الصفحة" to Icons.Outlined.ViewList\n                    13 -> "التسويق وتنسيق العرض" to Icons.Outlined.SettingsSuggest\n                    else ->',
    1
)
editor_text = editor_text.replace(
    '                        12 -> SectionsLayoutForm(dialogConfig, onUpdate = { dialogConfig = it })',
    '                        12 -> SectionsLayoutForm(dialogConfig, onUpdate = { dialogConfig = it })\n                        13 -> MarketingAppearanceForm(dialogConfig, onUpdate = { dialogConfig = it })',
    1
)
if "fun MarketingAppearanceForm(" not in editor_text:
    editor_text += '''

@Composable
fun MarketingAppearanceForm(config: WebsiteConfig, onUpdate: (WebsiteConfig) -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("شريط الإعلان", fontWeight = FontWeight.Bold, fontSize = 16.sp)
        OutlinedTextField(
            value = config.announcementActionUrl,
            onValueChange = { onUpdate(config.copy(announcementActionUrl = it)) },
            label = { Text("الرابط عند الضغط على شريط الإعلان") },
            placeholder = { Text("#featured أو https://...") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        OutlinedTextField(
            value = config.announcementRotationSeconds.toString(),
            onValueChange = { v -> v.toIntOrNull()?.let { onUpdate(config.copy(announcementRotationSeconds = it.coerceIn(1, 30))) } },
            label = { Text("مدة عرض كل رسالة بالثواني (1–30)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        Divider()
        Text("النافذة الترويجية المنبثقة", fontWeight = FontWeight.Bold, fontSize = 16.sp)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("تفعيل النافذة")
                Text("تظهر للزائر وفق الجهاز وفترة التكرار المحددين.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Switch(checked = config.popupEnabled, onCheckedChange = { onUpdate(config.copy(popupEnabled = it)) })
        }
        OutlinedTextField(config.popupTitle, { onUpdate(config.copy(popupTitle = it)) }, label = { Text("عنوان النافذة") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(config.popupMessage, { onUpdate(config.copy(popupMessage = it)) }, label = { Text("رسالة النافذة") }, modifier = Modifier.fillMaxWidth(), minLines = 3)
        ImageUploadSelector(
            imageUrl = config.popupImageUrl,
            onUrlChanged = { onUpdate(config.copy(popupImageUrl = it)) },
            bucket = "product-images",
            placeholderText = "رفع صورة النافذة الترويجية"
        )
        OutlinedTextField(config.popupButtonText, { onUpdate(config.copy(popupButtonText = it)) }, label = { Text("نص الزر") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(config.popupButtonUrl, { onUpdate(config.copy(popupButtonUrl = it)) }, label = { Text("رابط الزر") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = config.popupDelaySeconds.toString(),
                onValueChange = { v -> v.toIntOrNull()?.let { onUpdate(config.copy(popupDelaySeconds = it.coerceIn(0, 120))) } },
                label = { Text("تأخير الظهور (ث)") },
                modifier = Modifier.weight(1f),
                singleLine = true
            )
            OutlinedTextField(
                value = config.popupCooldownDays.toString(),
                onValueChange = { v -> v.toIntOrNull()?.let { onUpdate(config.copy(popupCooldownDays = it.coerceIn(0, 90))) } },
                label = { Text("تكرار كل (يوم)") },
                modifier = Modifier.weight(1f),
                singleLine = true
            )
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("إظهار على الموبايل", Modifier.weight(1f))
            Switch(config.popupShowOnMobile, { onUpdate(config.copy(popupShowOnMobile = it)) })
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("إظهار على الكمبيوتر", Modifier.weight(1f))
            Switch(config.popupShowOnDesktop, { onUpdate(config.copy(popupShowOnDesktop = it)) })
        }

        Divider()
        Text("بطاقات المنتجات", fontWeight = FontWeight.Bold, fontSize = 16.sp)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = config.productCardsMobileColumns.toString(),
                onValueChange = { v -> v.toIntOrNull()?.let { onUpdate(config.copy(productCardsMobileColumns = it.coerceIn(1, 3))) } },
                label = { Text("أعمدة الموبايل (1–3)") },
                modifier = Modifier.weight(1f),
                singleLine = true
            )
            OutlinedTextField(
                value = config.productCardsDesktopColumns.toString(),
                onValueChange = { v -> v.toIntOrNull()?.let { onUpdate(config.copy(productCardsDesktopColumns = it.coerceIn(2, 6))) } },
                label = { Text("أعمدة الكمبيوتر (2–6)") },
                modifier = Modifier.weight(1f),
                singleLine = true
            )
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("إظهار شارة الخصم", Modifier.weight(1f))
            Switch(config.productCardsShowDiscountBadge, { onUpdate(config.copy(productCardsShowDiscountBadge = it)) })
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("إظهار السعر القديم", Modifier.weight(1f))
            Switch(config.productCardsShowOldPrice, { onUpdate(config.copy(productCardsShowOldPrice = it)) })
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("إظهار سعر Prime داخل البطاقة", Modifier.weight(1f))
            Switch(config.productCardsShowPrimePrice, { onUpdate(config.copy(productCardsShowPrimePrice = it)) })
        }

        Divider()
        Text("تحسين الهوية والسيو", fontWeight = FontWeight.Bold, fontSize = 16.sp)
        ImageUploadSelector(
            imageUrl = config.seoOgImage,
            onUrlChanged = { onUpdate(config.copy(seoOgImage = it)) },
            bucket = "product-images",
            placeholderText = "صورة المشاركة في الشبكات الاجتماعية"
        )
        OutlinedTextField(config.canonicalUrl, { onUpdate(config.copy(canonicalUrl = it)) }, label = { Text("الرابط الأساسي Canonical URL") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = config.visualFontScale.toString(),
                onValueChange = { v -> v.toFloatOrNull()?.let { onUpdate(config.copy(visualFontScale = it.coerceIn(0.85f, 1.20f))) } },
                label = { Text("مقياس الخط (0.85–1.20)") },
                modifier = Modifier.weight(1f),
                singleLine = true
            )
            OutlinedTextField(
                value = config.visualSectionSpacingDp.toString(),
                onValueChange = { v -> v.toIntOrNull()?.let { onUpdate(config.copy(visualSectionSpacingDp = it.coerceIn(8, 64))) } },
                label = { Text("المسافة بين الأقسام") },
                modifier = Modifier.weight(1f),
                singleLine = true
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = config.visualButtonRadiusDp.toString(),
                onValueChange = { v -> v.toIntOrNull()?.let { onUpdate(config.copy(visualButtonRadiusDp = it.coerceIn(0, 36))) } },
                label = { Text("استدارة الأزرار") },
                modifier = Modifier.weight(1f),
                singleLine = true
            )
            OutlinedTextField(
                value = config.visualCardRadiusDp.toString(),
                onValueChange = { v -> v.toIntOrNull()?.let { onUpdate(config.copy(visualCardRadiusDp = it.coerceIn(0, 36))) } },
                label = { Text("استدارة البطاقات") },
                modifier = Modifier.weight(1f),
                singleLine = true
            )
        }

        Divider()
        Text("روابط إضافية في تذييل المتجر", fontWeight = FontWeight.Bold, fontSize = 16.sp)
        config.footerCustomLinks.forEachIndexed { index, link ->
            Card(border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)) {
                Column(Modifier.fillMaxWidth().padding(10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = link.label,
                        onValueChange = { value ->
                            onUpdate(config.copy(footerCustomLinks = config.footerCustomLinks.mapIndexed { i, old -> if (i == index) old.copy(label = value) else old }))
                        },
                        label = { Text("اسم الرابط") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = link.url,
                        onValueChange = { value ->
                            onUpdate(config.copy(footerCustomLinks = config.footerCustomLinks.mapIndexed { i, old -> if (i == index) old.copy(url = value) else old }))
                        },
                        label = { Text("وجهة الرابط") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    TextButton(onClick = {
                        onUpdate(config.copy(footerCustomLinks = config.footerCustomLinks.filterIndexed { i, _ -> i != index }))
                    }) { Text("حذف الرابط") }
                }
            }
        }
        OutlinedButton(
            onClick = {
                onUpdate(config.copy(footerCustomLinks = config.footerCustomLinks + com.pinky.dashboard.domain.model.SiteFooterLink()))
            },
            modifier = Modifier.fillMaxWidth()
        ) { Icon(Icons.Filled.Add, contentDescription = null); Spacer(Modifier.width(6.dp)); Text("إضافة رابط للتذييل") }
        Text(
            "يتم حفظ هذه الخيارات داخل إعدادات الموقع الحالية. لا تغير إعدادات المنتجات أو الطلبات أو Prime، ولا تتضمن مفتاح فتح/قفل الموقع.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}
'''
# Organize the existing editor cards into four mobile-friendly tabs.
# The store availability card is intentionally untouched and remains before this tab bar.
if "selectedEditorCategory" not in editor_text:
    state_anchor = "    var selectedPreviewDevice by remember { mutableIntStateOf(0) }"
    if editor_text.count(state_anchor) != 1:
        raise SystemExit("Website editor preview state anchor missing or duplicated")
    editor_text = editor_text.replace(
        state_anchor,
        state_anchor + "\n    var selectedEditorCategory by remember { mutableIntStateOf(0) }",
        1
    )

tabs_anchor = "                    // Card 1: الشريط العلوي"
tabs_source = """                    item {
                        Column(
                            modifier = Modifier.fillMaxWidth(),
                            verticalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Text("أقسام محرر الموقع", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall)
                            ScrollableTabRow(
                                selectedTabIndex = selectedEditorCategory,
                                edgePadding = 0.dp,
                                containerColor = MaterialTheme.colorScheme.surface,
                                contentColor = PinkPrimary,
                                modifier = Modifier.testTag("website_editor_category_tabs")
                            ) {
                                listOf("الهيدر والبانرات", "الأقسام والمنتجات", "الصور والتذييل", "الهوية والتسويق", "النسخ والاستعادة")
                                    .forEachIndexed { index, label ->
                                        Tab(
                                            selected = selectedEditorCategory == index,
                                            onClick = { selectedEditorCategory = index },
                                            text = { Text(label, maxLines = 1, overflow = TextOverflow.Ellipsis) }
                                        )
                                    }
                            }
                            Text(
                                when (selectedEditorCategory) {
                                    0 -> "الإعلانات العلوية والهيدر وروابط التنقل والبنرات الرئيسية"
                                    1 -> "الأقسام والمنتجات وPrime ومميزات المتجر"
                                    2 -> "معرض الصور وتذييل المتجر وبيانات التواصل"
                                    3 -> "هوية الموقع وترتيب الأقسام وأدوات التسويق"
                                    else -> "عرض النسخ المحفوظة واستعادة إعدادات الموقع بأمان"
                                },
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }

"""
if "website_editor_category_tabs" not in editor_text:
    if editor_text.count(tabs_anchor) != 1:
        raise SystemExit("Website editor card 1 insertion anchor missing or duplicated")
    editor_text = editor_text.replace(tabs_anchor, tabs_source + tabs_anchor, 1)

def wrap_editor_card(source, dialog_index, tab_index):
    click = "onClick = { activeEditingDialog = " + str(dialog_index) + " }"
    if source.count(click) != 1:
        raise SystemExit("Expected exactly one editor card for dialog " + str(dialog_index) + ", found " + str(source.count(click)))
    click_at = source.find(click)
    start = source.rfind("                    item {", 0, click_at)
    if start < 0:
        raise SystemExit("Could not locate item block for editor dialog " + str(dialog_index))
    end_marker = "\n                    }\n"
    end = source.find(end_marker, click_at)
    if end < 0:
        raise SystemExit("Could not locate end of editor item for dialog " + str(dialog_index))
    block_end = end + len("\n                    }")
    block = source[start:block_end]
    if not block.lstrip().startswith("item {"):
        raise SystemExit("Unexpected editor item structure for dialog " + str(dialog_index))
    indented = "\n".join(("    " + line if line else line) for line in block.split("\n"))
    wrapped = "                    if (selectedEditorCategory == " + str(tab_index) + ") {\n" + indented + "\n                    }"
    return source[:start] + wrapped + source[block_end:]

if "if (selectedEditorCategory == 0)" not in editor_text:
    category_by_dialog = {
        1: 0, 2: 0, 3: 0, 4: 0,
        5: 1, 6: 1, 7: 1, 8: 1,
        9: 2, 10: 2,
        11: 3, 12: 3, 13: 3
    }
    for dialog_index, tab_index in category_by_dialog.items():
        editor_text = wrap_editor_card(editor_text, dialog_index, tab_index)



# Add the live backup and restore panel as the fifth editor tab.
if "WebsiteVersionsPanel(" not in editor_text:
    versions_spacer = '''                    item {
                        Spacer(modifier = Modifier.height(80.dp))
                    }'''
    versions_item = '''                    if (selectedEditorCategory == 4) {
                        item {
                            WebsiteVersionsPanel(
                                versions = websiteVersions,
                                loadState = websiteVersionsLoadState,
                                restoreState = websiteVersionRestoreState,
                                onRefresh = onRefreshWebsiteVersions,
                                onRestore = onRestoreWebsiteVersion
                            )
                        }
                    }

'''
    if editor_text.count(versions_spacer) != 1:
        raise SystemExit("Website editor end spacer anchor missing or duplicated for version history")
    editor_text = editor_text.replace(versions_spacer, versions_item + versions_spacer, 1)

    editor_text += '''

@Composable
fun WebsiteVersionsPanel(
    versions: List<SiteCustomizationVersion>,
    loadState: String,
    restoreState: String,
    onRefresh: () -> Unit,
    onRestore: (Long) -> Unit
) {
    var pendingRestoreId by remember { mutableStateOf<Long?>(null) }
    Column(
        modifier = Modifier.fillMaxWidth().padding(bottom = 80.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("نسخ إعدادات الموقع", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
        Text(
            "يتم إنشاء نسخة تلقائيًا قبل النشر. الاستعادة تعيد إعدادات الموقع المنشورة ولا تغيّر مفتاح فتح/قفل المتجر الحالي.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedButton(onClick = onRefresh, enabled = loadState != "loading") {
                Icon(Icons.Outlined.Refresh, contentDescription = null)
                Spacer(Modifier.width(6.dp))
                Text(if (loadState == "loading") "جارٍ التحديث..." else "تحديث السجل")
            }
            Text(
                when (loadState) {
                    "loading" -> "جارٍ تحميل النسخ"
                    "error" -> "تعذر تحميل سجل النسخ"
                    "success" -> "عدد النسخ: " + versions.size
                    else -> "سجل النسخ"
                },
                style = MaterialTheme.typography.labelSmall,
                color = if (loadState == "error") MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        if (versions.isEmpty() && loadState == "success") {
            Text("لا توجد نسخ احتياطية محفوظة حتى الآن.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        versions.take(30).forEach { version ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                border = CardDefaults.outlinedCardBorder(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(version.label.ifBlank { "نسخة محفوظة" }, fontWeight = FontWeight.SemiBold)
                    Text("التاريخ: " + version.createdAt, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                        OutlinedButton(
                            onClick = { pendingRestoreId = version.id },
                            enabled = restoreState != "saving"
                        ) { Text(if (restoreState == "saving") "جارٍ الاستعادة..." else "استعادة هذه النسخة") }
                    }
                }
            }
        }
        when (restoreState) {
            "success" -> Text("تمت الاستعادة وتحديث بيانات المحرر.", color = MaterialTheme.colorScheme.primary)
            "error" -> Text("تعذرت الاستعادة بالكامل. راجع الاتصال والصلاحيات ثم حدّث السجل.", color = MaterialTheme.colorScheme.error)
        }
    }
    pendingRestoreId?.let { versionId ->
        AlertDialog(
            onDismissRequest = { pendingRestoreId = null },
            title = { Text("تأكيد استعادة النسخة") },
            text = { Text("سيتم استبدال إعدادات الموقع المنشورة بهذه النسخة. لن تتغير حالة مفتاح فتح/قفل المتجر. هل تريد المتابعة؟") },
            confirmButton = {
                TextButton(onClick = {
                    pendingRestoreId = null
                    onRestore(versionId)
                }) { Text("استعادة النسخة") }
            },
            dismissButton = { TextButton(onClick = { pendingRestoreId = null }) { Text("إلغاء") } }
        )
    }
}
'''
editor_path.write_text(editor_text, encoding="utf-8")

print("Integrated marketing, product-card, footer and appearance controls added.")
