# WalkScape Companion Wiki

A cleaner, faster reference for [WalkScape](https://walkscape.app) — the walk-to-play MMORPG.
Built because the official [wiki](https://wiki.walkscape.app) is comprehensive but hard to browse
on a phone, mid-walk.

**Live site:** [mitsu03.github.io/walkscape-wiki](https://mitsu03.github.io/walkscape-wiki/)

## What this is

A single-file, self-contained web app (`index.html`) — no server, no network, no dependencies:

- **Command palette search** (`/` or `Ctrl`/`Cmd`+`K`) with results grouped by category
- **Eight categories**: Start Here, Skills, Activities, Items & Equipment, Locations,
  Game Systems, Guides, Glossary
- **Category pages** with in-category filtering, subtype chips, sort and list/grid layouts
- **Articles** with breadcrumbs, an auto-generated table of contents, copyable heading
  anchors and related entries
- **Tables** with sticky headers, a sticky first column, scroll affordances, and a card
  view on narrow screens
- Light and dark themes, full keyboard navigation, works offline

Just open `index.html` in any browser.

## Structure

```
index.html        the companion app (open this) — generated, do not hand-edit
build_data.py     crawl -> data/wiki_data.json (cleaning + classification)
build_images.py   image refs -> data/images.json (compressed data URIs)
                  + data/img_meta.json (which ids are pixel art / share bytes)
build_site.py     data -> index.html (the entire UI lives here)
build_urls.py     cached pages -> data/master_urls.txt (link discovery)
data/             source content crawled from the official wiki
.github/          scheduled content refresh (see "Keeping content fresh")
```

`build_site.py` is the source of truth for the interface. `index.html` is a build
artifact and is overwritten on every build.

## Building

```bash
# 1. crawl (only when refreshing content)
firecrawl crawl "https://wiki.walkscape.app" --limit 200 --include-paths "/wiki/" \
  --wait -o data/crawl.json          # unpacked into .firecrawl/*.md

# 2. clean, classify, index
python build_data.py                 # -> data/wiki_data.json + data/img_map.json

# 3. fetch and compress the images referenced above (optional but recommended)
python build_images.py               # -> data/images.json + data/img_meta.json

# 4. render the app
python build_site.py                 # -> index.html
```

`build_data.py` prints the resulting classification, e.g.

```
  Start Here: 7  (Getting started 6, About the wiki 1)
  Skills: 16  (Gathering 6, Artisan 7, Support 3)
  Items & Equipment: 107  (Tools 13, Gear 9, Materials 15, ...)
```

Use that output to sanity-check the buckets after a re-crawl.

It then reports what it *discarded*, grouped by reason:

```
Cached files: 274 | built: 273 | dropped: 1
  language variant: 1
```

Anything dropped for a reason other than `language variant` is named individually
and wants a look. A page that was crawled at a bad address arrives as a MediaWiki
"There is currently no text in this page" placeholder, and shows up here as
`wiki placeholder` rather than disappearing quietly.

## Information architecture

Every page has exactly one **section** and one **subtype**; anything else it belongs to
becomes a secondary tag. The rules live in `classify()` in `build_data.py`:

| Section | Contains | Subtypes |
| --- | --- | --- |
| Start Here | Tutorial, FAQs, tips, troubleshooting, wiki meta | Getting started, About the wiki |
| Skills | the trainable skills | Gathering, Artisan, Support |
| Activities | things a character can be set to do | Gathering, Crafting, Movement, Other |
| Items & Equipment | every item page, plus item index pages | Tools, Gear, Materials, Consumables, Food, Collectibles, Cosmetics, Index |
| Locations | regions, cities, areas | Regions, Areas |
| Game Systems | attributes, progression, inventory, rules | Attributes, Progression, Inventory & Gear, Rewards, Core rules |
| Guides | goal-oriented walkthroughs | Walkthroughs |
| Glossary | item keywords and wiki terms | Reference, Item keywords |

Notable calls:

- The `X` / `X_(Mechanics)` / `X_Items` triples (Work Efficiency, Item Finding, Double
  Action…) are **attributes**: the bare page and its `_(Mechanics)` calculation page both
  go to Game Systems, the `_Items` page is an item index under Items & Equipment. The three
  share one icon, since only the item index carries artwork.
- `Cities` is defined in `LOC_SUBS` but currently resolves to nothing: the wiki files its
  ports and harbours as plain locations, so every settlement lands in `Areas`. The rule is
  kept for when the wiki starts distinguishing them.
- `*_Keyword` pages describe a term, not an item, so they live in the Glossary.
- Index pages (`Skills`, `Items`, `Materials`…) are preserved but tagged `Index` and sorted
  last, so real content wins.
- Wiki bookkeeping categories ("Pages That Automatically Update", stubs, translations) are
  filtered out of the visible tags.

## Source & credits

Content is derived from the community WalkScape wiki (wiki.walkscape.app), reorganized for
easier navigation. All game content © the WalkScape team / wiki contributors. This is an
unofficial personal companion tool.

Source code: [github.com/Mitsu03/walkscape-wiki](https://github.com/Mitsu03/walkscape-wiki)
