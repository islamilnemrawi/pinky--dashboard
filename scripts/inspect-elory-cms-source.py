import os,re
from pathlib import Path
root=Path(os.environ["PROJECT_DIR"])
files=list(root.rglob("*.kt"))
print(f"CMS_SOURCE_REVIEW files={len(files)} project={root}")
terms=re.compile(r"isStoreOpen|isWebsiteOpen|storeOpen|openClose|WebsiteEditorScreen|WebsiteConfig|SiteCustomizationConfig|AnnouncementConfig|FooterConfig|Faq|FAQ|Trust|Seo|SEO|Popup|Draft|Publish|Preview|CustomSiteSection",re.I)
hits=[]
for path in files:
 lines=path.read_text(encoding="utf-8",errors="replace").splitlines()
 for i,line in enumerate(lines):
  if terms.search(line):
   hits.append((path,i,lines))
print(f"CMS_SOURCE_REVIEW matching_lines={sum(1 for p,i,l in hits)}")
for path,i,lines in hits[:100]:
 print(f"\n--- {path.relative_to(root)}:{i+1} ---")
 lo=max(0,i-5); hi=min(len(lines),i+8)
 for n in range(lo,hi): print(f"{n+1}: {lines[n][:400]}")
# Dump complete small config model declarations for accurate mapping.
for path in files:
 lines=path.read_text(encoding="utf-8",errors="replace").splitlines()
 for i,line in enumerate(lines):
  if re.search(r"data class (WebsiteConfig|SiteCustomizationConfig|AnnouncementConfig|FooterConfig|GlobalConfig|CustomSiteSectionConfig|Faq|FAQ|Trust)",line):
   depth=0; started=False; out=[]
   for n in range(i,min(len(lines),i+180)):
    out.append(f"{n+1}: {lines[n]}")
    depth+=lines[n].count("{")-lines[n].count("}")
    started |= "{" in lines[n]
    if started and depth<=0: break
   print(f"\n=== MODEL {path.relative_to(root)}:{i+1} ===")
   print("\n".join(out))
# Locate the exact availability switch and its enclosing composable.
for path in files:
 lines=path.read_text(encoding="utf-8",errors="replace").splitlines()
 for i,line in enumerate(lines):
  if re.search(r"isStoreOpen|isWebsiteOpen|storeOpen|openClose",line,re.I):
   print(f"\n=== AVAILABILITY CONTROL {path.relative_to(root)}:{i+1} ===")
   for n in range(max(0,i-22),min(len(lines),i+28)): print(f"{n+1}: {lines[n]}")
