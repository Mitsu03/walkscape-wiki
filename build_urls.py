import re, glob, os, urllib.parse

BASE = "https://wiki.walkscape.app/wiki/"
cache = ".firecrawl"

# Namespaces / pages to EXCLUDE from the curated core
EXCLUDE_PREFIX = ("File:", "Special:", "Category:", "Talk:", "Template:",
                  "Help:", "MediaWiki:", "User:", "Property:")
EXCLUDE_EXACT = {
    "WalkScape:_Grind_by_walking!",  # main page, handled separately
}
# Meta/community pages not part of core gameplay reference
EXCLUDE_CONTAINS = ("Devblogs", "Illustrations", "How_to_contribute",
                    "Community_Guides", "Community_Gear_Sets", "Rumors",
                    "Job_Boards", "Mailbox", "Events", "Achievements_",
                    "Choose_Your_Own_Adventure", "Dry_Calculator")

urls = set()

# 1. sitemap urls
if os.path.exists("data/urls.txt"):
    for line in open("data/urls.txt", encoding="utf-8"):
        u = line.strip()
        if u.startswith(BASE):
            urls.add(u)

# 2. links from all cached pages
link_re = re.compile(r"https://wiki\.walkscape\.app/wiki/([^\s)\"'\]#|]+)")
for f in glob.glob(os.path.join(cache, "*.md")):
    txt = open(f, encoding="utf-8", errors="ignore").read()
    for m in link_re.findall(txt):
        page = m.rstrip(").,")
        page = urllib.parse.unquote(page)
        if any(page.startswith(p) for p in EXCLUDE_PREFIX):
            continue
        if page in EXCLUDE_EXACT:
            continue
        if any(c in page for c in EXCLUDE_CONTAINS):
            continue
        # skip anchors / query
        if "?" in page or "=" in page:
            continue
        urls.add(BASE + urllib.parse.quote(page))

urls = sorted(urls)
with open("data/master_urls.txt", "w", encoding="utf-8") as out:
    out.write("\n".join(urls) + "\n")
print(f"Total core URLs: {len(urls)}")
for u in urls[:15]:
    print(" ", u)
