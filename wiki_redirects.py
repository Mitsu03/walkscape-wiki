"""Wiki title aliases shared by the data and site build steps."""
import json, urllib.parse


# These old titles were deleted after their articles moved, so the wiki no
# longer reports them as redirects. Keep them across generated data refreshes.
LEGACY_ALIASES = {
    "Bar_Keyword": "Bar_(Keyword)",
    "Crafting_tool_Keyword": "Crafting_tool_(Keyword)",
    "Trinket_Keyword": "Trinket_(Keyword)",
    "Weapon_Keyword": "Weapon_(Keyword)",
    "Item_Finding_Items": "Roll_Special_Table_Items",
}


def load_redirects():
    try:
        with open("data/redirects.json", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return {}
    flat = {}
    for src in raw:
        # Follow chains: MediaWiki does not resolve a double redirect itself.
        seen, tgt = {src}, raw[src]
        while tgt in raw and tgt not in seen:
            seen.add(tgt)
            tgt = raw[tgt]
        if tgt != src:
            flat[urllib.parse.unquote(src)] = urllib.parse.unquote(tgt)
    return flat


def available_redirects(pages):
    """Only route missing titles to articles bundled in this build."""
    aliases = load_redirects()
    aliases.update(LEGACY_ALIASES)
    return {src: dst for src, dst in aliases.items()
            if src not in pages and dst in pages}
