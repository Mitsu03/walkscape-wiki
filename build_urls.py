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
# Non-English variants (Abilities/fi, Achievements/de). build_data.py discards
# these, so crawling them only burns API credits. Keep this in step with the
# LANG regex there.
LANG_RE = re.compile(r"[-./](de|fr|es|it|pt|pl|nl|ru|zh|ja|ko|tr|cs|fi|sv|da"
                     r"|no|uk|hu|ro|el|he|ar|th|id|vi|hr|sk|sl|et|lt|lv)$",
                     re.I)

urls = set()

# 1. sitemap urls
if os.path.exists("data/urls.txt"):
    for line in open("data/urls.txt", encoding="utf-8"):
        u = line.strip()
        if u.startswith(BASE):
            urls.add(u)

# 2. links from all cached pages
# NB: ")" is deliberately allowed in the match. Wiki titles like
# "Work_Efficiency_(Mechanics)" contain balanced parentheses, and excluding ")"
# here silently truncated them to "Work_Efficiency_(Mechanics" - which crawls
# as a non-existent page. trim_parens() below drops only the unbalanced ")"
# that closes the surrounding markdown link.
link_re = re.compile(r"https://wiki\.walkscape\.app/wiki/([^\s\"'\]#|]+)")


def trim_parens(page):
    """Cut the title at the first ")" that closes no "(" of its own.

    "Work_Efficiency_(Mechanics)" survives intact; "Core_Mechanics)" - where the
    ")" belongs to the enclosing "[text](url)" - loses its trailing bracket.
    """
    depth = 0
    for i, ch in enumerate(page):
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth == 0:
                return page[:i]
            depth -= 1
    return page


for f in glob.glob(os.path.join(cache, "*.md")):
    txt = open(f, encoding="utf-8", errors="ignore").read()
    for m in link_re.findall(txt):
        page = trim_parens(m).rstrip(".,")
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
        if LANG_RE.search(page):
            continue
        urls.add(BASE + urllib.parse.quote(page))

urls = sorted(urls)
with open("data/master_urls.txt", "w", encoding="utf-8") as out:
    out.write("\n".join(urls) + "\n")
print(f"Total core URLs: {len(urls)}")
for u in urls[:15]:
    print(" ", u)
