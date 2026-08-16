#!/usr/bin/env python3
"""Turn the crawled .firecrawl/*.md pages into a clean structured JSON
for the WalkScape Companion web app.

Output: data/wiki_data.json
  pages[slug] = {title, section, sub, tags, html, text, icon, related}
  sections[section] = [slug, ...]
  subs[section] = [subtype, ...]   (ordered, only non-empty ones)
"""
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


# --- redirects ---------------------------------------------------------
# fetch_pages.py records every title the wiki resolved elsewhere. They must not
# become pages of their own (that ships one article under two titles), but they
# are still linked to all over the wiki, so their links have to land somewhere.
def _load_redirects():
    try:
        with open("data/redirects.json", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return {}
    flat = {}
    for src in raw:
        # Follow chains: MediaWiki does not resolve a double redirect itself,
        # so A -> B -> C arrives here as two separate hops.
        seen, tgt = {src}, raw[src]
        while tgt in raw and tgt not in seen:
            seen.add(tgt)
            tgt = raw[tgt]
        if tgt != src:
            flat[urllib.parse.unquote(src)] = urllib.parse.unquote(tgt)
    return flat

REDIRECTS = _load_redirects()

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
    if t.startswith("Walkscape Walkthrough:"):
        t = t[22:]
    # The Guide: and Gear: namespaces shadow real pages - there is a Gear:Agility
    # gear set, a Guide:Agility walkthrough AND the Agility skill. Dropping the
    # namespace outright made all three read as plain "Agility", which is
    # indistinguishable in search results and category lists. Keep the plain
    # name up front, where it sorts and matches, and qualify it instead.
    if t.startswith("Guide:"):
        t = t[6:].replace("/", " - ") + " (guide)"
    elif t.startswith("Gear:"):
        t = t[5:].replace("/", " - ") + " (gear set)"
    # "Versions/512" is a patch-notes subpage; name it as one.
    if t.startswith("Versions/"):
        t = "Version " + t[len("Versions/"):]
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

# Cap on RENDERED html (images are refs, so this is generous). Sized to be a
# safety valve against one runaway page, NOT a page-weight budget: at 46000 it
# was truncating 113 pages and cutting 86% of "Equipment" (46 KB shipped of
# 335 KB), which is the opposite of what this project is for. Measured across
# every truncated page, lifting the cap entirely costs 1.91 MB raw - about 8.7%
# of index.html - to un-truncate all 113. The largest page in the corpus renders
# to 335 KB, so this leaves room for growth while still bounding the pathological
# case. Raise it rather than lowering it if pages start hitting it again.
HTML_CAP = 400000

def cap_html(h, url):
    if len(h) <= HTML_CAP:
        return h
    # prefer cutting at a table-row boundary so recipe tables stay intact
    cut = h.rfind("</tr>", 0, HTML_CAP)
    tail = ""
    if cut > HTML_CAP * 0.5:
        h = h[:cut + 5]
        if h.count("<table>") > h.count("</table>"):
            tail = "</tbody></table>"
    else:
        cut = h.rfind("</p>", 0, HTML_CAP)
        h = h[:(cut + 4) if cut > 0 else HTML_CAP]
    note = ('<blockquote class="cont"><strong>This reference continues on the '
            'official WalkScape wiki.</strong> The remaining rows were too long '
            'to bundle offline. <a href="%s" target="_blank" rel="noopener">'
            'Read the full page</a></blockquote>' % url)
    return h + tail + note

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
            # An image ends the nav block: the wiki's nav sub-blocks are pure
            # link lists, so the first line carrying an image is already page
            # content. Without this, pages whose whole body IS images (e.g.
            # Troubleshooting, which is two screenshots and no prose) got
            # swallowed here and then dropped as empty stubs.
            if "![" in s:
                skip = False
            elif s == "" or s.startswith("-") or s.startswith("*") \
                    or s.startswith("[") or s.startswith("!") or s == "More":
                continue
            else:
                skip = False
        out.append(ln)

    md = "\n".join(out)
    # collapse >2 blank lines
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    # strip collapse arrows / stray unicode markers in headings
    md = md.replace("\u25be", "").replace("\u25b8", "")
    md = pad_tables(md)
    return md

# --- table normalisation ----------------------------------------------
# MediaWiki infoboxes render as a table whose *header* is a single merged
# title cell, but whose body rows have two columns (label | value). The
# python-markdown tables extension fixes the column count from the header
# row and silently drops every extra body cell, so all the values (Rarity,
# Type, Slot, Value...) vanish. Pad the header + delimiter of each table
# block out to the widest row so those value cells survive.
_DELIM_RE = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$")

def _ncols(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return len(s.split("|"))

def pad_tables(md_text):
    lines = md_text.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]
        # a table block: a header row (starts with |) immediately followed
        # by a delimiter row of dashes.
        if ln.lstrip().startswith("|") and i + 1 < n and \
                _DELIM_RE.match(lines[i + 1]) and "-" in lines[i + 1]:
            j = i + 2
            while j < n and lines[j].lstrip().startswith("|"):
                j += 1
            block = lines[i:j]
            maxc = max(_ncols(b) for b in block)
            hcols = _ncols(block[0])
            if maxc > hcols:
                header = block[0].rstrip()
                if not header.endswith("|"):
                    header += " |"
                header += " |" * (maxc - hcols)
                delim = "| " + " | ".join(["---"] * maxc) + " |"
                out.append(header)
                out.append(delim)
                out.extend(block[2:])
            else:
                out.extend(block)
            i = j
            continue
        out.append(ln)
        i += 1
    return "\n".join(out)

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
    # NB: no loading="lazy" — every image is an inline data-URI (no network),
    # and lazy loading collapses viewBox-only SVG icons to 0 width in tables.
    return '<img data-i="%s" alt="%s">' % (img_id(url), alt)

# Every wiki image arrives wrapped in a link to its File: description page.
# Offline, that link goes nowhere useful - and the wrappers were 31% of all
# page HTML (4.9 MB across the corpus), so the picture stays and the link goes.
_FILE_WRAP_RE = re.compile(
    r'<a href="https://wiki\.walkscape\.app/wiki/File:[^"]*"[^>]*>'
    r'(<img[^>]*>)</a>')

_DUP_TITLE_RE = re.compile(r'<a ([^>]*?) ?title="([^"]*)"([^>]*)>([^<]*)</a>')


def _drop_dup_title(m):
    before, title, after, text = m.groups()
    if title.strip() != text.strip():
        return m.group(0)
    attrs = (before + after).strip()
    return "<a %s>%s</a>" % (attrs, text)


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
            # MediaWiki language-redirect prefix used by recipe/item links
            # (e.g. Special:MyLanguage/Copper_bar) -> resolve to the real page
            for pre in ("Special:MyLanguage/", "Special:MyLanguage:"):
                if page.startswith(pre):
                    page = page[len(pre):]
                    break
            dec = urllib.parse.unquote(page)
            # a link to a redirect belongs on the page it redirects to
            dec = REDIRECTS.get(dec, dec)
            key = dec  # compare against slugs (decoded, underscores)
            if key in have_slugs:
                # Encode the DECODED key, never `page` - `page` may already be
                # percent-encoded, and re-quoting it turns "%27" into "%2527",
                # which the router then decodes to "%27" and fails to find.
                return 'href="#/' + urllib.parse.quote(dec) + '"'
            # namespaced/meta or missing -> external
            # target/rel are applied at render time instead of being repeated
            # here - 59k copies of them cost 1.8 MB.
            return 'href="https://wiki.walkscape.app/wiki/' + page + '"'
        # index.php / other links -> external new tab
        if href.startswith("http"):
            return 'href="' + href + '"'
        return m.group(0)

    html_str = re.sub(r'href="([^"]+)"', repl, html_str)
    # unwrap images from their File: description links (see _FILE_WRAP_RE)
    html_str = _FILE_WRAP_RE.sub(r"\1", html_str)
    # MediaWiki gives every link a title that usually just repeats the link
    # text; as a tooltip that is noise, and it costs ~0.6 MB. Titles that say
    # something the text does not are kept.
    html_str = _DUP_TITLE_RE.sub(_drop_dup_title, html_str)
    # also clean the language-redirect prefix out of title tooltips
    html_str = html_str.replace("Special:MyLanguage/", "").replace(
        "Special:MyLanguage:", "")
    return html_str

# ======================================================================
#  CLASSIFICATION
# ======================================================================
# Eight top-level sections. Everything lands in exactly one of them; the
# extra facets a page belongs to become tags instead of duplicate entries.
START, SKILLS, ACTS, ITEMS, LOCS, SYS, GUIDES, GLOSS = (
    "Start Here", "Skills", "Activities", "Items & Equipment",
    "Locations", "Game Systems", "Guides", "Glossary")

# --- curated overrides, audited against data/master_urls.txt ----------
# Onboarding + wiki meta.
START_PAGES = {
    "Home", "Tutorial", "FAQs", "Troubleshooting", "Tips", "Shortcuts",
    "Versions", "Walkscape_Walkthrough:About",
    "Walkscape_Walkthrough:General_disclaimer",
    "Walkscape_Walkthrough:Privacy_policy",
}
ABOUT_PAGES = {"Walkscape_Walkthrough:About",
               "Walkscape_Walkthrough:General_disclaimer",
               "Walkscape_Walkthrough:Privacy_policy", "Versions"}

# The 14 trainable skills, split the way players think about them.
# The complete list of trainable skills. Membership is the whole test - there is
# deliberately no category-based fallback, since the wiki tags anything
# skill-adjacent with the Skills category.
#
# "Forge" and "Traveling" used to be listed here and were dropped once redirect
# handling made them unreachable: the wiki renamed Forge to Smithing (already
# below) and retired Traveling, folding it into Agility. Both matched nothing,
# so removing them changes no output.
SKILL_GROUPS = {
    "Gathering": {"Fishing", "Foraging", "Hunting", "Mining", "Woodcutting",
                  "Farming"},
    "Artisan": {"Carpentry", "Cooking", "Crafting", "Smithing", "Tailoring",
                "Trinketry"},
    "Support": {"Agility"},
}
SKILL_PAGES = set().union(*SKILL_GROUPS.values())

# Venues where a skill is practised ("Use blazing forges to smelt ores..."). The
# wiki tags them with the skill's category, which used to file them as skills;
# they are places, and belong with the other buildings.
#
# As of the 2026-08 refresh every one of these is a redirect to its skill (or
# gone), so redirect handling drops them before this rule is reached and the
# set matches nothing. It is kept because the wiki has split venues back out
# before: if one returns as a real page, the category fallback would file it
# under Skills again, which is the bug this rule exists to stop.
FACILITY_PAGES = {
    "Forges", "Kitchens", "Sawmills", "Workshops", "Tanneries",
    "Erdwiss_Trinketry_Factory",
}

# Attribute triples: <Name>, <Name>_(Mechanics, <Name>_Items all describe one
# character attribute. The bare page is the system, the _Items page is an index.
ATTRIBUTES = {
    "Work_Efficiency", "Steps_Required", "Item_Finding", "Double_Action",
    "Double_Rewards", "Quality_Outcome", "Fine_Material_Finding",
    "Chest_Finding", "Find_Gems", "Find_Bird_Nests", "Find_Collectibles",
    "Inventory_Space", "Skill_Level", "Bonus_Experience",
    "No_Materials_Consumed", "Crafting_Outcome",
}
# "_(Mechanics)" with or without its closing bracket - older cache entries were
# truncated at the "(" by the link scraper, current ones are well-formed.
MECH_RE = re.compile(r"_\(Mechanics\)?$")
# The three pages of an attribute/skill family share one subject: the bare
# concept, its calculation page, and its item index.
_FAM_RE = re.compile(r"(_\(Mechanics\)?|_Attribute_Items|_Items)$")


def family_key(slug):
    """Collapse a page onto the subject it is about.

    'X', 'X_(Mechanics)' and 'X_Attribute_Items' are one attribute; and a
    'Gear:X/Variant' set or a 'Guide:X' walkthrough is about X too, so it can
    borrow X's artwork instead of rendering as a bare glyph.
    """
    s = urllib.parse.unquote(slug)
    for pre in ("Gear:", "Guide:"):
        if s.startswith(pre):
            s = s[len(pre):].split("/", 1)[0]
            break
    return _FAM_RE.sub("", s)
# Core rules and progression pages.
SYS_PAGES = {
    "Attributes", "Character_Level", "Skill_Experience", "Skill_Level",
    "Skill_Training", "Core_Mechanics", "Inventory", "Toolbelt", "Abilities",
    "Achievements", "Pets", "Pet_Eggs", "Chests", "Services", "Recipes",
    "Upgraded_Equipment", "Perfect_Items", "Overencumbered", "Overprepared",
    "Saved_steps", "Fine_Material", "Activity", "Equipment", "Arenum",
    "Map_of_Arenum", "Skills", "Activities", "Items", "Locations",
    "Movement_Activities", "Spelunking", "Traveling",
}
SYS_GROUPS = {
    "Attributes": {"Attributes"} | ATTRIBUTES,
    "Progression": {"Character_Level", "Skill_Experience", "Skill_Level",
                    "Skill_Training", "Abilities", "Achievements"},
    "Inventory & Gear": {"Inventory", "Toolbelt", "Equipment",
                         "Upgraded_Equipment", "Perfect_Items",
                         "Overencumbered", "Overprepared"},
    "Rewards": {"Chests", "Pets", "Pet_Eggs", "Recipes", "Services",
                "Fine_Material"},
}
# Section index pages ("Skills", "Items"...) - kept, but flagged as indexes so
# the UI can push them below real content.
INDEX_PAGES = {"Skills", "Activities", "Items", "Locations", "Equipment",
               "Materials", "Consumables", "Gear", "Tools", "Keywords",
               "Collectibles", "Cosmetics", "Gems", "Crafted_Items",
               "Crafted_items", "Food", "Trinkets", "Rings", "Weapons",
               "Logs", "Ores", "Bars", "Lore_Items", "Loot_Items",
               "Fishing_Chests", "Bird_Nests", "Berries", "Recipes",
               "Map_of_Arenum", "Arenum"}

GUIDE_PAGES = {"Skill_Training", "Money_Making", "Tips_and_Tricks"}

# Item subtype detection, checked in order. (slug-suffix hints, cat keywords)
ITEM_SUBS = [
    ("Index",        (), ()),  # handled separately
    ("Tools",        ("pickaxe", "hatchet", "hammer", "sickle", "pan", "rod",
                      "shovel", "bellows", "cartpack", "fishing_line",
                      "toolbelt", "kicksled", "dynamite", "guidebook"),
                     ("tool",)),
    ("Food",         ("pie", "sandwich", "soup", "weave", "rolls", "beer",
                      "cooked_", "salmon", "shrimp", "carp", "cucumber",
                      "tomato", "honeycomb", "berries", "jellyfish", "squid"),
                     ("food", "cooked", "edible")),
    ("Consumables",  (), ("consumable", "potion", "drink")),
    # "^cape" is a token match, not a substring: a bare "cape" also matched
    # walkscape, landscape and escape, which filed the wiki's own main page
    # as a cosmetic. "^" still matches "cape_of_achiever" and "feather_cape".
    ("Cosmetics",    ("sunglasses", "sneakers", "^cape", "cool_", "teddy"),
                     ("cosmetic",)),
    ("Collectibles", ("memosphere", "tusk", "tear", "clam_shell", "feather",
                      "shell", "butterfly", "bauble", "horn_of"),
                     ("collectible", "lore item", "lore")),
    ("Gear",         ("ring", "trinket", "shield", "sword", "hat", "jacket",
                      "handwraps", "crown", "^cape", "boots", "armour",
                      "armor", "helm", "gloves", "belt", "amulet"),
                     ("gear", "equipment", "weapon", "armour", "armor",
                      "ring", "trinket", "jewellery", "jewelry", "clothing")),
    ("Materials",    ("_ore", "_bar", "_log", "logs", "_scrap", "scraps",
                      "stone", "root", "topaz", "hide", "wood", "gem"),
                     ("material", "resource", "ore", "bar", "log", "gem",
                      "fish", "raw")),
]

LOC_SUBS = [
    ("Regions", ("region", "kingdom", "empire", "duchy", "continent")),
    ("Cities",  ("city", "cities", "town", "settlement", "port", "village")),
    ("Areas",   ("area", "areas", "zone", "wilderness", "forest", "mountain")),
]

ACT_SUBS = [
    ("Gathering", ("woodcutting", "mining", "fishing", "foraging", "hunting",
                   "farming")),
    ("Crafting",  ("crafting", "smithing", "cooking", "carpentry", "tailoring",
                   "trinketry")),
    ("Movement",  ("agility", "traveling", "movement")),
]


_WORD_NEEDLE = {}


def _hit(needles, haystack):
    """Substring match, except a needle written "^x" must match x at a token
    boundary - the start of the slug or just after an underscore.

    Slugs are underscore-separated, so a bare substring silently matches inside
    longer words: "cape" hit walkscape, landscape and escape, which is how the
    wiki's own main page ended up filed as a cosmetic.
    """
    for n in needles:
        if n.startswith("^"):
            rx = _WORD_NEEDLE.get(n)
            if rx is None:
                rx = _WORD_NEEDLE[n] = re.compile(r"(?:^|_)" + re.escape(n[1:]))
            if rx.search(haystack):
                return True
        elif n in haystack:
            return True
    return False


def classify(slug, title, cats):
    """Return (section, subtype, tags). One primary home per page; anything
    else it also belongs to becomes a secondary tag."""
    # Slugs arrive percent-encoded (they come from cache filenames), but every
    # curated set below is written in decoded form ("Guide:Money_Making",
    # "Walkscape_Walkthrough:About"). Decode once here so those literals match -
    # otherwise the ":" pages silently fall through to the generic buckets.
    slug = urllib.parse.unquote(slug)
    lc = " | ".join(c.lower() for c in cats)
    sl = slug.lower()
    tags = []

    def has(*keys):
        return _hit(keys, lc)

    # -- Start Here ----------------------------------------------------
    if slug in START_PAGES:
        sub = "About the wiki" if slug in ABOUT_PAGES else "Getting started"
        return START, sub, tags

    # -- Guides --------------------------------------------------------
    if slug.startswith("Guide:") or slug.startswith("Gear:") \
            or slug in GUIDE_PAGES:
        return GUIDES, "Walkthroughs", tags

    # These run before the item rules on purpose. They identify a page by what
    # the wiki filed it as, and the item rules below match on much looser
    # signals - left later, they scattered buildings and changelogs across
    # Items and the Glossary catch-all depending on which weak signal hit first.
    cat_set = set(cats)

    # -- Release notes: "Versions/512" and friends are patch notes ------
    if slug.startswith("Versions/"):
        return START, "Release notes", tags

    # -- Equipment slots describe where gear goes, not the gear ---------
    if slug.endswith("_Slot"):
        return SYS, "Inventory & Gear", tags

    # -- Buildings are places you visit ---------------------------------
    if "Buildings" in cat_set or any(c.startswith("Building Type:") for c in cats):
        return LOCS, "Buildings", tags

    # -- Achievement pages. Matched exactly: an item whose category is
    #    "Achievement reward Keyword Items" is an item, not an achievement.
    if any(c == "Achievements" or c.endswith(" Achievements") for c in cats):
        return SYS, "Progression", tags

    # -- Faction standing and its reward tables -------------------------
    if "Faction Reputation" in cat_set:
        return SYS, "Rewards", tags

    # -- Chest loot tables ----------------------------------------------
    # "<Skill>_Chests" pages list what a chest drops. They were landing in five
    # different buckets on the strength of whatever their loot happened to be -
    # Carpentry_Chests was filed as Food - so pin them next to "Chests" itself.
    if slug.endswith("_Chests"):
        return SYS, "Rewards", tags

    # -- Crafting venues are places, not skills -------------------------
    if slug in FACILITY_PAGES:
        return LOCS, "Buildings", tags

    # -- "<Name>_Gear_Set" is a curated kit list, i.e. an index ---------
    if slug.endswith("_Gear_Set"):
        return ITEMS, "Index", tags

    # -- Glossary: keyword pages describe a term, not an item ----------
    if slug.endswith("_Keyword") or title.endswith("Keyword") \
            or slug in ("Keywords", "Glossary"):
        tags.append("Keyword")
        return GLOSS, "Item keywords" if slug.endswith("_Keyword") else \
            "Reference", tags

    # -- Attribute triples --------------------------------------------
    base = slug[:-6] if slug.endswith("_Items") else slug
    base = base[:-len("_Attribute")] if base.endswith("_Attribute") else base
    if slug.endswith("_Items") and (base in ATTRIBUTES or
                                    base in SKILL_PAGES or base == "Global"):
        # e.g. "Mining_Attribute_Items", "Work_Efficiency_Items" - these are
        # lists of gear, so they live with the gear but are marked as indexes.
        tags.append(base.replace("_", " "))
        return ITEMS, "Index", tags
    if slug in ATTRIBUTES or MECH_RE.sub("", slug) in ATTRIBUTES:
        return SYS, "Attributes", tags

    # -- Skills --------------------------------------------------------
    # SKILL_GROUPS is the complete list of trainable skills, so membership is
    # the whole test. There used to be a `has("skills")` fallback here, but the
    # wiki tags anything skill-adjacent with that category, so it swept in the
    # crafting facilities (Forges, Kitchens, Sawmills, Workshops) and filed them
    # as skills. Pages merely *about* skills fall through to the rules below,
    # which classify them on what they actually are.
    if slug in SKILL_PAGES:
        for group, members in SKILL_GROUPS.items():
            if slug in members:
                return SKILLS, group, tags

    # -- Game systems --------------------------------------------------
    if slug in SYS_PAGES:
        for group, members in SYS_GROUPS.items():
            if slug in members:
                if slug in INDEX_PAGES:
                    tags.append("Index")
                return SYS, group, tags
        if slug in INDEX_PAGES:
            tags.append("Index")
        return SYS, "Core rules", tags

    # -- Activities ----------------------------------------------------
    if has("activit") or sl.startswith(("cut_", "mine_", "find_", "venture_",
                                        "hut_", "catch_")):
        for group, keys in ACT_SUBS:
            if _hit(keys, lc) or _hit(keys, sl):
                return ACTS, group, tags
        return ACTS, "Other", tags

    # -- Locations -----------------------------------------------------
    if has("location", "cities", "areas", "region", "arenum", "place"):
        for group, keys in LOC_SUBS:
            if _hit(keys, lc):
                return LOCS, group, tags
        return LOCS, "Areas", tags

    # -- Items ---------------------------------------------------------
    if slug in INDEX_PAGES or slug.endswith("_Items"):
        tags.append("Index")
        return ITEMS, "Index", tags
    if has("item", "material", "consumable", "equipment", "food", "tool",
           "trinket", "ring", "gear", "weapon", "armor", "armour",
           "resource", "log", "ore", "fish", "bar", "gem", "cosmetic",
           "collectible", "chest"):
        for name, slug_keys, cat_keys in ITEM_SUBS[1:]:
            if _hit(cat_keys, lc) or _hit(slug_keys, sl):
                return ITEMS, name, tags
        return ITEMS, "Materials", tags

    # -- last resort: shape of the slug, not a catch-all bucket --------
    for name, slug_keys, cat_keys in ITEM_SUBS[1:]:
        if _hit(slug_keys, sl):
            return ITEMS, name, tags
    if has("mechanic", "gameplay", "system"):
        return SYS, "Core rules", tags
    return GLOSS, "Reference", tags


# tags the wiki uses for its own bookkeeping - never show these
TAG_BLOCK = re.compile(
    r"^(pages |articles |all |stub|candidates|wiki |maintenance|"
    r"needs |translat|disambig)", re.I)

def clean_tags(cats, extra):
    out = list(extra)
    for c in cats:
        if TAG_BLOCK.match(c):
            continue
        if c.lower() in ("categories", "browse", "main page"):
            continue
        if c not in out:
            out.append(c)
    return out[:6]


SECTION_ORDER = [START, SKILLS, ACTS, ITEMS, LOCS, SYS, GUIDES, GLOSS]
SUB_ORDER = {
    START: ["Getting started", "About the wiki", "Release notes"],
    SKILLS: ["Gathering", "Artisan", "Support"],
    ACTS: ["Gathering", "Crafting", "Movement", "Other"],
    ITEMS: ["Tools", "Gear", "Materials", "Consumables", "Food",
            "Collectibles", "Cosmetics", "Index"],
    LOCS: ["Regions", "Cities", "Areas", "Buildings"],
    SYS: ["Attributes", "Progression", "Inventory & Gear", "Rewards",
          "Core rules"],
    GUIDES: ["Walkthroughs"],
    GLOSS: ["Reference", "Item keywords"],
}

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
        raw["Home"] = open("data/home.md", encoding="utf-8",
                           errors="ignore").read()

    have = set(urllib.parse.unquote(s) for s in raw.keys()) - set(REDIRECTS)

    LANG = re.compile(r"[-./](de|fr|es|it|pt|pl|nl|ru|zh|ja|ko|tr|cs|fi|sv|da"
                      r"|no|uk|hu|ro|el|he|ar|th|id|vi|hr|sk|sl|et|lt|lv)$",
                      re.I)
    pages = {}
    # Every drop is recorded by reason. A page vanishing between the cache and
    # the build used to be invisible, which is how 16 wrongly-addressed pages
    # sat broken in the cache unnoticed: the scraper truncated their URLs, the
    # wiki served a "no text in this page" placeholder, and the malformed-slug
    # rule below quietly swallowed the evidence.
    dropped = {"language variant": [], "malformed slug": [],
               "wiki placeholder": [], "empty after cleaning": [],
               "redirect": []}
    for slug, text in raw.items():
        title = slug_to_title(slug)
        if slug != "Home":
            # drop non-English language variants (e.g. Materials.de)
            if LANG.search(slug):
                dropped["language variant"].append(slug)
                continue
            # The page is a redirect; its content belongs to the target and is
            # built from the target's own cache entry. fetch_pages.py stops
            # caching these, but a CI run restores .firecrawl from cache, so an
            # older duplicate can still be sitting there.
            if urllib.parse.unquote(slug) in REDIRECTS:
                dropped["redirect"].append(slug)
                continue
            # a slug that opens a bracket it never closes means the link
            # scraper truncated the URL - the page was crawled at a bad address
            if "(" in title and ")" not in title:
                dropped["malformed slug"].append(slug)
                continue
            # the page does not exist on the wiki; we cached its placeholder
            if "There is currently no text in this page" in text:
                dropped["wiki placeholder"].append(slug)
                continue
        cats = extract_categories(text)
        body_md = clean_markdown(text, title)
        if len(body_md) < 15:
            dropped["empty after cleaning"].append(slug)
            continue
        # Page keys are the DECODED title. Cache filenames are inconsistently
        # encoded ("Guide%3AMoney_Making" but "Work_Efficiency_(Mechanics)"),
        # and the app's router decodes the hash before looking a page up - so
        # an encoded key is simply unreachable by any link rewritten from the
        # wiki. Normalise here, and re-encode when building the source URL.
        key = urllib.parse.unquote(slug)
        if slug == "Home":
            source_url = ("https://wiki.walkscape.app/wiki/"
                          "WalkScape:_Grind_by_walking!")
        else:
            # ":" is safe in a wiki path and keeps the canonical form readable
            source_url = ("https://wiki.walkscape.app/wiki/"
                          + urllib.parse.quote(key, safe="/:"))
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
        if slug != "Home":
            body_html = cap_html(body_html, source_url)

        section, sub, extra = classify(slug, title, cats)
        # first referenced image doubles as the entry's icon in lists/cards
        first_img = re.search(r'data-i="([^"]+)"', body_html)
        # plain text for search + excerpt
        plain = re.sub(r"<[^>]+>", " ", body_html)
        plain = html.unescape(re.sub(r"\s+", " ", plain)).strip()
        pages[key] = {
            "title": title,
            "section": section,
            "sub": sub,
            "tags": clean_tags(cats, extra),
            "html": body_html,
            "text": plain[:280],
            "icon": first_img.group(1) if first_img else "",
            "url": source_url,
        }

    # --- icon inheritance within a page family --------------------------
    # An entry's icon is the first image on the page, but the conceptual pages
    # carry no artwork at all: "Work Efficiency", "Work Efficiency (Mechanics)"
    # and "Work Efficiency Items" describe one attribute, and only the item
    # index has a picture. Let the family share it so these entries stop
    # rendering as bare text in the palette and grid views.
    families = {}
    for slug, p in pages.items():
        families.setdefault(family_key(slug), []).append(p)
    for members in families.values():
        donors = [q for q in members if q["icon"]]
        if not donors or len(donors) == len(members):
            continue
        # prefer the item index as donor: it is the page with real gear art
        donors.sort(key=lambda q: (q["sub"] != "Index", q["title"]))
        for q in members:
            if not q["icon"]:
                q["icon"] = donors[0]["icon"]

    # --- related entries: pages this page links to, that link back or share
    #     a section. Cheap, deterministic, no NLP.
    link_re = re.compile(r'href="#/([^"]+)"')
    outgoing = {}
    for slug, p in pages.items():
        seen = []
        for m in link_re.findall(p["html"]):
            t = urllib.parse.unquote(m)
            if t != slug and t in pages and t not in seen:
                seen.append(t)
        outgoing[slug] = seen
    for slug, p in pages.items():
        same = [s for s in outgoing[slug] if pages[s]["section"] == p["section"]]
        other = [s for s in outgoing[slug] if s not in same]
        p["related"] = (same + other)[:6]

    # build category index
    sections, subs = {}, {}
    for slug, p in pages.items():
        sections.setdefault(p["section"], []).append(slug)
        subs.setdefault(p["section"], set()).add(p["sub"])
    for s in sections:
        sections[s].sort(key=lambda x: pages[x]["title"].lower())
    subs = {s: [x for x in SUB_ORDER.get(s, []) if x in subs[s]] +
               sorted(v for v in subs[s] if v not in SUB_ORDER.get(s, []))
            for s in subs}

    order = [s for s in SECTION_ORDER if s in sections] + \
            [s for s in sections if s not in SECTION_ORDER]

    data = {"pages": pages, "sections": sections, "subs": subs,
            "order": order, "count": len(pages), "home": "Home"}
    os.makedirs("data", exist_ok=True)
    with open("data/wiki_data.json", "w", encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False)
    with open("data/img_map.json", "w", encoding="utf-8") as out:
        json.dump(IMG_MAP, out)
    print(f"Pages: {len(pages)} | images referenced: {len(IMG_MAP)}")
    for s in order:
        line = ", ".join("%s %d" % (k, sum(1 for x in sections[s]
                                           if pages[x]["sub"] == k))
                         for k in subs[s])
        print(f"  {s}: {len(sections[s])}  ({line})")

    total_dropped = sum(len(v) for v in dropped.values())
    print(f"\nCached files: {len(raw)} | built: {len(pages)} | "
          f"dropped: {total_dropped}")
    for reason, slugs in dropped.items():
        if not slugs:
            continue
        # language variants and redirects are expected and numerous; the rest
        # are not, so name them - a page dropped for any other reason wants a
        # human look.
        if reason in ("language variant", "redirect"):
            print(f"  {reason}: {len(slugs)}")
        else:
            print(f"  {reason}: {len(slugs)}  -> "
                  + ", ".join(sorted(slugs)[:12])
                  + (" ..." if len(slugs) > 12 else ""))


if __name__ == "__main__":
    main()
