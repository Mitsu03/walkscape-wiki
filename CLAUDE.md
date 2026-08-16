# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## What this is

A static, single-file companion wiki for [WalkScape](https://walkscape.app), built by
fetching the official community wiki, reclassifying it into a phone-friendly information
architecture, and rendering everything — markup, CSS, JS, page content and images — into one
self-contained `index.html`. No server, no runtime dependencies, no network at view time.

Published at [mitsu03.github.io/walkscape-wiki](https://mitsu03.github.io/walkscape-wiki/)
via GitHub Pages. **`index.html` is not committed.** `.github/workflows/deploy-pages.yml`
renders it from the committed `data/` on every push to `main` that touches `data/**` or
`build_site.py`, and publishes it as a Pages artifact — so **merging a data change is the
deploy**. Pages is configured with `build_type: workflow`; it no longer serves the branch.

Locally, `python build_site.py` still writes `index.html` into the working tree, which is
gitignored. Open it directly — that is unchanged and still the whole point.

## The build pipeline

```
python fetch_pages.py          -> .firecrawl/*.md          (gitignored scratch cache)
                               +  data/redirects.json     (titles the wiki resolves elsewhere)
python build_urls.py           -> data/master_urls.txt      (link discovery)
python build_data.py           -> data/wiki_data.json + data/img_map.json
python build_images.py         -> data/images.json + data/img_meta.json
python build_site.py           -> index.html                (the deliverable)
```

Typical loop when only the *interface* changes:

```bash
python build_site.py      # stdlib only — works from committed data, ~16.9 MB / 686 pages
```

Only re-fetch when the game content itself has changed. `build_data.py` prints its
classification counts per section, then every page it *discarded* grouped by reason — read
both after a re-fetch. Anything dropped for a reason other than `language variant` wants a
look.

### Content comes from the wiki's own API — there is no crawler

`fetch_pages.py` reads MediaWiki's public `action=parse` endpoint directly. No API key, no
crawler service, no per-page cost, and no browser: the wiki is server-rendered, so nothing
here needs JavaScript. Re-fetching the whole 690-page manifest is free and takes ~12 min at
the default 0.5 s politeness pause.

Do not reintroduce a scraping service. This project used one, and it cost money to
reproduce content the source hands out for free — and worse, its output needed a whole
layer of chrome-stripping that the API makes unnecessary.

`fetch_pages.py --refresh` re-fetches pages already cached; without it, only missing pages
are fetched. `--list` shows the work list, `--limit N` caps it.

### Dependencies

| Script | Needs |
|---|---|
| `build_site.py` | stdlib only (`json`, `os`) |
| `build_urls.py` | stdlib only |
| `build_data.py` | `markdown` |
| `build_images.py` | `Pillow` |
| `fetch_pages.py` | `markdownify`, `beautifulsoup4` |

`pip install -r requirements.txt` covers all of it. The `.firecrawl/` cache is gitignored,
so out of the box only `build_site.py` can run — which is enough for any UI work, since
`data/wiki_data.json` and `data/images.json` are committed.

**Encoding gotcha:** cache filenames keep the page title percent-encoded, so `classify()`
decodes the slug before matching anything, and page keys are stored decoded. Namespaced pages
arrive as `Guide%3AMoney_Making` and would otherwise miss the `Guide:` prefix entirely — this
one convention mismatch previously produced four separate-looking bugs, including dead links
that shipped. When a page key and a URL disagree, suspect this first.

**Needle gotcha:** `_hit()` matches substrings, which silently match inside longer words —
`"cape"` also hit walkscape, landscape and escape. Write `"^cape"` for a token-boundary match.

**Redirect gotcha:** the API follows redirects, so asking for a redirect returns the *target's*
article — successfully. Nothing errors, the page count only goes up, and the corpus quietly
gains the same article under two titles (`Forges` held all of Smithing; `Gear` rendered a
literal "(Redirected from Gear)" line). `fetch_pages.py` compares the resolved title against
the requested one and records the mismatch in `data/redirects.json` instead of caching it;
`build_data.py` skips those slugs and rewrites inbound links to the target. Both steps are
needed — the CI job restores `.firecrawl/` from cache, so a duplicate fetched before the fix
would otherwise keep building.

**`fetch_pages.py` gotcha:** markdownify drops an `<img>` in an inline context and emits
only its alt text. Nearly every wiki image is wrapped in an `<a>` file link — including the
infobox portrait that becomes each page's icon — so `keep_inline_images_in` is load-bearing,
not a nicety. Removing it silently strips the art from the entire item catalogue.

## Layout

```
index.html          GENERATED, gitignored — rendered in CI at deploy time
fetch_pages.py      MediaWiki API -> .firecrawl/*.md page cache
build_data.py       page cache -> cleaned, classified page data
build_images.py     referenced images -> compressed data-URIs
build_site.py       data -> index.html; the ENTIRE UI lives in here
build_urls.py       sitemap + link scrape -> discovered URL list
data/
  wiki_data.json    the page payload (~14 MB)
  images.json       image data-URIs (~2.5 MB)
  img_meta.json     which ids are pixel art, and which share another's bytes
  img_map.json      image id -> source URL
  redirects.json    redirect slug -> canonical slug (never built as pages)
  master_urls.txt   discovered fetch targets (~690)
  urls.txt          sitemap seed
  home.md           the home page, kept apart (its title contains ':')
.github/            weekly refresh workflow; opens a PR, never pushes to main
```

## Rules that matter

**`index.html` is a build artifact and is not in the repository.** It is overwritten
wholesale on every build and gitignored; CI renders it at deploy time. Never edit it
directly — change `build_site.py` and rebuild. A UI-change commit therefore touches
`build_site.py` alone, and the deploy workflow picks the change up on merge.

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
same `index.html` byte for byte. `git status` can no longer show that — the file is
gitignored — so hash it across the change instead:

```bash
sha256sum index.html > /tmp/before && python build_site.py && sha256sum -c /tmp/before
```

After a UI edit, rebuild and open `index.html` directly in a browser
(`file://` works — that is the whole design) and exercise: the command palette (`/` or
`Ctrl`/`Cmd`+`K`), a category page's filters and layout toggle, an article's table of contents
and tables, both themes, and a narrow viewport for the card view.

There are no tests and no linter.

## Content and attribution

Content is derived from the community wiki at `wiki.walkscape.app` and reorganized; game
content remains © the WalkScape team and wiki contributors. This is an unofficial personal
companion tool. Every page keeps a `url` field pointing back at its source, and articles that
were truncated by `HTML_CAP` link out to the original — preserve that attribution path.

Be considerate when re-fetching: `fetch_pages.py` sleeps `--pause` seconds (default 0.5)
between requests and identifies itself in the User-Agent. Fetching is free now, which makes
politeness the *only* limit — do not remove that throttle or parallelise the fetch.
