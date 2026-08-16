#!/usr/bin/env python3
"""Sanity-check a regenerated build against the committed one, and decide
whether it is worth opening a pull request.

Used by .github/workflows/refresh-content.yml after build_data.py /
build_images.py / build_site.py have run. Two jobs:

1. Guard rails. A half-finished crawl still produces a perfectly valid
   wiki_data.json -- just a much smaller one. Without a floor, a bad refresh
   would happily open a PR that deletes half the wiki, and the diff is far too
   large for a human to notice. So the regenerated build must stay within a
   ratio of the committed one, and no section may empty out.

2. A readable PR body. The diffs themselves are unreviewable (index.html is
   ~10 MB of generated markup), so the value of the review is in the summary:
   which pages appeared, which disappeared, which changed, and how the section
   counts moved.

Exit codes: 0 ok, 1 guard tripped.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

DATA = Path("data/wiki_data.json")
IMAGES = Path("data/images.json")
SITE = Path("index.html")


def git_show(path: Path) -> bytes | None:
    """Committed version of a file, or None if it is not in HEAD.

    Note the as_posix(): git wants forward slashes in a `HEAD:<path>` revspec,
    and str(Path) hands it backslashes on Windows. Getting that wrong makes this
    look like "no committed build", which silently disables the whole guard --
    so the caller treats an unreadable-but-present baseline as an error.
    """
    proc = subprocess.run(["git", "show", f"HEAD:{path.as_posix()}"],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return proc.stdout if proc.returncode == 0 else None


def in_head(path: Path) -> bool:
    proc = subprocess.run(
        ["git", "ls-tree", "--name-only", "HEAD", "--", path.as_posix()],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    return bool(proc.stdout.strip())


def load_json_blob(path: Path):
    """Parsed committed JSON, or None if the file is not committed at all.

    Raises if it is committed but unreadable: a baseline we cannot parse must
    not be mistaken for a baseline that does not exist.
    """
    blob = git_show(path)
    if blob is None:
        if in_head(path):
            raise RuntimeError(f"{path} is committed but `git show` failed")
        return None
    try:
        return json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"committed {path} is not readable JSON: {exc}")


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(obj) -> str:
    return hashlib.sha1(canonical(obj).encode("utf-8")).hexdigest()


def set_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")
    print(f"::notice::{name}={value}")


def bullet_list(items: list[str], cap: int) -> list[str]:
    out = [f"- `{s}`" for s in sorted(items)[:cap]]
    if len(items) > cap:
        out.append(f"- ...and {len(items) - cap} more")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-page-ratio", type=float, default=0.90,
                    help="fail if pages drop below this fraction of the "
                         "committed build (default: 0.90)")
    # Looser than the page floor on purpose: build_images.py fills a fixed byte
    # budget, so adding pages legitimately evicts images and the count wobbles.
    ap.add_argument("--min-image-ratio", type=float, default=0.70,
                    help="fail if embedded images drop below this fraction "
                         "(default: 0.70)")
    ap.add_argument("--min-site-ratio", type=float, default=0.80,
                    help="fail if index.html shrinks below this fraction "
                         "(default: 0.80)")
    ap.add_argument("--pr-body", type=Path, default=None,
                    help="write the pull-request body here")
    args = ap.parse_args()

    for p in (DATA, IMAGES, SITE):
        if not p.exists() or p.stat().st_size == 0:
            print(f"::error::{p} is missing or empty after the build")
            return 1

    new = json.loads(DATA.read_text(encoding="utf-8"))
    old = load_json_blob(DATA)
    new_imgs = json.loads(IMAGES.read_text(encoding="utf-8"))
    old_imgs = load_json_blob(IMAGES)
    old_site = git_show(SITE)
    site_bytes = SITE.stat().st_size

    new_pages: dict = new.get("pages", {})
    report: list[str] = []   # table rows
    notes: list[str] = []    # prose, kept out of the table
    failed = False

    if old is None:
        notes.append("> No committed build to compare against, so the "
                     "regression guard was skipped for this run.")
        report.append(f"| pages | - | {len(new_pages)} | - |")
        added, removed, edited = sorted(new_pages), [], []
    else:
        old_pages: dict = old.get("pages", {})
        added = sorted(set(new_pages) - set(old_pages))
        removed = sorted(set(old_pages) - set(new_pages))
        edited = sorted(k for k in set(new_pages) & set(old_pages)
                        if digest(new_pages[k]) != digest(old_pages[k]))

        if old_pages and len(new_pages) < len(old_pages) * args.min_page_ratio:
            print(f"::error::page count fell from {len(old_pages)} to "
                  f"{len(new_pages)} (below {args.min_page_ratio:.0%}); "
                  "this looks like a broken crawl, not a wiki change")
            failed = True

        for section, slugs in (old.get("sections") or {}).items():
            if slugs and not (new.get("sections") or {}).get(section):
                print(f"::error::section '{section}' is empty in the new build "
                      f"(was {len(slugs)} page(s))")
                failed = True

        report.append(
            f"| pages | {len(old_pages)} | {len(new_pages)} | "
            f"{len(new_pages) - len(old_pages):+d} |")

    if old_imgs is not None:
        if len(new_imgs) < len(old_imgs) * args.min_image_ratio:
            print(f"::error::embedded images fell from {len(old_imgs)} to "
                  f"{len(new_imgs)} (below {args.min_image_ratio:.0%})")
            failed = True
        report.append(f"| embedded images | {len(old_imgs)} | {len(new_imgs)} | "
                      f"{len(new_imgs) - len(old_imgs):+d} |")

    if old_site is not None:
        if site_bytes < len(old_site) * args.min_site_ratio:
            print(f"::error::index.html shrank from {len(old_site)} to "
                  f"{site_bytes} bytes (below {args.min_site_ratio:.0%})")
            failed = True
        report.append(f"| index.html (MB) | {len(old_site)/1e6:.2f} | "
                      f"{site_bytes/1e6:.2f} | "
                      f"{(site_bytes - len(old_site))/1e6:+.2f} |")

    # --- did anything actually change? -----------------------------------
    # Compared semantically, not byte-wise: an identical crawl must not open a
    # weekly no-op PR that adds ~21 MB of blobs to the repository history.
    changed = (
        old is None
        or canonical(new) != canonical(old)
        or old_imgs is None
        or canonical(new_imgs) != canonical(old_imgs)
    )

    lines: list[str] = []
    lines.append("Automated content refresh from the live wiki "
                 "(`.github/workflows/refresh-content.yml`).")
    lines.append("")
    lines.append("| metric | before | after | delta |")
    lines.append("| --- | ---: | ---: | ---: |")
    lines.extend(report)
    lines.append("")
    if notes:
        lines.extend(notes)
        lines.append("")

    counts = {s: len(v) for s, v in (new.get("sections") or {}).items()}
    if counts:
        lines.append("**Sections:** " +
                     ", ".join(f"{s} {n}" for s, n in counts.items()))
        lines.append("")

    if added:
        lines.append(f"**New pages ({len(added)})**")
        lines.extend(bullet_list(added, 40))
        lines.append("")
    if removed:
        lines.append(f"**Pages no longer present ({len(removed)})** "
                     "-- check these were really removed upstream and did not "
                     "just fail to scrape.")
        lines.extend(bullet_list(removed, 40))
        lines.append("")
    if edited:
        lines.append(f"**Updated pages ({len(edited)})**")
        lines.extend(bullet_list(edited, 40))
        lines.append("")
    if not (added or removed or edited):
        lines.append("No page-level differences detected.")
        lines.append("")

    lines.append("`index.html` and `data/*.json` are build artifacts; review "
                 "the summary above rather than the file diffs.")

    body = "\n".join(lines)
    if args.pr_body:
        args.pr_body.parent.mkdir(parents=True, exist_ok=True)
        args.pr_body.write_text(body, encoding="utf-8")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("\n### Build check\n\n" + body + "\n")

    print(body)
    set_output("changed", "true" if changed and not failed else "false")
    set_output("added", str(len(added)))
    set_output("removed", str(len(removed)))
    set_output("edited", str(len(edited)))

    if failed:
        return 1
    if not changed:
        print("::notice::content is identical to the committed build; "
              "no pull request needed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(f"::error::{exc}")
        sys.exit(1)
