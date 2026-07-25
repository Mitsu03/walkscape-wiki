#!/usr/bin/env python3
"""Turn the crawled .firecrawl/*.md pages into a clean structured JSON
for the WalkScape Companion web app."""
import re, glob, os, json, html, urllib.parse, hashlib
import markdown

# url -> short id, collected while cleaning pages
IMG_MAP = {}
def img_id(url):
    h = hashlib.sha1(url.encode()).hexdigest()[:12]
    IMG_MAP[h] = url
    return h

CACHE = ".firecrawl"
PREFIX = "wiki.walkscape.app-wiki-"

# --- page slug helpers -------------------------------------------------
def file_to_slug(path):
    name = os.path.basename(path)
    assert name.startswith(PREFIX) and name.endswith(".md")
    raw = name[len(PREFIX):-3]
    return raw  # already the wiki page title with underscores / %xx

def slug_to_title(slug):
    if slug == "Home":
        return "Welcome to WalkScape"
    t = urllib.parse.unquote(slug).replace("_", " ")
    return t

# --- cleaning ----------------------------------------------------------
SKIP_HEADERS = {"### Namespaces", "### More", "### Page actions",
                "### In more languages", "### Read", "## Navigation",
                "## Wiki tools", "## Page tools", "## Categories",
                "### Actions"}
FOOTER_MARKERS = ("Retrieved from \"", "Retrieved from [", "## Navigation",
                  "## Wiki tools", "This page was last edited")

CAT_RE = re.compile(r"/wiki/Category:([^\s)\"'\]#|]+)")

def extract_categories(text):
    cats = []
    for m in CAT_RE.findall(text):
        c = urllib.parse.unquote(m).replace("_", " ").rstrip(").,")
        if c not in cats:
            cats.append(c)
    return cats

CAP = 13000  # max chars of cleaned markdown before we truncate + link out

def cap_markdown(md, source_url):
    if len(md) <= CAP:
        return md
    cut = md.rfind("\n\n", 0, CAP)
    if cut < CAP * 0.4:
        cut = CAP
    trimmed = md[:cut].rstrip()
    trimmed += ("\n\n> **This is a long reference entry.** The full table "
                "continues on the [official WalkScape wiki](" + source_url + ") ↗")
    return trimmed

def clean_markdown(text, title):
    lines = text.splitlines()
    # find H1
    start = 0
    for i, ln in enumerate(lines):
        if ln.startswith("# "):
            start = i + 1
            break
    # find footer
    end = len(lines)
    for i in range(start, len(lines)):
        if any(mk in lines[i] for mk in FOOTER_MARKERS):
            end = i
            break
    body = lines[start:end]

    out = []
    skip = False
    skip_toc = False
    for ln in body:
        s = ln.strip()
        if s == "From Walkscape Walkthrough":
            continue
        if s in ("### Search", "**Tip of the day**"):
            continue
        # TOC block
        if s == "## Contents":
            skip_toc = True
            continue
        if skip_toc:
            if s.startswith("## ") or s.startswith("# "):
                skip_toc = False
                # fallthrough to normal handling of this heading
            else:
                continue
        # nav sub-blocks
        if s in SKIP_HEADERS:
            skip = True
            continue
        if skip:
            if s == "" or s.startswith("-") or s.startswith("*") \
               or s.startswith("[") or s.startswith("!") or s == "More":
                continue
            skip = False
        out.append(ln)

    md = "\n".join(out)
    # collapse >2 blank lines
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    # strip collapse arrows / stray unicode markers in headings
    md = md.replace("▾", "").replace("▸", "")
    return md

# --- link + image rewriting on rendered HTML --------------------------
GIF_RE = re.compile(r"\.gif($|\?)", re.I)
def _img_repl(m):
    tag = m.group(0)
    src = re.search(r'src="([^"]+)"', tag)
    if not src:
        return ""
    url = html.unescape(src.group(1))
    if not url.startswith("https://wiki.walkscape.app/images/"):
        return ""
    if GIF_RE.search(url):
        return ""  # animated gifs are too heavy to inline
    alt = re.search(r'alt="([^"]*)"', tag)
    alt = alt.group(1) if alt else ""
    return '<img data-i="%s" alt="%s" loading="lazy">' % (img_id(url), alt)

def rewrite_html(html_str, have_slugs):
    # keep wiki images as resolvable refs (embedded later as data URIs)
    html_str = re.sub(r"<img[^>]*>", _img_repl, html_str)
    # empty anchors left over
    html_str = re.sub(r"<a[^>]*>\s*</a>", "", html_str)

    def repl(m):
        href = m.group(1)
        # internal wiki link?
        mm = re.match(r"https?://wiki\.walkscape\.app/wiki/([^\"#?]+)", href)
        if mm:
            page = mm.group(1)
            dec = urllib.parse.unquote(page)
            key = dec  # compare against slugs (decoded, underscores)
            if key in have_slugs:
                return 'href="#/' + urllib.parse.quote(page) + '"'
            # namespaced/meta or missing -> external
            return 'href="https://wiki.walkscape.app/wiki/' + page + '" target="_blank" rel="noopener"'
        # index.php / other tesla-app links -> external new tab
        if href.startswith("http"):
            return 'href="' + href + '" target="_blank" rel="noopener"'
        return m.group(0)

    html_str = re.sub(r'href="([^"]+)"', repl, html_str)
    return html_str

# --- categorization ----------------------------------------------------
SKILL_PAGES = set()  # filled from Category:Skills membership

def primary_section(slug, title, cats):
    lc = [c.lower() for c in cats]
    def has(*keys):
        return any(any(k in c for c in lc) for k in keys)

    if slug == "Home":
        return "Basics & Reference"
    # explicit index/basics pages
    basics = {"Skills", "Activities", "Items", "Equipment", "Keywords",
              "Attributes", "Character_Level", "Inventory", "Materials",
              "Consumables", "Gear", "Services", "Locations", "Arenum",
              "Glossary", "Abilities", "Achievements", "Chests"}
    if slug in basics:
        return "Basics & Reference"
    if slug.startswith("Guide:") or slug.startswith("Gear:"):
        return "Guides"
    # keyword pages are named "<X>_Keyword"
    if slug.endswith("_Keyword") or title.endswith("Keyword"):
        return "Keywords"
    # item-list / collection pages
    if slug.endswith("_Items") or slug in ("Gems", "Crafted_Items", "Food",
            "Tools", "Trinkets", "Rings", "Weapons", "Logs", "Ores", "Bars",
            "Lore_Items"):
        return "Items"
    if "skills" in lc and slug != "Skills":
        return "Skills"
    if "activities" in lc or has("activit"):
        return "Activities"
    if has("location", "cities", "areas", "region"):
        return "Locations"
    if has("keyword"):
        return "Keywords"
    if has("item", "material", "consumable", "equipment", "food", "tool",
           "trinket", "ring", "gear", "weapon", "armor", "armour",
           "resource", "log", "ore", "fish", "bar", "gem"):
        return "Items"
    return "Basics & Reference"

# --- main --------------------------------------------------------------
def main():
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])
    files = sorted(glob.glob(os.path.join(CACHE, "*.md")))
    raw = {}
    for f in files:
        slug = file_to_slug(f)
        text = open(f, encoding="utf-8", errors="ignore").read()
        raw[slug] = text
    # home page (title has ':' -> can't be a Windows filename, loaded apart)
    if os.path.exists("data/home.md"):
        raw["Home"] = open("data/home.md", encoding="utf-8", errors="ignore").read()

    have = set(urllib.parse.unquote(s) for s in raw.keys())

    LANG = re.compile(r"[-./](de|fr|es|it|pt|pl|nl|ru|zh|ja|ko|tr|cs|fi|sv|da"
                      r"|no|uk|hu|ro|el|he|ar|th|id|vi|hr|sk|sl|et|lt|lv)$", re.I)
    pages = {}
    for slug, text in raw.items():
        title = slug_to_title(slug)
        if slug != "Home":
            # drop non-English language variants (e.g. Materials.de)
            if LANG.search(slug):
                continue
            # drop malformed slugs where the link parser dropped a ")"
            if "(" in title and ")" not in title:
                continue
        cats = extract_categories(text)
        body_md = clean_markdown(text, title)
        if len(body_md) < 15:
            continue  # empty/redirect stub
        if slug == "Home":
            source_url = "https://wiki.walkscape.app/wiki/WalkScape:_Grind_by_walking!"
        else:
            source_url = "https://wiki.walkscape.app/wiki/" + slug
        body_md = cap_markdown(body_md, source_url)
        md.reset()
        body_html = md.convert(body_md)
        body_html = rewrite_html(body_html, have)
        # the home page's giant MediaWiki nav table renders cramped; drop it
        # (our own category cards replace it)
        if slug == "Home":
            body_html = re.sub(r"<table.*?</table>", "", body_html, flags=re.S)
            # drop the wiki's "Install as a PWA" note (irrelevant here)
            body_html = re.sub(r"<p>[^<]*Install the Wiki as a PWA.*", "",
                               body_html, flags=re.S)
        # minify: collapse whitespace-only gaps between tags
        body_html = re.sub(r">\s+<", "><", body_html)
        section = primary_section(slug, title, cats)
        # plain text for search
        plain = re.sub(r"<[^>]+>", " ", body_html)
        plain = html.unescape(re.sub(r"\s+", " ", plain)).strip()
        pages[slug] = {
            "title": title,
            "section": section,
            "categories": cats,
            "html": body_html,
            "text": plain[:240],
        }

    # build category index
    sections = {}
    for slug, p in pages.items():
        sections.setdefault(p["section"], []).append(slug)
    for s in sections:
        sections[s].sort(key=lambda x: pages[x]["title"].lower())

    data = {"pages": pages, "sections": sections,
            "count": len(pages),
            "home": "Home"}
    os.makedirs("data", exist_ok=True)
    with open("data/wiki_data.json", "w", encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False)
    with open("data/img_map.json", "w", encoding="utf-8") as out:
        json.dump(IMG_MAP, out)
    print(f"Pages: {len(pages)} | images referenced: {len(IMG_MAP)}")
    for s in sorted(sections, key=lambda x: -len(sections[x])):
        print(f"  {s}: {len(sections[s])}")
    return

if __name__ == "__main__":
    main()
