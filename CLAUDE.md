# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## What this is

A static, single-file companion wiki for [WalkScape](https://walkscape.app), built by
crawling the official community wiki, reclassifying it into a phone-friendly information
architecture, and rendering everything — markup, CSS, JS, page content and images — into one
self-contained `index.html`. No server, no runtime dependencies, no network at view time.

Published at [mitsu03.github.io/walkscape-wiki](https://mitsu03.github.io/walkscape-wiki/)
via GitHub Pages, straight off the default branch. There is no CI: **committing a rebuilt
`index.html` to `main` is the deploy.**

## The build pipeline

```
firecrawl crawl                -> .firecrawl/*.md          (gitignored scratch cache)
python build_urls.py           -> data/master_urls.txt      (curated crawl target list)
bash   scrape_missing.sh       -> .firecrawl/*.md           (fills gaps, throttled)
python build_data.py           -> data/wiki_data.json + data/img_map.json
python build_images.py         -> data/images.json          (compressed data-URIs)
python build_site.py           -> index.html                (the deliverable)
```

Typical loop when only the *interface* changes:

```bash
python3 build_site.py     # stdlib only — works from committed data, ~10.5 MB / 259 pages
```

Only re-crawl when the game content itself has changed. `build_data.py` prints its
classification counts per section — read that output to sanity-check the buckets after a
re-crawl.

### Dependencies

| Script | Needs |
|---|---|
| `build_site.py` | stdlib only (`json`, `os`) |
| `build_urls.py` | stdlib only |
| `build_data.py` | `markdown` |
| `build_images.py` | `requests`, `Pillow` |
| crawling | the `firecrawl` CLI |

There is no `requirements.txt`, no virtualenv, no lockfile. Install what you need ad hoc.
A fresh container generally has `requests` but **not** `markdown` or `Pillow`, and the
`.firecrawl/` cache is gitignored — so out of the box only `build_site.py` can run. That is
enough for any UI work, since `data/wiki_data.json` and `data/images.json` are committed.

## Layout

```
index.html          GENERATED — do not hand-edit
build_data.py       crawl cache -> cleaned, classified page data
build_images.py     referenced images -> compressed data-URIs
build_site.py       data -> index.html; the ENTIRE UI lives in here
build_urls.py       sitemap + link scrape -> curated URL list
scrape_missing.sh   re-scrape only pages missing from the cache, 8 at a time, 12 s apart
data/
  wiki_data.json    the page payload (~4.4 MB)
  images.json       image data-URIs (~6.2 MB)
  img_map.json      image id -> source URL
  master_urls.txt   curated crawl targets
  urls.txt          sitemap seed
  home.md           the home page, kept apart (its title contains ':')
```

## Rules that matter

**`index.html` is a build artifact.** It is overwritten wholesale on every build and is
committed only so GitHub Pages can serve it. Never edit it directly — change `build_site.py`
and rebuild. A UI-change commit should touch `build_site.py` **and** `index.html` together,
and their diffs will be near-identical line counts.

**`build_site.py` is the source of truth for the interface.** Nearly all of its 1600+ lines
are one raw string, `TEMPLATE`, holding the full document. The only Python logic around it:
load `data/wiki_data.json`, merge in `data/images.json` (tolerating its absence), compute the
section order, serialize to compact JSON, and substitute it for the `__DATA__` placeholder.
Because the payload is injected by plain string replacement, nothing in `TEMPLATE` may contain
the literal `__DATA__`, and the template is a raw string (`r"""…"""`) so backslashes in the
CSS/JS survive.

**`build_data.py` owns the information architecture.** `classify()` returns exactly one
`(section, subtype, tags)` per page — one primary home, everything else demoted to a secondary
tag. The eight sections are Start Here, Skills, Activities, Items & Equipment, Locations,
Game Systems, Guides, Glossary. The rules are explicit sets and ordered keyword lists
(`START_PAGES`, `SKILL_GROUPS`, `ATTRIBUTES`, `SYS_GROUPS`, `ITEM_SUBS`, `LOC_SUBS`,
`ACT_SUBS`) evaluated top to bottom — **order is significant**, since the first match wins.
`README.md` documents the intended buckets and the notable judgement calls (attribute triples,
`*_Keyword` pages, index pages sorted last). Change the rules there, not downstream in the UI.

## Conventions

### Python

Terse, script-style, stdlib-first. Multiple imports per line (`import re, glob, os`),
module-level constants in caps, a `main()` guarded by `if __name__ == "__main__"` in the two
larger scripts and straight-line top-level code in the smaller ones. Regexes are compiled at
module level. Every script prints a one-line summary of what it produced — keep that habit,
it is the only progress feedback there is.

Budgets and caps are tuned constants; treat them as deliberate:

- `HTML_CAP = 46000` — per-page rendered HTML cap in `build_data.py`
- `RASTER_MAX = 128`, `WEBP_Q = 72`, `SVG_MAX_BYTES = 22000`, `RASTER_MAX_BYTES = 14000`,
  `TOTAL_BUDGET = 6_200_000` — image pipeline limits in `build_images.py`

Raising the image budget directly inflates `index.html`, which every visitor downloads in full.

### Front-end (inside `TEMPLATE`)

Vanilla ES5-flavoured JS — no framework, no bundler, no `let`/arrow functions in the shipped
code, no external requests of any kind (that constraint is the point of the project). Sections
are marked with `/* ============ name ============ */` banner comments in both the CSS and the
JS; keep new code inside the matching banner.

- **Routing** is hash-based: `#/Slug` for an article, `#/c/Section` for a category page,
  `#Anchor` for in-page scroll, `#/browse/X` redirects to `#/c/X` for backwards compatibility.
- **Theming** is `data-theme="light|dark"` on the root, persisted in `localStorage` under
  `ws-theme` (`ws-side` for sidebar collapse), defaulting to `prefers-color-scheme`.
- **Table handling** is the most intricate part of the UI. `enhance()` runs the chain:
  `cleanTable` → `stripEmptyCols` → `foldIconColumn` → `infobox` (padded key/value tables
  become titled cards) → `groupRecipeRows` / `sortableRecipe` (recipe tables group by output
  product, with clickable headers to re-sort by level or restore the grouped view). The narrow-
  screen card view must stay in sync with whatever the table view does.
- Escape anything derived from page data with `esc()` / `attr()` before inserting it as HTML.

## Verifying a change

`python3 build_site.py` is deterministic: with the committed data unchanged it reproduces the
existing `index.html` byte for byte, so `git status` staying clean is a valid check that you
changed nothing. After a UI edit, rebuild and open `index.html` directly in a browser
(`file://` works — that is the whole design) and exercise: the command palette (`/` or
`Ctrl`/`Cmd`+`K`), a category page's filters and layout toggle, an article's table of contents
and tables, both themes, and a narrow viewport for the card view.

There are no tests and no linter.

## Content and attribution

Content is derived from the community wiki at `wiki.walkscape.app` and reorganized; game
content remains © the WalkScape team and wiki contributors. This is an unofficial personal
companion tool. Every page keeps a `url` field pointing back at its source, and articles that
were truncated by `HTML_CAP` link out to the original — preserve that attribution path.

Be considerate when re-crawling: `scrape_missing.sh` deliberately batches 8 URLs and sleeps
12 s between batches. Do not remove that throttle.
