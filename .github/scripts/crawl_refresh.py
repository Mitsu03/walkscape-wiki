#!/usr/bin/env python3
"""Refresh the .firecrawl/ markdown cache from the live wiki.

CI entry point for .github/workflows/refresh-content.yml. This script does not
touch build_data.py / build_images.py / build_site.py -- it only makes sure
.firecrawl/ holds a current copy of every page listed in data/master_urls.txt,
plus any page newly linked from those pages, and that data/home.md is current.

Why it is shaped this way
-------------------------
* .firecrawl/ is gitignored, so a CI run has no cache of its own. The committed
  data/master_urls.txt IS the crawl manifest -- 278 explicit URLs -- so the
  refresh is a deterministic `firecrawl scrape` over that list rather than an
  open-ended `firecrawl crawl`. Cost per run is therefore predictable and
  roughly equal to the manifest size (~1 credit per page).
* New pages still get discovered: after the manifest is scraped, build_urls.py
  is re-run, which harvests wiki links out of the freshly scraped markdown and
  rewrites the manifest. Anything newly linked is then scraped in a follow-up
  round. That reuses the project's existing (and already correctly filtered)
  discovery logic instead of duplicating it here.
* The previous cache (restored by actions/cache) is moved aside before
  scraping, not scraped over. That guarantees every page is genuinely re-fetched
  regardless of any CLI-side write-skipping, while still leaving a fallback: any
  manifest page whose fresh scrape failed is restored from the old copy, so one
  flaky page cannot delete content from the site.
* Files are matched to URLs by percent-decoded key, never by literal filename.
  The Firecrawl CLI decodes some escapes into the filename (`%28` -> `(`) and
  leaves others alone (`%3A`, `%27`), and it does so differently on Windows and
  Linux. Comparing decoded keys makes the match stable across both, and lets us
  drop the duplicate that appears when a Windows-seeded cache meets a
  Linux-produced scrape.

Usage:
    python .github/scripts/crawl_refresh.py [--full-refresh] [--dry-run] ...
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

CACHE = Path(".firecrawl")
PREFIX = "wiki.walkscape.app-wiki-"
BASE = "https://wiki.walkscape.app/wiki/"

# The main page's title contains ':' and '!', which cannot be a filename on
# Windows, so the project keeps it apart as data/home.md and build_data.py loads
# it from there. On Linux the CLI *could* write it into .firecrawl/, which would
# render the home page twice, so it is always handled separately and evicted
# from the cache dir.
HOME_URL = BASE + "WalkScape:_Grind_by_walking!"
HOME_KEY = "WalkScape:_Grind_by_walking!"
HOME_DEST = Path("data/home.md")

MANIFEST = Path("data/master_urls.txt")
# The committed build is a second, independent manifest: whatever the live site
# currently renders must be re-scraped even if link discovery misses it.
BUILT = Path("data/wiki_data.json")

# build_data.py discards non-English variants (Materials/de) and slugs whose
# closing bracket the link parser ate (Bonus_Experience_%28Mechanics). Both
# shapes are in data/master_urls.txt, and scraping them costs a credit each to
# produce a file that is then thrown away, so they are filtered out up front.
LANG_SUFFIX = re.compile(
    r"[-./](de|fr|es|it|pt|pl|nl|ru|zh|ja|ko|tr|cs|fi|sv|da|no|uk|hu|ro|el|he"
    r"|ar|th|id|vi|hr|sk|sl|et|lt|lv)$", re.I)


def wanted(key: str) -> bool:
    """Would build_data.py keep a page with this (decoded) title?"""
    if not key or key == HOME_KEY:
        return False
    if LANG_SUFFIX.search(key):
        return False
    if key.count("(") != key.count(")"):
        return False
    return True


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def log(msg: str) -> None:
    print(msg, flush=True)


def page_of(url: str) -> str:
    return url[len(BASE):]


def key_of_page(page: str) -> str:
    """Percent-decoded page title -- the stable identity of a wiki page."""
    return urllib.parse.unquote(page)


def key_of_file(path: Path) -> str:
    return urllib.parse.unquote(path.name[len(PREFIX):-len(".md")])


def cached() -> dict[str, list[Path]]:
    """Map of decoded page key -> cached markdown files holding it."""
    out: dict[str, list[Path]] = {}
    if not CACHE.is_dir():
        return out
    for p in sorted(CACHE.glob("*.md")):
        if not p.name.startswith(PREFIX):
            continue
        try:
            if p.stat().st_size == 0:
                continue
        except OSError:
            continue
        out.setdefault(key_of_file(p), []).append(p)
    return out


def read_manifest() -> list[str]:
    """Every page URL worth scraping, de-duplicated by decoded key.

    Two sources, unioned: data/master_urls.txt (the crawl manifest, rebuilt by
    build_urls.py from links found in the cache) and the page slugs of the
    committed data/wiki_data.json. The second matters because .firecrawl/ is
    gitignored: the committed build is the only record of the page set that
    survives into a fresh CI checkout, so it keeps a link-discovery hiccup from
    quietly shrinking the site.
    """
    keys: dict[str, str] = {}  # decoded key -> url

    def add(key: str) -> None:
        if wanted(key) and key not in keys:
            keys[key] = BASE + urllib.parse.quote(key)

    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            u = line.strip()
            if not u.startswith(BASE):
                continue
            page = page_of(u)
            if not page or "#" in page or "?" in page:
                continue
            add(key_of_page(page))
    if BUILT.exists():
        try:
            built = json.loads(BUILT.read_text(encoding="utf-8"))
            for slug in (built.get("pages") or {}):
                add(key_of_page(slug))
        except (json.JSONDecodeError, OSError) as exc:
            log(f"[manifest] could not read {BUILT}: {exc}")
    if not keys:
        sys.exit(f"no page urls found in {MANIFEST} or {BUILT}")
    return [keys[k] for k in sorted(keys)]


# --------------------------------------------------------------------------
# scraping
# --------------------------------------------------------------------------
def scrape(urls: list[str], args, label: str) -> None:
    """Scrape URLs in throttled batches. Coverage is verified by file presence
    afterwards, so a batch that reports failure is retried but never fatal."""
    if not urls:
        log(f"[{label}] nothing to scrape")
        return
    total = len(urls)
    batches = (total + args.batch_size - 1) // args.batch_size
    log(f"[{label}] scraping {total} url(s) in {batches} batch(es) of "
        f"{args.batch_size}")
    if args.dry_run:
        for u in urls[:10]:
            log(f"[{label}]   would scrape {u}")
        if total > 10:
            log(f"[{label}]   ... and {total - 10} more")
        return

    failures = 0
    for i in range(0, total, args.batch_size):
        chunk = urls[i:i + args.batch_size]
        n = i // args.batch_size + 1
        cmd = ["firecrawl", "scrape", *chunk]
        if args.max_age is not None:
            cmd += ["--max-age", str(args.max_age)]
        ok = False
        for attempt in range(1, args.retries + 1):
            # stdout is the scraped markdown itself -- megabytes of it; discard.
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE, text=True)
            if proc.returncode == 0:
                ok = True
                break
            err = (proc.stderr or "").strip().splitlines()
            tail = err[-1] if err else f"exit {proc.returncode}"
            log(f"[{label}] batch {n}/{batches} attempt {attempt} failed: {tail}")
            if attempt < args.retries:
                time.sleep(args.batch_delay * attempt * 2)
        if not ok:
            failures += 1
        log(f"[{label}] batch {n}/{batches} {'ok' if ok else 'FAILED'}")
        if i + args.batch_size < total:
            time.sleep(args.batch_delay)
    if failures:
        log(f"[{label}] {failures} batch(es) failed after retries")


def refresh_home(args) -> None:
    """Scrape the main page straight into data/home.md."""
    log("[home] refreshing data/home.md")
    if args.dry_run:
        return
    cmd = ["firecrawl", "scrape", HOME_URL]
    if args.max_age is not None:
        cmd += ["--max-age", str(args.max_age)]
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE, text=True)
    produced = [p for p in CACHE.glob("*.md")
                if p.name.startswith(PREFIX) and key_of_file(p) == HOME_KEY]
    if proc.returncode != 0 or not produced:
        log("[home] scrape failed; keeping the committed data/home.md")
        for p in produced:
            p.unlink(missing_ok=True)
        return
    src = max(produced, key=lambda p: p.stat().st_size)
    if src.stat().st_size < 2000:
        log(f"[home] scraped file suspiciously small ({src.stat().st_size} B); "
            "keeping the committed data/home.md")
    else:
        HOME_DEST.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, HOME_DEST)
        log(f"[home] wrote {HOME_DEST} ({HOME_DEST.stat().st_size} B)")
    # never leave the main page in .firecrawl/: build_data.py would emit it a
    # second time, as its own page, alongside Home.
    for p in produced:
        p.unlink(missing_ok=True)


# --------------------------------------------------------------------------
# post-processing
# --------------------------------------------------------------------------
def dedupe() -> int:
    """Drop files that decode to a page we already have under another spelling."""
    dropped = 0
    for key, paths in cached().items():
        if len(paths) < 2:
            continue
        keep = max(paths, key=lambda p: (p.stat().st_size, p.stat().st_mtime))
        for p in paths:
            if p != keep:
                log(f"[dedupe] {p.name} (duplicate of {keep.name})")
                p.unlink(missing_ok=True)
                dropped += 1
    return dropped


def restore_gaps(backup: Path, urls: list[str]) -> int:
    """Put back the previous copy of any manifest page we failed to re-scrape."""
    if not backup.is_dir():
        return 0
    have = cached()
    old: dict[str, Path] = {}
    for p in sorted(backup.glob("*.md")):
        if p.name.startswith(PREFIX) and p.stat().st_size > 0:
            old.setdefault(key_of_file(p), p)
    restored = 0
    for u in urls:
        k = key_of_page(page_of(u))
        if k in have or k not in old:
            continue
        dest = CACHE / old[k].name
        shutil.copyfile(old[k], dest)
        log(f"[restore] {dest.name} (fresh scrape missing; kept previous copy)")
        restored += 1
    return restored


def run_build_urls() -> None:
    log("[discover] python build_urls.py")
    subprocess.run([sys.executable, "build_urls.py"], check=True)


def summarise(lines: list[str]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batch-size", type=int, default=8,
                    help="URLs per firecrawl invocation (default: 8)")
    ap.add_argument("--batch-delay", type=float, default=10.0,
                    help="seconds to wait between batches (default: 10)")
    ap.add_argument("--retries", type=int, default=3,
                    help="attempts per batch (default: 3)")
    ap.add_argument("--max-age", type=int, default=86_400_000,
                    help="Firecrawl --max-age in ms; 0 forces a fully fresh "
                         "fetch at full credit cost (default: 86400000 = 24h)")
    ap.add_argument("--discovery-rounds", type=int, default=2,
                    help="build_urls.py + scrape-the-new passes (default: 2)")
    ap.add_argument("--max-urls", type=int, default=800,
                    help="abort if the manifest exceeds this many pages; a "
                         "runaway manifest is a credit bill, and this job runs "
                         "unattended (default: 800)")
    ap.add_argument("--full-refresh", action="store_true",
                    help="ignore the restored cache entirely: pages that fail "
                         "to re-scrape are dropped instead of kept")
    ap.add_argument("--dry-run", action="store_true",
                    help="plan only; never call firecrawl (spends no credits)")
    args = ap.parse_args()

    if not args.dry_run and not os.environ.get("FIRECRAWL_API_KEY"):
        sys.exit("FIRECRAWL_API_KEY is not set -- configure the repository "
                 "secret before running the refresh")

    CACHE.mkdir(exist_ok=True)
    manifest = read_manifest()
    log(f"manifest: {len(manifest)} page url(s) "
        f"(~{len(manifest)} Firecrawl credits per full pass)")
    if len(manifest) > args.max_urls:
        log(f"::error::manifest has {len(manifest)} urls, over the "
            f"--max-urls budget of {args.max_urls}. Either the wiki grew a lot "
            "or link discovery regressed; raise the budget deliberately rather "
            "than letting an unattended run spend the credits.")
        return 1

    # Move the restored cache aside so every page is genuinely re-fetched.
    backup = Path(os.environ.get("RUNNER_TEMP") or ".") / "firecrawl-prev"
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)
    before = len(cached())
    if before and not args.dry_run:
        shutil.move(str(CACHE), str(backup))
        CACHE.mkdir(exist_ok=True)
        log(f"set aside {before} previously cached page(s) -> {backup}")

    refresh_home(args)
    scrape(manifest, args, "manifest")

    # Discovery: build_urls.py rewrites the manifest from links found in the
    # pages we just scraped, so newly added wiki pages show up here.
    discovered_total = 0
    for rnd in range(1, args.discovery_rounds + 1):
        if args.dry_run:
            break
        run_build_urls()
        manifest = read_manifest()
        have = cached()
        missing = [u for u in manifest
                   if key_of_page(page_of(u)) not in have]
        if not missing:
            log(f"[discover] round {rnd}: no new pages")
            break
        budget = args.max_urls - len(manifest)
        if len(missing) > max(0, budget):
            log(f"::warning::discovery round {rnd} found {len(missing)} new "
                f"page(s) but only {max(0, budget)} are left in the "
                "--max-urls budget; scraping the first ones only")
            missing = missing[:max(0, budget)]
        if not missing:
            break
        log(f"[discover] round {rnd}: {len(missing)} new/absent page(s)")
        discovered_total += len(missing)
        scrape(missing, args, f"discover-{rnd}")

    restored = 0
    if not args.dry_run:
        if not args.full_refresh:
            restored = restore_gaps(backup, manifest)
        dropped = dedupe()
        shutil.rmtree(backup, ignore_errors=True)
        run_build_urls()  # final manifest reflects the final cache
    else:
        dropped = 0

    after = len(cached())
    have = cached()
    still_missing = [u for u in read_manifest()
                     if key_of_page(page_of(u)) not in have]

    log("")
    log(f"cached pages: {before} -> {after}")
    log(f"newly discovered: {discovered_total}, restored from previous run: "
        f"{restored}, duplicates dropped: {dropped}")
    log(f"manifest urls with no page: {len(still_missing)}")
    for u in still_missing[:20]:
        log(f"  no page for {u}")

    summarise([
        "### Crawl refresh",
        "",
        f"- cached pages: **{before} -> {after}**",
        f"- newly discovered: {discovered_total}",
        f"- restored from previous run: {restored}",
        f"- duplicates dropped: {dropped}",
        f"- manifest urls with no page: {len(still_missing)}",
    ])

    if args.dry_run:
        return 0

    # A wholesale collapse means the crawl broke, not that the wiki shrank.
    # Stop before build_data.py bakes the damage into the site.
    if before and after < before * 0.75:
        log(f"::error::cache collapsed from {before} to {after} pages "
            "(<75%); refusing to rebuild")
        return 1
    if after < 50:
        log(f"::error::only {after} page(s) cached; refusing to rebuild")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
