#!/usr/bin/env python3
"""Download the images referenced by the pages, compress hard, and emit
data/images.json = {id: data-uri} within a size budget.

- SVG  -> minified, embedded as utf8 data URI (vectors stay crisp & tiny)
- PNG/JPG -> downscaled + WebP, embedded as base64
Animated GIFs are already excluded upstream.
"""
import json, os, re, io, base64, urllib.parse, urllib.request, concurrent.futures
from PIL import Image

CACHE = "data/img_cache"
os.makedirs(CACHE, exist_ok=True)
IMG_MAP = json.load(open("data/img_map.json", encoding="utf-8"))

RASTER_MAX = 128         # max px on the long edge for icons/rasters
WEBP_Q = 72
SVG_MAX_BYTES = 22000    # skip absurdly heavy svgs
RASTER_MAX_BYTES = 14000 # skip rasters that won't compress small enough
TOTAL_BUDGET = 6_200_000 # cap total data-uri payload (chars)

UA = {"User-Agent": "Mozilla/5.0 (WalkScapeCompanion build script)"}

def fetch(item):
    iid, url = item
    ext = url.rsplit(".", 1)[-1].split("?")[0].lower()
    path = os.path.join(CACHE, iid + "." + ext)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return iid, path, ext
    try:
        req = urllib.request.Request(url, headers=UA)
        data = urllib.request.urlopen(req, timeout=30).read()
        with open(path, "wb") as f:
            f.write(data)
        return iid, path, ext
    except Exception as e:
        return iid, None, ext

def minify_svg(txt):
    txt = re.sub(r"<!--.*?-->", "", txt, flags=re.S)
    txt = re.sub(r"<\?xml.*?\?>", "", txt, flags=re.S)
    txt = re.sub(r"<!DOCTYPE.*?>", "", txt, flags=re.S)
    txt = re.sub(r">\s+<", "><", txt)
    txt = re.sub(r"\s{2,}", " ", txt).strip()
    return txt

def to_datauri(iid, path, ext):
    try:
        if ext == "svg":
            txt = open(path, encoding="utf-8", errors="ignore").read()
            txt = minify_svg(txt)
            if not txt or len(txt) > SVG_MAX_BYTES:
                return None
            enc = urllib.parse.quote(txt, safe="~()*!.'")
            return "data:image/svg+xml,%s" % enc
        # raster
        im = Image.open(path)
        im.load()
        if im.mode in ("P", "LA"):
            im = im.convert("RGBA")
        elif im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")
        w, h = im.size
        scale = min(1.0, RASTER_MAX / max(w, h))
        if scale < 1.0:
            im = im.resize((max(1, int(w*scale)), max(1, int(h*scale))),
                           Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="WEBP", quality=WEBP_Q, method=6)
        raw = buf.getvalue()
        if len(raw) > RASTER_MAX_BYTES:
            return None
        return "data:image/webp;base64," + base64.b64encode(raw).decode()
    except Exception:
        return None

def main():
    items = list(IMG_MAP.items())
    print(f"Downloading {len(items)} images...")
    got = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        for iid, path, ext in ex.map(fetch, items):
            if path:
                got.append((iid, path, ext))
    print(f"Fetched {len(got)}. Encoding...")

    encoded = {}
    for iid, path, ext in got:
        uri = to_datauri(iid, path, ext)
        if uri:
            encoded[(iid)] = (uri, ext)

    # budget: svgs first (small+vector), then rasters by size ascending
    order = sorted(encoded.items(),
                   key=lambda kv: (0 if kv[1][1] == "svg" else 1, len(kv[1][0])))
    out = {}
    total = 0
    skipped = 0
    for iid, (uri, ext) in order:
        if total + len(uri) > TOTAL_BUDGET:
            skipped += 1
            continue
        out[iid] = uri
        total += len(uri)

    with open("data/images.json", "w", encoding="utf-8") as f:
        json.dump(out, f)
    print(f"Embedded {len(out)} images ({total/1024/1024:.2f} MB payload); "
          f"skipped {skipped} over budget, {len(got)-len(encoded)} failed to encode.")

if __name__ == "__main__":
    main()
