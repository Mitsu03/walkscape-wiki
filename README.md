# WalkScape Companion Wiki

A cleaner, easier-to-navigate reference for [WalkScape](https://walkscape.app) — the walk-to-play MMORPG. Built because the official [wiki](https://wiki.walkscape.app) is comprehensive but hard to browse.

## What this is

A single-file, self-contained web app (`index.html`) with:
- 🔍 Instant search across all content
- 📂 Category browsing: Skills, Activities, Items, Locations, Keywords
- 📖 The getting-started walkthrough
- 📱 Works on phone and desktop, nothing to install

Just open `index.html` in any browser.

## Structure

- `index.html` — the companion wiki app (open this)
- `data/` — source content crawled from the official wiki (markdown/JSON)

## Source & credits

Content is derived from the official community WalkScape wiki (wiki.walkscape.app),
reorganized for easier navigation. All game content © the WalkScape team / wiki contributors.
This is an unofficial personal companion tool.

## Updating

Re-run the crawl with the [Firecrawl CLI](https://docs.firecrawl.dev/sdks/cli):

```bash
firecrawl crawl "https://wiki.walkscape.app" --limit 200 --include-paths "/wiki/" --wait -o data/crawl.json
```

Then rebuild `index.html` from the refreshed data.
