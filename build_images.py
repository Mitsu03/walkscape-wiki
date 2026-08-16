#!/usr/bin/env python3
"""Download the images referenced by the pages, compress hard, and emit
data/images.json = {id: data-uri} within a size budget.

Encoding strategy
-----------------
Almost every "SVG" on the WalkScape wiki is *pixel art* exported by
"Pixels to Svg": a 32x32 (or 20x20 / 48x48 / ...) sprite emitted as one
`<path>` per colour, made of thousands of 1px horizontal runs.  Kept as a
vector data URI those average ~3 kB each *after* percent-encoding, which
made them ~75% of the whole payload for images that are really only a few
hundred actual pixels.

So we rasterise them back onto their native pixel grid (exact, no
resampling), scale up by an integer factor with NEAREST so they stay crisp
pixel art at the sizes the UI uses, and store lossless WebP.  That is
visually identical to the vector and roughly 9x smaller.

- pixel-art SVG -> exact raster -> integer NEAREST upscale -> lossless WebP
- other SVG     -> minified, embedded as utf8 data URI (vectors stay crisp)
- PNG/JPG       -> downscaled + lossy WebP, embedded as base64
- images that no page references are dropped entirely
Animated GIFs are already excluded upstream.
"""
import json, os, re, io, base64, urllib.parse, urllib.request, concurrent.futures
from PIL import Image

CACHE = "data/img_cache"
os.makedirs(CACHE, exist_ok=True)
IMG_MAP = json.load(open("data/img_map.json", encoding="utf-8"))

# --- size targets -----------------------------------------------------------
# build_site.py displays images at, at most:
#   img.ic       1.35em / 1.6em inline icon      ~20-26 CSS px
#   .thumb img   26 px                           ~26 CSS px
#   .ibx-fig img max-height 130px                ~130 CSS px
#   .body img.bl max-height 210px                ~210 CSS px
# so icons only ever need ~128px (covers 26px at 4x DPR and 130px infobox
# figures), while true content images want ~256px to stay legible in the
# 210px block slot on a hi-dpi phone.
SPRITE_TARGET = 128      # long edge to upscale pixel-art sprites toward
ICON_MAX = 128           # max px on the long edge for small raster icons
CONTENT_MAX = 256        # max px on the long edge for large content rasters
ICON_SRC_CUTOFF = 200    # source long edge below this counts as an icon
ICON_Q = 70
CONTENT_Q = 58
SVG_MAX_BYTES = 40000    # skip absurdly heavy *vector* svgs (non pixel-art)
RASTER_MAX_BYTES = 40000 # skip rasters that won't compress small enough
TOTAL_BUDGET = 6_200_000 # safety cap on total data-uri payload (chars)

UA = {"User-Agent": "Mozilla/5.0 (WalkScapeCompanion build script)"}

# ---------------------------------------------------------------------------
# which images are actually reachable from a page?
# ---------------------------------------------------------------------------
def referenced_ids():
    """Ids that build_site.py can actually look up: `data-i` attributes in the
    page HTML and the per-page `icon` field.  Anything else in img_map.json is
    a dangling reference and would only bloat the payload."""
    try:
        raw = open("data/wiki_data.json", encoding="utf-8").read()
    except FileNotFoundError:
        return None  # no page data -> fall back to encoding everything
    ids = set(re.findall(r'data-i=\\"([0-9a-f]{12})\\"', raw))
    ids |= set(re.findall(r'data-i="([0-9a-f]{12})"', raw))
    ids |= set(re.findall(r'"icon":\s*"([0-9a-f]{12})"', raw))
    return ids or None


def fetch(item):
    iid, url = item
    ext = url.rsplit(".", 1)[-1].split("?")[0].lower()
    if ext not in ("svg", "png", "jpg", "jpeg", "gif", "webp"):
        ext = "png"
    path = os.path.join(CACHE, iid + "." + ext)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return iid, path, ext, None
    err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            data = urllib.request.urlopen(req, timeout=30).read()
            if not data:
                raise ValueError("empty response")
            with open(path, "wb") as f:
                f.write(data)
            return iid, path, ext, None
        except Exception as e:
            err = "%s: %s" % (type(e).__name__, e)
    return iid, None, ext, err


def minify_svg(txt):
    txt = re.sub(r"<!--.*?-->", "", txt, flags=re.S)
    txt = re.sub(r"<\?xml.*?\?>", "", txt, flags=re.S)
    txt = re.sub(r"<!DOCTYPE.*?>", "", txt, flags=re.S)
    txt = re.sub(r"<metadata\b.*?</metadata>", "", txt, flags=re.S)
    txt = re.sub(r">\s+<", "><", txt)
    txt = re.sub(r"\s{2,}", " ", txt).strip()
    return txt


# ---------------------------------------------------------------------------
# pixel-art SVG -> exact raster
# ---------------------------------------------------------------------------
RE_SVG_TAG = re.compile(r"<svg\b([^>]*)>")
RE_PATH = re.compile(r"<path\b([^>]*?)/?>")
RE_RECT = re.compile(r"<rect\b([^>]*?)/?>")
RE_SEG = re.compile(r"M(-?[\d.]+) (-?[\d.]+)h([\d.]+)")
RE_VIEWBOX = re.compile(
    r'viewBox="\s*(-?[\d.]+)[\s,]+(-?[\d.]+)[\s,]+(-?[\d.]+)[\s,]+(-?[\d.]+)"')
# a pixel-art export uses only <path>/<rect> primitives; anything else
# (circle, polygon, gradients, transforms, ...) means a real vector.
RE_OTHER_TAG = re.compile(
    r"<(?!/|svg\b|path\b|rect\b|g\b|title\b|desc\b|metadata\b|\?|!)([a-zA-Z][\w:-]*)")


def parse_color(s):
    s = s.strip()
    if s.startswith("#"):
        if len(s) == 4:
            return (int(s[1] * 2, 16), int(s[2] * 2, 16), int(s[3] * 2, 16), 255)
        if len(s) == 7:
            return (int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16), 255)
        if len(s) == 9:
            return (int(s[1:3], 16), int(s[3:5], 16),
                    int(s[5:7], 16), int(s[7:9], 16))
        return None
    m = re.match(r"rgba?\(([^)]*)\)$", s)
    if m:
        p = [x.strip() for x in m.group(1).replace("/", ",").split(",") if x.strip()]
        try:
            r, g, b = (max(0, min(255, int(round(float(x))))) for x in p[:3])
            a = int(round(float(p[3]) * 255)) if len(p) > 3 else 255
        except ValueError:
            return None
        return (r, g, b, max(0, min(255, a)))
    if s in ("none", "transparent"):
        return (0, 0, 0, 0)
    return None


def svg_to_pixels(txt):
    """Rasterise a Pixels-to-Svg pixel-art SVG onto its exact native grid.
    Returns None if the file is not of that restricted shape."""
    m = RE_SVG_TAG.search(txt)
    if not m:
        return None
    head = m.group(1)
    body = txt[m.end():]
    if RE_OTHER_TAG.search(body):
        return None                        # real vector art -> keep as SVG
    if "transform=" in body or "url(#" in txt or "opacity=" in body:
        return None
    vb = RE_VIEWBOX.search(head)
    if vb:
        vx, vy, vw, vh = (float(x) for x in vb.groups())
        w, h = int(round(vw)), int(round(vh))
        # Pixels-to-Svg uses "0 -0.5 W H": the -0.5 keeps 1px strokes crisp,
        # so stroke y == pixel row y.
        ox, oy = int(round(vx)), int(round(vy + 0.5))
    else:
        wm = re.search(r'width="([\d.]+)"', head)
        hm = re.search(r'height="([\d.]+)"', head)
        if not (wm and hm):
            return None
        w, h = int(round(float(wm.group(1)))), int(round(float(hm.group(1))))
        ox = oy = 0
    if not (0 < w <= 2048 and 0 < h <= 2048):
        return None

    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()

    def put(x, y, c):
        if not (0 <= x < w and 0 <= y < h):
            return
        if c[3] == 255:
            px[x, y] = c
        elif c[3]:
            dr, dg, db, da = px[x, y]
            a, d = c[3] / 255.0, da / 255.0
            na = a + d * (1 - a)
            if na <= 0:
                px[x, y] = (0, 0, 0, 0)
            else:
                px[x, y] = (
                    int(round((c[0] * a + dr * d * (1 - a)) / na)),
                    int(round((c[1] * a + dg * d * (1 - a)) / na)),
                    int(round((c[2] * a + db * d * (1 - a)) / na)),
                    int(round(na * 255)))

    drew = 0
    for attrs in RE_PATH.findall(body):
        sm = re.search(r'stroke="([^"]*)"', attrs)
        dm = re.search(r'd="([^"]*)"', attrs)
        if not (sm and dm):
            return None
        d = dm.group(1)
        # the only grammar we understand is a run of "Mx yh<len>" segments;
        # anything else means this is real vector art, not a pixel export
        if RE_SEG.sub("", d).strip():
            return None
        c = parse_color(sm.group(1))
        if c is None:
            return None
        for xs, ys, ln in RE_SEG.findall(d):
            x0 = int(round(float(xs))) - ox
            y0 = int(round(float(ys))) - oy
            for i in range(int(round(float(ln)))):
                put(x0 + i, y0, c)
                drew += 1
    for attrs in RE_RECT.findall(body):
        f = re.search(r'fill="([^"]*)"', attrs)
        gx = re.search(r'x="(-?[\d.]+)"', attrs)
        gy = re.search(r'y="(-?[\d.]+)"', attrs)
        gw = re.search(r'width="([\d.]+)"', attrs)
        gh = re.search(r'height="([\d.]+)"', attrs)
        if not (f and gx and gy and gw and gh):
            return None
        c = parse_color(f.group(1))
        if c is None:
            return None
        bx, by = int(float(gx.group(1))) - ox, int(float(gy.group(1))) - oy
        for yy in range(int(float(gh.group(1)))):
            for xx in range(int(float(gw.group(1)))):
                put(bx + xx, by + yy, c)
                drew += 1
    if not drew:
        return None
    return im


def webp(im, lossless=False, quality=80):
    buf = io.BytesIO()
    if lossless:
        im.save(buf, format="WEBP", lossless=True, quality=100, method=4)
    else:
        im.save(buf, format="WEBP", quality=quality, method=6)
    return buf.getvalue()


def datauri_webp(raw):
    return "data:image/webp;base64," + base64.b64encode(raw).decode()


def encode_sprite(sprite):
    """Encode an exactly-rasterised pixel-art sprite.

    Small sprites (real icons) are integer-upscaled with NEAREST so the pixel
    grid stays razor sharp at the sizes the UI uses, then stored lossless -
    flat pixel art compresses so well that lossless is both smaller and
    perfect.  A few "sprites" are really full illustrations exported pixel by
    pixel (thousands of colours, hundreds of px wide); those behave like
    content rasters, so they get downscaled and encoded lossily instead."""
    if max(sprite.size) >= ICON_SRC_CUTOFF:
        w, h = sprite.size
        scale = min(1.0, CONTENT_MAX / max(w, h))
        if scale < 1.0:
            sprite = sprite.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                                   Image.LANCZOS)
        for q in (CONTENT_Q + 20, CONTENT_Q, CONTENT_Q - 15):
            raw = webp(sprite, quality=q)
            if len(raw) <= RASTER_MAX_BYTES:
                return raw
        return None

    f = max(1, SPRITE_TARGET // max(sprite.size))
    if f > 1:
        sprite = sprite.resize((sprite.width * f, sprite.height * f), Image.NEAREST)
    raw = webp(sprite, lossless=True)
    if len(raw) <= RASTER_MAX_BYTES:
        return raw
    for q in (92, 80):                       # safety net, rarely reached
        raw = webp(sprite, quality=q)
        if len(raw) <= RASTER_MAX_BYTES:
            return raw
    return None


def to_datauri(iid, path, ext):
    try:
        if ext == "svg":
            txt = open(path, encoding="utf-8", errors="ignore").read()
            sprite = svg_to_pixels(txt)
            if sprite is not None:
                raw = encode_sprite(sprite)
                if raw is not None:
                    return datauri_webp(raw)
                # pathological sprite: fall through to the vector path
            txt = minify_svg(txt)
            if not txt or len(txt) > SVG_MAX_BYTES:
                return None
            enc = urllib.parse.quote(txt, safe="~()*!.'")
            return "data:image/svg+xml,%s" % enc

        # raster
        im = Image.open(path)
        im.load()
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")
        w, h = im.size
        long_edge = max(w, h)
        if long_edge < ICON_SRC_CUTOFF:
            cap, q = ICON_MAX, ICON_Q
        else:
            cap, q = CONTENT_MAX, CONTENT_Q
        scale = min(1.0, cap / long_edge)
        if scale < 1.0:
            im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                           Image.LANCZOS)
        raw = webp(im, quality=q)
        if len(raw) > RASTER_MAX_BYTES:
            return None
        return datauri_webp(raw)
    except Exception:
        return None


def main():
    wanted = referenced_ids()
    if wanted is None:
        items = list(IMG_MAP.items())
        print("No page data found - encoding all %d mapped images." % len(items))
    else:
        items = [(k, v) for k, v in IMG_MAP.items() if k in wanted]
        print("img_map has %d entries; %d are referenced by a page, "
              "%d dangling refs dropped."
              % (len(IMG_MAP), len(items), len(IMG_MAP) - len(items)))

    print("Downloading %d images..." % len(items))
    got, failed = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        for iid, path, ext, err in ex.map(fetch, items):
            if path:
                got.append((iid, path, ext))
            else:
                failed.append((iid, err))
    if failed:
        print("  %d could not be downloaded:" % len(failed))
        for iid, err in failed[:20]:
            print("    %s  %s  (%s)" % (iid, IMG_MAP.get(iid, ""), err))
    print("Fetched %d. Encoding..." % len(got))

    encoded, unencodable = {}, []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(to_datauri, iid, path, ext): (iid, ext)
                for iid, path, ext in got}
        for fut in concurrent.futures.as_completed(futs):
            iid, ext = futs[fut]
            uri = fut.result()
            if uri:
                encoded[iid] = (uri, ext)
            else:
                unencodable.append(iid)
    if unencodable:
        print("  %d could not be encoded:" % len(unencodable))
        for iid in unencodable[:20]:
            print("    %s  %s" % (iid, IMG_MAP.get(iid, "")))

    # budget: smallest first, so a squeeze drops the fewest images possible
    order = sorted(encoded.items(), key=lambda kv: len(kv[1][0]))
    out, total, skipped = {}, 0, 0
    for iid, (uri, ext) in order:
        if total + len(uri) > TOTAL_BUDGET:
            skipped += 1
            continue
        out[iid] = uri
        total += len(uri)

    # keep a stable, readable ordering in the file
    out = {k: out[k] for k in sorted(out)}
    with open("data/images.json", "w", encoding="utf-8") as f:
        json.dump(out, f)

    dropped = [k for k, _ in items if k not in out]
    print("Embedded %d images (%.2f MB payload); %d over budget, "
          "%d failed to encode, %d failed to download."
          % (len(out), total / 1024 / 1024, skipped,
             len(unencodable), len(failed)))
    if dropped:
        print("WARNING: %d referenced images have no data URI and will render "
              "as 'image unavailable': %s" % (len(dropped), ", ".join(dropped[:10])))


if __name__ == "__main__":
    main()
