import os
from pathlib import Path
root = Path(os.environ["PROJECT_DIR"])
targets = {
 "WebsiteCustomizationConfig.kt": [
  "data class SiteCustomizationConfig(", "data class AnnouncementConfig(", "data class FooterConfig(",
  "data class GlobalConfig(", "data class CustomSiteSectionConfig("
 ],
 "StoreModels.kt": ["data class WebsiteConfig("],
 "WebsiteEditorScreen.kt": [
  "fun WebsiteEditorScreen(", "fun GlobalSettingsForm(", "fun AnnouncementForm(",
  "fun FooterForm(", "Switch(checked = config.isStoreOpen"
 ],
 "PinkyViewModel.kt": ["private fun buildWebsiteSiteConfig(", "fun updateWebsiteConfig(", "fun saveWebsiteDraft("]
}
for filename, markers in targets.items():
 matches=list(root.rglob(filename))
 print(f"\n===== {filename}: {len(matches)} file(s) =====")
 if not matches: continue
 source=matches[0].read_text(encoding="utf-8")
 for marker in markers:
  pos=source.find(marker)
  print(f"\n--- {marker}: {'FOUND' if pos>=0 else 'missing'} ---")
  if pos>=0: print(source[max(0,pos-500):min(len(source),pos+4500)])
