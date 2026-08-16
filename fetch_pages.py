#!/usr/bin/env python
"""Fetch wiki pages straight from the MediaWiki API into the .firecrawl cache.

This is the no-credit path.  The wiki is server-rendered MediaWiki, so its
`action=parse` endpoint hands back the finished content HTML and the category
list - no crawler service, no browser, no API key.  Output is written in the
same shape the previous crawler produced, so `build_data.py` consumes it
unchanged:

    # <title>
    <body markdown, absolute URLs>
    Retrieved from "<canonical url>"
    ## Categories
    - [<cat>](https://wiki.walkscape.app/wiki/Category:<cat>)

Usage:
    python fetch_pages.py                 # fetch everything missing from cache
    python fetch_pages.py --limit 20      # stop after 20 pages
    python fetch_pages.py --refresh       # re-fetch pages already cached
    python fetch_pages.py --list          # show what would be fetched, fetch nothing
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup
from markdownify import MarkdownConverter

BASE = "https://wiki.walkscape.app"
API = BASE + "/api.php"
CACHE = ".firecrawl"
PREFIX = "wiki.walkscape.app-wiki-"

# Identify the bot and give a contact-ish string: standard MediaWiki etiquette.
UA = {"User-Agent": "walkscape-wiki-companion/1.0 "
                    "(offline reference builder; contact via repo issues)"}

# Chrome the API includes that is navigation, not content.  Selectors rather
# than regexes, because these are structural, not textual.
DROP_SELECTORS = [
    ".mw-editsection",          # [edit] links
    ".mw-pt-languages",         # translation switcher
    ".navigation-not-searchable",
    "#toc", ".toc", ".toccolours",
    ".printfooter",
    ".mw-empty-elt",
    "style", "script", "link", "meta",
    ".mw-indicators",
    ".noprint",
]

PAUSE = 0.5      # seconds between requests - be a good citizen
RETRIES = 3


def slug_to_filename(slug):
    """Mirror the cache's existing naming: literal parens, everything unsafe
    for a Windows filename percent-encoded (notably ':' -> %3A)."""
    return PREFIX + urllib.parse.quote(slug, safe="_-.()!,~") + ".md"


def absolutise(soup):
    for tag, attr in (("a", "href"), ("img", "src")):
        for el in soup.find_all(tag):
            v = el.get(attr)
            if not v:
                continue
            if v.startswith("//"):
                el[attr] = "https:" + v
            elif v.startswith("/"):
                el[attr] = BASE + v
    # srcset would smuggle in relative thumb URLs the image step can't resolve
    for el in soup.find_all("img"):
        if el.get("srcset"):
            del el["srcset"]
    return soup


# markdownify discards an <img> that sits in an inline context, emitting only
# its alt text.  Almost every wiki image is wrapped in a <a> file link, and the
# infobox portrait is the page's icon, so losing those would strip the art from
# the entire item catalogue.  Name the wrappers we want images kept inside.
KEEP_IMAGES_IN = ["a", "b", "strong", "i", "em", "big", "small", "span",
                  "td", "th", "li", "p", "div", "center"]


class WikiConverter(MarkdownConverter):
    """Keep <br> inside table cells - the infobox rows rely on it."""

    def convert_br(self, el, text, *args, **kwargs):
        return "<br>"


def api_get(params):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(API + "?" + qs, headers=UA)
    last = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except Exception as e:                       # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def fetch_page(slug):
    """Return (markdown_document, None) or (None, error_string)."""
    data = api_get({
        "action": "parse",
        "page": slug,
        "prop": "text|categories|displaytitle",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
    })
    if "error" in data:
        return None, data["error"].get("code", "api-error")
    parse = data["parse"]
    title = parse.get("title", slug.replace("_", " "))

    soup = BeautifulSoup(parse["text"], "html.parser")
    for sel in DROP_SELECTORS:
        for el in soup.select(sel):
            el.decompose()
    absolutise(soup)

    body = WikiConverter(heading_style="ATX", bullets="-",
                         keep_inline_images_in=KEEP_IMAGES_IN).convert_soup(soup)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    cats = [c["category"] for c in parse.get("categories", [])
            if not c.get("hidden")]
    canonical = BASE + "/wiki/" + urllib.parse.quote(slug, safe="/:")

    out = ["# %s\n" % title, body, "",
           'Retrieved from "%s"' % canonical, ""]
    if cats:
        out.append("## Categories\n")
        for c in cats:
            out.append("- [%s](%s/wiki/Category:%s)"
                       % (c.replace("_", " "), BASE, c))
    return "\n".join(out) + "\n", None


def cached_slugs():
    have = set()
    for name in os.listdir(CACHE):
        if name.startswith(PREFIX) and name.endswith(".md"):
            have.add(urllib.parse.unquote(name[len(PREFIX):-3]))
    return have


def wanted_slugs():
    urls = [l.strip() for l in open("data/master_urls.txt", encoding="utf-8")
            if l.strip()]
    return [urllib.parse.unquote(u.split("/wiki/", 1)[1]) for u in urls]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refresh", action="store_true",
                    help="re-fetch pages that are already cached")
    ap.add_argument("--list", action="store_true",
                    help="print the work list and exit")
    ap.add_argument("--pause", type=float, default=PAUSE)
    args = ap.parse_args()

    os.makedirs(CACHE, exist_ok=True)
    have = set() if args.refresh else cached_slugs()
    todo = [s for s in wanted_slugs() if s not in have]
    if args.limit:
        todo = todo[:args.limit]

    print("cached: %d | manifest: %d | to fetch: %d"
          % (len(cached_slugs()), len(wanted_slugs()), len(todo)))
    if args.list:
        for s in todo:
            print("   ", s)
        return 0
    if not todo:
        print("nothing to do")
        return 0

    ok = failed = 0
    errors = []
    for i, slug in enumerate(todo, 1):
        try:
            doc, err = fetch_page(slug)
        except Exception as e:                       # noqa: BLE001
            doc, err = None, "%s: %s" % (type(e).__name__, e)
        if doc is None:
            failed += 1
            errors.append((slug, err))
        else:
            with open(os.path.join(CACHE, slug_to_filename(slug)),
                      "w", encoding="utf-8") as f:
                f.write(doc)
            ok += 1
        if i % 25 == 0 or i == len(todo):
            print("  [%d/%d] ok %d, failed %d" % (i, len(todo), ok, failed))
        time.sleep(args.pause)

    print("done: %d fetched, %d failed" % (ok, failed))
    if errors:
        print("failures:")
        for slug, err in errors[:25]:
            print("   %-45s %s" % (slug, err))
    return 0


if __name__ == "__main__":
    sys.exit(main())
