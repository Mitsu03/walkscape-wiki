#!/usr/bin/env python3
"""Generate the single-file WalkScape Companion web app (index.html)
from data/wiki_data.json.

Everything the browser needs is inlined: markup, CSS, JS, the page payload
and the compressed image data-URIs. No network, no fonts to fetch, no build
step at runtime. Open index.html and it works.
"""
import json, os

with open("data/wiki_data.json", encoding="utf-8") as f:
    data = json.load(f)

# embed compressed image data-URIs, if the image pipeline has run
try:
    with open("data/images.json", encoding="utf-8") as f:
        data["images"] = json.load(f)
except FileNotFoundError:
    data["images"] = {}

SECTION_ORDER = ["Start Here", "Skills", "Activities", "Items & Equipment",
                 "Locations", "Game Systems", "Guides", "Glossary"]
sections = data["sections"]
data["order"] = [s for s in SECTION_ORDER if s in sections] + \
                [s for s in sections if s not in SECTION_ORDER]
data.setdefault("subs", {})

payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

TEMPLATE = r"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>WalkScape Companion</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<meta name="description" content="A fast, offline field companion for the WalkScape wiki: skills, activities, items, locations and game systems.">
<style>
:root{
  --canvas:#F3F6F4; --panel:#FFFFFF; --panel-2:#FAFCFB;
  --ink:#17252E; --ink-2:#617078; --ink-3:#8A979D;
  --line:#D8E1DE; --line-2:#E8EEEB;
  --glacier:#4FAEAA; --amber:#E5A449; --waypoint:#4E7DB8;
  --good:#58A66B; --warn:#D47B4C;
  --accent:var(--glacier);
  --tint:rgba(79,174,170,.10);
  --shadow:0 1px 2px rgba(23,37,46,.05), 0 10px 24px -18px rgba(23,37,46,.35);
  --r:6px;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --display:"Seravek","Gill Sans Nova",Optima,"Segoe UI",system-ui,sans-serif;
  --mono:ui-monospace,"SF Mono","IBM Plex Mono","Cascadia Mono",Menlo,Consolas,monospace;
  --measure:70ch;
  --side:260px; --rail:236px;
}
html[data-theme="dark"]{
  --canvas:#0E1820; --panel:#16242D; --panel-2:#132029;
  --ink:#EAF1EF; --ink-2:#99AAA5; --ink-3:#7A8B88;
  --line:#2A3B43; --line-2:#213038;
  --glacier:#6EC4C0; --amber:#EDB463; --waypoint:#7BA3D6;
  --good:#72BC85; --warn:#E0916A;
  --tint:rgba(110,196,192,.12);
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 12px 28px -18px rgba(0,0,0,.8);
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--canvas);color:var(--ink);font-family:var(--sans);
  font-size:16px;line-height:1.6;-webkit-font-smoothing:antialiased;
  overflow-wrap:break-word}
h1,h2,h3,h4{font-family:var(--display);font-weight:600;letter-spacing:-.008em;
  text-wrap:balance}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:2px}
button{font:inherit;color:inherit}
:focus-visible{outline:2px solid var(--waypoint);outline-offset:2px;border-radius:3px}
::selection{background:var(--tint)}
@media (prefers-reduced-motion:reduce){*{animation-duration:.001ms!important;
  transition-duration:.001ms!important;scroll-behavior:auto!important}}
.skip{position:absolute;left:8px;top:-60px;z-index:100;background:var(--panel);
  border:1px solid var(--line);border-radius:var(--r);padding:10px 14px;
  transition:top .15s}
.skip:focus{top:8px}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);
  white-space:nowrap}

/* ============ shell ============ */
.app{display:grid;grid-template-columns:var(--side) minmax(0,1fr);min-height:100vh}
html[data-side="off"] .app{grid-template-columns:0 minmax(0,1fr)}
html[data-side="off"] .side{transform:translateX(-100%);border-right:0}

/* ============ sidebar ============ */
.side{position:sticky;top:0;height:100vh;display:flex;flex-direction:column;
  background:var(--panel);border-right:1px solid var(--line);overflow:hidden;
  transition:transform .18s ease}
.brand{display:flex;align-items:center;gap:9px;padding:16px 14px 14px;
  text-decoration:none;color:inherit}
.brand:hover{text-decoration:none}
.brand .bm{width:26px;height:26px;flex:none;border-radius:50%;
  border:1.5px solid var(--glacier);display:grid;place-items:center}
.brand .bm i{width:7px;height:7px;border-radius:50%;background:var(--glacier);
  display:block}
.brand .bt{min-width:0}
.brand b{font-family:var(--display);font-size:.98rem;font-weight:600;
  letter-spacing:-.01em;line-height:1.15;display:block}
.brand .bs{font-family:var(--mono);font-size:.6rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ink-3);display:block}

.sbtn{display:flex;align-items:center;gap:8px;width:calc(100% - 20px);
  margin:0 10px 10px;padding:8px 10px;background:var(--panel-2);
  border:1px solid var(--line);border-radius:var(--r);color:var(--ink-2);
  cursor:pointer;text-align:left;font-size:.86rem;min-height:38px;
  white-space:nowrap;overflow:hidden}
.sbtn:hover{border-color:var(--glacier);color:var(--ink)}
.sbtn .k{margin-left:auto;font-family:var(--mono);font-size:.66rem;
  color:var(--ink-3);border:1px solid var(--line);border-radius:4px;
  padding:1px 5px;background:var(--panel)}
svg{flex:none}

.nav{flex:1;overflow-y:auto;overscroll-behavior:contain;padding:0 8px 20px}
.nav::-webkit-scrollbar{width:8px}
.nav::-webkit-scrollbar-thumb{background:var(--line);border-radius:8px}
.nrow{display:flex;align-items:center;gap:9px;width:100%;padding:7px 8px;
  border:0;background:none;border-radius:var(--r);cursor:pointer;
  font-size:.875rem;color:var(--ink-2);min-height:36px;text-align:left}
.nrow:hover{background:var(--panel-2);color:var(--ink)}
.nrow .glyph{width:9px;height:9px;flex:none}
.nrow .cnt{margin-left:auto;font-family:var(--mono);font-size:.66rem;
  color:var(--ink-3);font-variant-numeric:tabular-nums}
.nrow .chev{margin-left:auto;color:var(--ink-3);transition:transform .15s}
.nrow[aria-expanded="true"] .chev{transform:rotate(90deg)}
.nrow.on{background:var(--tint);color:var(--ink);font-weight:600}
.nrow.on .glyph{filter:none}
a.nrow:hover{text-decoration:none}
.nkids{list-style:none;margin:1px 0 6px;padding:0 0 0 8px;
  border-left:1px solid var(--line-2);margin-left:12px}
.nkids a{display:block;padding:5px 9px;font-size:.83rem;color:var(--ink-2);
  border-radius:4px;line-height:1.35;min-height:30px}
.nkids a:hover{background:var(--panel-2);color:var(--ink);text-decoration:none}
.nkids a[aria-current]{color:var(--ink);font-weight:600;background:var(--tint)}
.nkids .more{display:block;padding:5px 9px;font-size:.78rem;color:var(--ink-3);
  font-family:var(--mono)}
.sfoot{border-top:1px solid var(--line);padding:10px 14px;font-size:.76rem;
  color:var(--ink-3);display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.sfoot a{color:var(--ink-2)}

/* ============ topbar ============ */
.main{min-width:0;display:flex;flex-direction:column}
.top{position:sticky;top:0;z-index:12;display:flex;align-items:center;gap:8px;
  padding:9px 20px;background:color-mix(in srgb,var(--canvas) 90%,transparent);
  backdrop-filter:saturate(140%) blur(10px);border-bottom:1px solid var(--line-2)}
.top .ttl{font-family:var(--display);font-weight:600;font-size:.95rem;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:none}
.ib{display:grid;place-items:center;width:38px;height:38px;border-radius:var(--r);
  border:1px solid transparent;background:none;color:var(--ink-2);cursor:pointer}
.ib:hover{background:var(--panel);border-color:var(--line);color:var(--ink)}
.grow{flex:1}
#mburger,#msearch,#mtoc{display:none}

/* ============ trail (signature) ============ */
.crumbs{display:flex;align-items:center;gap:8px;flex-wrap:wrap;
  font-size:.78rem;color:var(--ink-2);margin:0 0 14px;line-height:1.4}
.crumbs a{color:var(--ink-2)}
.crumbs a:hover{color:var(--accent)}
.crumbs .seg{display:flex;align-items:center;gap:8px;white-space:nowrap;
  border:0;background:none;border-radius:0;overflow:visible}
.crumbs .lnk{padding:2px 0}
.crumbs .dash{width:16px;height:1px;background:var(--line);flex:none}
.crumbs .node{width:5px;height:5px;border-radius:50%;background:var(--line);
  flex:none}
.crumbs .seg:last-child .node{background:var(--accent)}
.crumbs .seg:last-child .lnk{color:var(--ink);font-weight:600}

/* ============ content ============ */
.wrap{display:grid;grid-template-columns:minmax(0,1fr) var(--rail);gap:36px;
  padding:26px 30px 100px;max-width:1240px;width:100%}
.wrap.solo{grid-template-columns:minmax(0,1fr);max-width:1000px}
.col{min-width:0;max-width:calc(var(--measure) + 4ch)}
.rail{position:sticky;top:64px;align-self:start;max-height:calc(100vh - 84px);
  overflow-y:auto;padding-bottom:20px}

.ahead{border-bottom:1px solid var(--line);padding-bottom:16px;margin-bottom:22px}
.ahead h1{font-size:2rem;line-height:1.12;margin:0 0 10px}
.meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:.72rem;
  border:1px solid var(--line);border-radius:var(--r);padding:3px 8px;
  color:var(--ink-2);background:var(--panel);white-space:nowrap}
.pill.kind{border-color:color-mix(in srgb,var(--accent) 45%,transparent);
  color:var(--accent);font-weight:600;letter-spacing:.04em;text-transform:uppercase;
  font-size:.66rem;font-family:var(--mono)}
.pill .glyph{width:8px;height:8px}
.lede{color:var(--ink-2);font-size:1.02rem;margin:12px 0 0;max-width:64ch}

/* ============ article body ============ */
.body{font-size:1rem}
.body>*{max-width:var(--measure)}
.body>.tw,.body>figure{max-width:100%}
.body h2{font-size:1.34rem;margin:2em 0 .5em;padding-bottom:.3em;
  border-bottom:1px solid var(--line-2);scroll-margin-top:80px}
.body h3{font-size:1.06rem;margin:1.6em 0 .35em;scroll-margin-top:80px}
.body h4{font-size:.94rem;margin:1.3em 0 .3em;color:var(--ink-2)}
.body p{margin:.8em 0}
.body ul,.body ol{margin:.7em 0;padding-left:1.35em}
.body li{margin:.25em 0}
.body li::marker{color:var(--ink-3)}
.body a[target]{color:var(--waypoint)}
.body a[target]::after{content:"\2197";font-size:.78em;opacity:.7;margin-left:.1em;
  text-decoration:none;display:inline-block}
.body blockquote{margin:1.2em 0;padding:12px 16px;border:1px solid var(--line);
  border-left:2px solid var(--amber);border-radius:0 var(--r) var(--r) 0;
  background:var(--panel);color:var(--ink-2)}
.body blockquote p:first-child{margin-top:0}
.body blockquote p:last-child{margin-bottom:0}
.body code{font-family:var(--mono);font-size:.86em;background:var(--panel);
  border:1px solid var(--line-2);border-radius:4px;padding:.08em .34em}
.body pre{overflow-x:auto;background:var(--panel);border:1px solid var(--line);
  border-radius:var(--r);padding:14px 16px}
.body pre code{background:none;border:0;padding:0}
.body hr{border:0;border-top:1px solid var(--line);margin:2em 0}
.body img{max-width:100%;height:auto}
.body img.ic{height:1.35em;width:auto;vertical-align:-.22em;margin:0 2px}
.body td img.ic,.body th img.ic{height:1.6em}
.body img.bl{display:block;max-height:210px;width:auto;margin:16px 0;padding:8px;
  background:var(--panel);border:1px solid var(--line-2);border-radius:var(--r)}
.body figure{margin:16px 0}
.body figcaption{font-size:.8rem;color:var(--ink-3);margin-top:6px;
  font-family:var(--mono)}
.imgmiss{display:inline-flex;align-items:center;gap:5px;font-family:var(--mono);
  font-size:.7rem;color:var(--ink-3);border:1px dashed var(--line);
  border-radius:4px;padding:1px 6px;vertical-align:middle}
.anchor{opacity:0;margin-left:.4em;font-size:.7em;color:var(--ink-3);
  border:0;background:none;cursor:pointer;padding:2px;vertical-align:middle;
  font-family:var(--mono)}
h2:hover .anchor,h3:hover .anchor,.anchor:focus-visible{opacity:1}

/* ============ tables ============ */
.tw{position:relative;margin:1.3em 0}
.tscroll{overflow-x:auto;border:1px solid var(--line);border-radius:var(--r);
  background:var(--panel)}
.tw table{border-collapse:separate;border-spacing:0;width:100%;font-size:.88rem;
  font-variant-numeric:tabular-nums}
.tw thead th{position:sticky;top:0;z-index:2;background:var(--panel-2);
  text-align:left;font-weight:600;font-size:.76rem;letter-spacing:.05em;
  text-transform:uppercase;color:var(--ink-2);white-space:nowrap;
  border-bottom:1px solid var(--line)}
.tw th,.tw td{padding:8px 12px;vertical-align:top;
  border-bottom:1px solid var(--line-2)}
.tw tbody tr:last-child td{border-bottom:0}
.tw tbody tr:nth-child(even){background:color-mix(in srgb,var(--ink) 2.5%,transparent)}
.tw tbody tr:hover,.tw tbody tr:focus-within{background:var(--tint)}
.tw td.num{text-align:right;font-family:var(--mono);font-size:.84rem}
.tw[data-stick] tbody th:first-child,.tw[data-stick] tbody td:first-child{
  position:sticky;left:0;background:var(--panel);z-index:1;
  border-right:1px solid var(--line)}
.tw[data-stick] thead th:first-child{position:sticky;left:0;z-index:3}
.tw::after{content:"";position:absolute;top:0;right:0;bottom:0;width:26px;
  pointer-events:none;border-radius:0 var(--r) var(--r) 0;opacity:0;
  transition:opacity .18s;
  background:linear-gradient(to right,transparent,color-mix(in srgb,var(--ink) 12%,transparent))}
.tw[data-over]::after{opacity:1}
.thint{display:none;align-items:center;gap:5px;font-family:var(--mono);
  font-size:.68rem;color:var(--ink-3);margin-top:5px}
.tw[data-over] .thint{display:flex}
.tcards{display:none}
@media (max-width:640px){
  .tw[data-cards] .tscroll{display:none}
  .tw[data-cards] .thint{display:none}
  .tw[data-cards] .tcards{display:grid;gap:8px}
  .tcard{border:1px solid var(--line);border-radius:var(--r);
    background:var(--panel);padding:10px 12px}
  .tcard .th{font-weight:600;font-size:.92rem;margin-bottom:6px;
    padding-bottom:6px;border-bottom:1px solid var(--line-2)}
  .tcard dl{display:grid;grid-template-columns:auto 1fr;gap:3px 12px;margin:0;
    font-size:.85rem}
  .tcard dt{color:var(--ink-3);font-size:.72rem;text-transform:uppercase;
    letter-spacing:.04em;padding-top:2px}
  .tcard dd{margin:0}
}

/* ============ rail / TOC ============ */
.rlabel{font-family:var(--mono);font-size:.66rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ink-3);margin:0 0 10px}
.toc{list-style:none;margin:0 0 26px;padding:0 0 0 14px;position:relative}
.toc::before{content:"";position:absolute;left:2px;top:8px;bottom:8px;width:1px;
  background:var(--line)}
.toc li{position:relative}
.toc a{display:block;padding:4px 0 4px 4px;font-size:.82rem;color:var(--ink-2);
  line-height:1.35;min-height:28px}
.toc a::before{content:"";position:absolute;left:-15px;top:11px;width:5px;
  height:5px;border-radius:50%;background:var(--canvas);
  border:1px solid var(--line)}
.toc a:hover{color:var(--ink);text-decoration:none}
.toc a:hover::before{border-color:var(--accent)}
.toc a.on{color:var(--ink);font-weight:600}
.toc a.on::before{background:var(--accent);border-color:var(--accent)}
.toc .l3{padding-left:14px;font-size:.79rem}
.toc .l3::before{left:-15px;width:4px;height:4px;top:12px}
.rel{list-style:none;margin:0;padding:0;display:grid;gap:2px}
.rel a{display:flex;gap:8px;align-items:center;padding:6px 8px;font-size:.83rem;
  color:var(--ink-2);border-radius:4px;min-height:32px}
.rel a:hover{background:var(--panel);color:var(--ink);text-decoration:none}
.rel .glyph{width:8px;height:8px}

/* ============ cards / lists ============ */
.grid{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}
.list{display:grid;gap:2px}
.card{display:block;padding:13px 14px;border:1px solid var(--line);
  border-radius:var(--r);background:var(--panel);color:inherit}
.card:hover{border-color:var(--accent);text-decoration:none;box-shadow:var(--shadow)}
.card .ct{font-family:var(--display);font-weight:600;font-size:.98rem;
  display:flex;align-items:center;gap:8px;line-height:1.25}
.card .cd{color:var(--ink-2);font-size:.83rem;margin-top:5px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
  overflow:hidden}
.card .cs{font-family:var(--mono);font-size:.68rem;color:var(--ink-3);
  margin-top:8px;display:flex;gap:8px;align-items:center}
.row{display:flex;gap:11px;align-items:flex-start;padding:9px 10px;
  border-radius:var(--r);color:inherit;border:1px solid transparent;min-height:44px}
.row:hover{background:var(--panel);border-color:var(--line);text-decoration:none}
.row .rt{font-weight:600;font-size:.92rem;line-height:1.3}
.row .rd{color:var(--ink-2);font-size:.82rem;line-height:1.4;
  display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;
  overflow:hidden}
.row .rk{margin-left:auto;font-family:var(--mono);font-size:.68rem;
  color:var(--ink-3);white-space:nowrap;padding-top:2px}
.thumb{width:34px;height:34px;flex:none;border-radius:var(--r);
  border:1px solid var(--line-2);background:var(--panel-2);display:grid;
  place-items:center;overflow:hidden}
.thumb img{max-width:26px;max-height:26px;width:auto;height:auto;
  image-rendering:auto}
.thumb .glyph{width:11px;height:11px}
.grid .thumb{width:30px;height:30px}
.alpha{font-family:var(--mono);font-size:.72rem;color:var(--ink-3);
  letter-spacing:.1em;margin:20px 0 6px;padding-bottom:5px;
  border-bottom:1px solid var(--line-2)}
.alpha:first-child{margin-top:6px}

/* ============ controls ============ */
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 16px;
  padding-bottom:14px;border-bottom:1px solid var(--line-2)}
.field{position:relative;flex:1;min-width:180px}
.field input{width:100%;padding:9px 12px 9px 32px;border:1px solid var(--line);
  background:var(--panel);color:var(--ink);border-radius:var(--r);
  font-size:.88rem;font-family:var(--sans);min-height:40px}
.field input::placeholder{color:var(--ink-3)}
.field svg{position:absolute;left:10px;top:50%;transform:translateY(-50%);
  color:var(--ink-3)}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-size:.78rem;padding:6px 11px;border:1px solid var(--line);
  border-radius:var(--r);background:var(--panel);color:var(--ink-2);
  cursor:pointer;min-height:34px;white-space:nowrap;display:inline-flex;
  align-items:center}
.chip:hover{border-color:var(--accent);color:var(--ink)}
.chip[aria-pressed="true"]{background:var(--tint);color:var(--ink);
  border-color:color-mix(in srgb,var(--accent) 50%,transparent);font-weight:600}
.chip .n{font-family:var(--mono);font-size:.68rem;color:var(--ink-3);
  margin-left:5px}
.seg{display:flex;border:1px solid var(--line);border-radius:var(--r);
  overflow:hidden;background:var(--panel)}
.seg button{padding:6px 11px;border:0;background:none;font-size:.78rem;
  color:var(--ink-2);cursor:pointer;min-height:34px;white-space:nowrap}
.seg button+button{border-left:1px solid var(--line)}
.seg button[aria-pressed="true"]{background:var(--tint);color:var(--ink);
  font-weight:600}

/* ============ empty states ============ */
.empty{border:1px dashed var(--line);border-radius:var(--r);padding:26px 22px;
  text-align:left;color:var(--ink-2);background:var(--panel-2)}
.empty b{display:block;font-family:var(--display);font-size:1.02rem;
  color:var(--ink);margin-bottom:5px}
.empty .acts{margin-top:12px;display:flex;gap:8px;flex-wrap:wrap}

/* ============ home ============ */
.home{padding:30px 30px 100px;max-width:1080px;width:100%}
.hhead{display:flex;align-items:flex-start;gap:14px;margin-bottom:6px}
.hhead h1{font-size:1.9rem;margin:0;line-height:1.1}
.hsub{color:var(--ink-2);margin:6px 0 22px;max-width:60ch}
.hsearch{display:flex;align-items:center;gap:10px;width:100%;padding:14px 16px;
  border:1px solid var(--line);border-radius:var(--r);background:var(--panel);
  color:var(--ink-3);cursor:pointer;text-align:left;font-size:1rem;
  box-shadow:var(--shadow);min-height:52px;white-space:nowrap;overflow:hidden}
.hsearch:hover{border-color:var(--glacier)}
.hsearch span:not(.k){overflow:hidden;text-overflow:ellipsis}
.hsearch .k{margin-left:auto;font-family:var(--mono);font-size:.7rem;
  border:1px solid var(--line);border-radius:4px;padding:2px 6px;
  white-space:nowrap}
.startline{display:flex;align-items:center;gap:10px;margin:12px 0 30px;
  padding:12px 14px;border:1px solid var(--line);border-left:2px solid var(--amber);
  border-radius:0 var(--r) var(--r) 0;background:var(--panel);font-size:.9rem}
.startline b{font-weight:600}
.startline a{margin-left:auto;white-space:nowrap;font-size:.86rem}
.hsec{margin:34px 0 12px;display:flex;align-items:baseline;gap:10px}
.hsec h2{font-size:.72rem;font-family:var(--mono);font-weight:600;
  letter-spacing:.16em;text-transform:uppercase;color:var(--ink-3);margin:0}
.hsec .rule{flex:1;height:1px;background:var(--line-2)}
.cgrid{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(250px,1fr))}
.ccard{display:flex;flex-direction:column;padding:15px 16px;
  border:1px solid var(--line);border-radius:var(--r);background:var(--panel);
  color:inherit;min-height:112px}
.ccard:hover{border-color:var(--accent);text-decoration:none;box-shadow:var(--shadow)}
.ccard .h{display:flex;align-items:center;gap:9px;font-family:var(--display);
  font-weight:600;font-size:1.02rem}
.ccard p{margin:7px 0 0;font-size:.86rem;color:var(--ink-2);line-height:1.45}
.ccard .f{margin-top:auto;padding-top:10px;font-family:var(--mono);
  font-size:.68rem;color:var(--ink-3)}
.quick{display:flex;flex-wrap:wrap;gap:6px}
.qa{display:inline-flex;align-items:center;gap:7px;padding:7px 11px;
  border:1px solid var(--line);border-radius:var(--r);background:var(--panel);
  font-size:.85rem;color:var(--ink);min-height:36px;white-space:nowrap}
.qa:hover{border-color:var(--accent);text-decoration:none}
.hfoot{margin-top:44px;padding-top:16px;border-top:1px solid var(--line);
  color:var(--ink-3);font-size:.79rem;max-width:70ch}
.hfoot a{color:var(--ink-2)}

/* ============ search palette ============ */
.scrim{position:fixed;inset:0;background:rgba(14,24,32,.5);z-index:40;
  display:none}
.scrim.on{display:block}
.pal{position:fixed;z-index:50;left:50%;top:64px;transform:translateX(-50%);
  width:min(680px,calc(100vw - 24px));max-height:min(620px,calc(100vh - 96px));
  background:var(--panel);border:1px solid var(--line);border-radius:8px;
  box-shadow:0 24px 60px -20px rgba(14,24,32,.5);display:none;
  flex-direction:column;overflow:hidden}
.pal.on{display:flex}
.palin{display:flex;align-items:center;gap:10px;padding:12px 14px;
  border-bottom:1px solid var(--line)}
.palin input{flex:1;border:0;background:none;color:var(--ink);font-size:1.02rem;
  font-family:var(--sans);outline:none;min-width:0}
.palin input::placeholder{color:var(--ink-3)}
.palin .esc{font-family:var(--mono);font-size:.68rem;color:var(--ink-3);
  border:1px solid var(--line);border-radius:4px;padding:2px 6px}
.palout{overflow-y:auto;padding:6px;overscroll-behavior:contain}
.pgroup{font-family:var(--mono);font-size:.66rem;letter-spacing:.13em;
  text-transform:uppercase;color:var(--ink-3);padding:10px 10px 5px;
  display:flex;align-items:center;gap:7px}
.pres{display:flex;gap:10px;align-items:center;padding:8px 10px;border-radius:var(--r);
  color:inherit;min-height:46px}
.pres:hover{text-decoration:none}
.pres[data-sel="1"]{background:var(--tint);outline:1px solid
  color-mix(in srgb,var(--accent) 40%,transparent)}
.pres .pt{font-weight:600;font-size:.92rem;line-height:1.25}
.pres .px{font-size:.79rem;color:var(--ink-2);line-height:1.35;
  display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;
  overflow:hidden}
.pres .pk{margin-left:auto;font-family:var(--mono);font-size:.66rem;
  color:var(--ink-3);white-space:nowrap}
.palfoot{border-top:1px solid var(--line);padding:8px 14px;display:flex;gap:14px;
  font-family:var(--mono);font-size:.68rem;color:var(--ink-3);flex-wrap:wrap}
.palempty{padding:26px 16px;color:var(--ink-2);font-size:.9rem}
.palempty b{display:block;color:var(--ink);font-family:var(--display);
  font-size:1rem;margin-bottom:4px}
mark{background:color-mix(in srgb,var(--amber) 34%,transparent);color:inherit;
  border-radius:2px;padding:0 1px}

/* ============ mobile sheet ============ */
.sheet{position:fixed;left:0;right:0;bottom:0;z-index:50;background:var(--panel);
  border-top:1px solid var(--line);border-radius:10px 10px 0 0;
  max-height:70vh;overflow-y:auto;padding:16px 18px 30px;display:none;
  box-shadow:0 -12px 40px -20px rgba(0,0,0,.5)}
.sheet.on{display:block}

/* ============ responsive ============ */
@media (max-width:1180px){
  .wrap{grid-template-columns:minmax(0,1fr);gap:0}
  .rail{display:none}
  .hastoc #mtoc{display:grid}
}
@media (max-width:900px){
  .app{grid-template-columns:minmax(0,1fr)}
  .side{position:fixed;top:0;left:0;width:min(300px,86vw);z-index:45;
    transform:translateX(-100%)}
  html[data-side="on"] .side{transform:none;box-shadow:0 0 50px rgba(0,0,0,.35)}
  html[data-side="off"] .app{grid-template-columns:minmax(0,1fr)}
  #mburger,#msearch{display:grid}
  #sidetoggle{display:none}
  .top .ttl{display:block}
  .wrap,.home{padding-left:16px;padding-right:16px}
  .ahead h1{font-size:1.6rem}
  .hhead h1{font-size:1.5rem}
  .pal{top:0;left:0;transform:none;width:100vw;max-height:100vh;height:100vh;
    border-radius:0;border:0}
}
@media print{
  .side,.top,.rail,.pal,.scrim{display:none!important}
  .wrap{grid-template-columns:1fr;padding:0}
}
</style>

<a class="skip" href="#main">Skip to content</a>

<div class="app">
  <aside class="side" id="side" aria-label="Sections">
    <a class="brand" href="#/">
      <span class="bm" aria-hidden="true"><i></i></span>
      <span class="bt"><b>WalkScape</b><span class="bs">Companion</span></span>
    </a>
    <button class="sbtn" id="opensearch">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg>
      Search everything
      <span class="k">/</span>
    </button>
    <nav class="nav" id="nav" aria-label="Browse"></nav>
    <div class="sfoot">
      <a href="https://wiki.walkscape.app" target="_blank" rel="noopener">Official wiki</a>
      <span aria-hidden="true">·</span>
      <span id="pcount"></span>
    </div>
  </aside>

  <div class="main">
    <header class="top">
      <button class="ib" id="mburger" aria-label="Open menu" aria-expanded="false" aria-controls="side">
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
      </button>
      <button class="ib" id="sidetoggle" aria-label="Collapse sidebar" aria-expanded="true" aria-controls="side">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></svg>
      </button>
      <span class="ttl" id="mtitle">WalkScape Companion</span>
      <span class="grow"></span>
      <button class="ib" id="mtoc" aria-label="On this page" aria-expanded="false">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 6h10M4 12h16M4 18h7"/></svg>
      </button>
      <button class="ib" id="msearch" aria-label="Search">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg>
      </button>
      <button class="ib" id="themebtn" aria-label="Switch theme">
        <svg id="ic-theme" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.6v2.2M12 19.2v2.2M3.6 12H1.4M22.6 12h-2.2M5.6 5.6l1.6 1.6M16.8 16.8l1.6 1.6M18.4 5.6l-1.6 1.6M7.2 16.8l-1.6 1.6"/></svg>
      </button>
    </header>
    <main id="main" tabindex="-1"></main>
  </div>
</div>

<div class="scrim" id="scrim"></div>
<div class="pal" id="pal" role="dialog" aria-modal="true" aria-label="Search">
  <div class="palin">
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" style="color:var(--ink-3)"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg>
    <input id="palq" type="text" autocomplete="off" spellcheck="false" role="combobox"
      aria-expanded="true" aria-controls="palout" aria-autocomplete="list"
      placeholder="Search skills, items, activities, locations…">
    <span class="esc">Esc</span>
  </div>
  <div class="palout" id="palout" role="listbox" aria-label="Search results"></div>
  <div class="palfoot">
    <span>&#8593;&#8595; move</span><span>&#8629; open</span><span>Esc close</span>
    <span class="grow"></span><span id="palcount"></span>
  </div>
</div>
<div class="vh" role="status" aria-live="polite" id="live"></div>
<div class="sheet" id="sheet" role="dialog" aria-modal="true" aria-label="On this page"></div>

<script type="application/json" id="data">__DATA__</script>
<script>
"use strict";
var DATA = JSON.parse(document.getElementById('data').textContent);
var P = DATA.pages, SEC = DATA.sections, SUBS = DATA.subs || {},
    ORDER = DATA.order, IMG = DATA.images || {};
var main = document.getElementById('main'),
    nav = document.getElementById('nav'),
    live = document.getElementById('live');

/* ---------- escaping: one function, used everywhere ---------- */
var EMAP = {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'};
function esc(s){ return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){ return EMAP[c]; }); }
function attr(s){ return esc(s); }
function hrefFor(slug){ return '#/' + encodeURIComponent(slug); }

/* ---------- section identity ---------- */
var META = {
  'Start Here':      {shape:'dot',     accent:'--amber',    blurb:'What the game is, how to begin, and the answers new walkers need first.'},
  'Skills':          {shape:'diamond', accent:'--glacier',  blurb:'The trainable skills, what they unlock and how experience is earned.'},
  'Activities':      {shape:'tri',     accent:'--amber',    blurb:'Everything you can set your character to do, and where each one is available.'},
  'Items & Equipment':{shape:'square', accent:'--waypoint', blurb:'Tools, gear, materials, food and collectibles, with their stats and sources.'},
  'Locations':       {shape:'circle',  accent:'--good',     blurb:'Regions, cities and points of interest across Arenum.'},
  'Game Systems':    {shape:'ring',    accent:'--ink-2',    blurb:'Attributes, progression, inventory and the rules underneath the numbers.'},
  'Guides':          {shape:'flag',    accent:'--waypoint', blurb:'Practical walkthroughs written for a specific goal.'},
  'Glossary':        {shape:'bar',     accent:'--ink-2',    blurb:'Item keywords and wiki terms explained in one line each.'}
};
function metaOf(s){ return META[s] || {shape:'dot', accent:'--ink-2', blurb:''}; }
function accentOf(s){ return 'var(' + metaOf(s).accent + ')'; }

function glyph(section, size){
  var m = metaOf(section), c = 'var(' + m.accent + ')', z = size || 9, s = m.shape;
  var g;
  if (s === 'diamond') g = '<rect x="3" y="3" width="6" height="6" transform="rotate(45 6 6)" fill="' + c + '"/>';
  else if (s === 'square') g = '<rect x="2" y="2" width="8" height="8" rx="1" fill="' + c + '"/>';
  else if (s === 'circle') g = '<circle cx="6" cy="6" r="4" fill="' + c + '"/>';
  else if (s === 'ring') g = '<circle cx="6" cy="6" r="3.6" fill="none" stroke="' + c + '" stroke-width="2"/>';
  else if (s === 'tri') g = '<path d="M6 1.6 10.6 10H1.4Z" fill="' + c + '"/>';
  else if (s === 'flag') g = '<path d="M3 1v10" stroke="' + c + '" stroke-width="1.8" stroke-linecap="round"/><path d="M3.8 2h5.4l-1.5 2.2 1.5 2.2H3.8Z" fill="' + c + '"/>';
  else if (s === 'bar') g = '<rect x="1.5" y="4.5" width="9" height="3" rx="1.5" fill="' + c + '"/>';
  else g = '<circle cx="6" cy="6" r="3" fill="' + c + '"/>';
  return '<svg class="glyph" width="' + z + '" height="' + z + '" viewBox="0 0 12 12" aria-hidden="true">' + g + '</svg>';
}

/* ---------- thumbnails ---------- */
function thumb(slug){
  var p = P[slug], uri = p && p.icon ? IMG[p.icon] : null;
  if (uri) return '<span class="thumb"><img src="' + attr(uri) + '" alt="" loading="lazy"></span>';
  return '<span class="thumb">' + glyph(p ? p.section : '', 11) + '</span>';
}

/* ---------- search index ---------- */
var IDX = Object.keys(P).map(function(slug){
  var p = P[slug];
  return {slug:slug, title:p.title, lc:p.title.toLowerCase(), section:p.section,
          sub:p.sub || '', text:(p.text || ''), tlc:(p.text || '').toLowerCase()};
});
IDX.sort(function(a, b){ return a.lc < b.lc ? -1 : 1; });

function query(term, limit){
  var t = term.trim().toLowerCase();
  if (!t) return [];
  var out = [];
  for (var i = 0; i < IDX.length; i++){
    var e = IDX[i], s = 0;
    if (e.lc === t) s = 100;
    else if (e.lc.indexOf(t) === 0) s = 70;
    else if (e.lc.indexOf(' ' + t) > -1) s = 55;
    else if (e.lc.indexOf(t) > -1) s = 40;
    else if (e.tlc.indexOf(t) > -1) s = 12;
    if (s){ if (e.sub === 'Index') s -= 6; out.push([s, e]); }
  }
  out.sort(function(a, b){ return b[0] - a[0] || (a[1].lc < b[1].lc ? -1 : 1); });
  return out.slice(0, limit || 40).map(function(x){ return x[1]; });
}
function highlight(text, term){
  var t = term.trim();
  if (!t) return esc(text);
  var re = new RegExp('(' + t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig');
  return esc(text).replace(re, '<mark>$1</mark>');
}

/* ---------- recents (localStorage only) ---------- */
function lsGet(k, d){ try { return JSON.parse(localStorage.getItem(k)) || d; } catch(e){ return d; } }
function lsSet(k, v){ try { localStorage.setItem(k, JSON.stringify(v)); } catch(e){} }
function pushRecent(slug){
  var r = lsGet('ws-recent', []).filter(function(x){ return x !== slug && P[x]; });
  r.unshift(slug); lsSet('ws-recent', r.slice(0, 10));
}
function pushRecentQuery(q){
  if (q.length < 2) return;
  var r = lsGet('ws-recentq', []).filter(function(x){ return x.toLowerCase() !== q.toLowerCase(); });
  r.unshift(q); lsSet('ws-recentq', r.slice(0, 5));
}

/* ================= Sidebar ================= */
var openSection = null;
function Sidebar(active){
  var h = '<a class="nrow' + (active === '@home' ? ' on' : '') + '" href="#/" style="--accent:var(--glacier)">' +
    '<svg class="glyph" width="9" height="9" viewBox="0 0 12 12" aria-hidden="true"><path d="M1.5 6 6 2l4.5 4v4.5h-9Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>Home</a>';
  ORDER.forEach(function(s){
    var slugs = SEC[s] || [], open = openSection === s, id = 'ns-' + s.replace(/\W/g, '');
    h += '<div style="--accent:' + accentOf(s) + '">' +
      '<button class="nrow' + (active === s && !open ? ' on' : '') + '" aria-expanded="' + open + '" aria-controls="' + id + '" data-sec="' + attr(s) + '">' +
      glyph(s) + esc(s) +
      '<svg class="chev" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m9 5 7 7-7 7"/></svg>' +
      '</button>';
    if (open){
      var shown = slugs.slice(0, 40);
      h += '<ul class="nkids" id="' + id + '">' +
        '<li><a href="#/c/' + encodeURIComponent(s) + '"' + (active === s ? ' aria-current="page"' : '') + '>All ' + esc(s) + ' &middot; ' + slugs.length + '</a></li>' +
        shown.map(function(x){
          return '<li><a href="' + hrefFor(x) + '"' + (active === x ? ' aria-current="page"' : '') + '>' + esc(P[x].title) + '</a></li>';
        }).join('') +
        (slugs.length > 40 ? '<li><a class="more" href="#/c/' + encodeURIComponent(s) + '">Browse all ' + slugs.length + ' &rarr;</a></li>' : '') +
        '</ul>';
    } else {
      h += '<ul class="nkids" id="' + id + '" hidden></ul>';
    }
    h += '</div>';
  });
  nav.innerHTML = h;
  var cur = nav.querySelector('[aria-current]');
  if (cur){
    var top = cur.offsetTop, h2 = nav.clientHeight;
    if (top > nav.scrollTop + h2 - 40 || top < nav.scrollTop) nav.scrollTop = Math.max(0, top - h2 / 2);
  }
}
nav.addEventListener('click', function(e){
  var b = e.target.closest('button[data-sec]');
  if (!b) return;
  var s = b.getAttribute('data-sec');
  openSection = (openSection === s) ? null : s;
  Sidebar(currentActive);
  if (openSection === s){
    var nb = nav.querySelector('button[data-sec="' + s.replace(/"/g, '\\"') + '"]');
    if (nb) nb.focus();
  }
});
var currentActive = '@home';

/* ================= Breadcrumbs (the trail) ================= */
function Breadcrumbs(items){
  return '<nav class="crumbs" aria-label="Breadcrumb">' + items.map(function(it, i){
    var inner = it.href ? '<a class="lnk" href="' + attr(it.href) + '">' + esc(it.label) + '</a>'
                        : '<span class="lnk" aria-current="page">' + esc(it.label) + '</span>';
    return '<span class="seg">' + (i ? '<span class="dash"></span>' : '') +
      '<span class="node"></span>' + inner + '</span>';
  }).join('') + '</nav>';
}

/* ================= Entry cards / rows ================= */
function EntryCard(slug, term){
  var p = P[slug];
  return '<a class="card" href="' + hrefFor(slug) + '">' +
    '<span class="ct">' + thumb(slug) + '<span>' + (term ? highlight(p.title, term) : esc(p.title)) + '</span></span>' +
    '<span class="cd">' + esc((p.text || '').slice(0, 110)) + '</span>' +
    '<span class="cs">' + glyph(p.section, 8) + esc(p.sub || p.section) + '</span></a>';
}
function EntryRow(slug, term, showSection){
  var p = P[slug];
  return '<a class="row" href="' + hrefFor(slug) + '">' + thumb(slug) +
    '<span style="min-width:0"><span class="rt">' + (term ? highlight(p.title, term) : esc(p.title)) + '</span>' +
    '<span class="rd">' + esc((p.text || '').slice(0, 120)) + '</span></span>' +
    '<span class="rk">' + esc(showSection ? p.section : (p.sub || '')) + '</span></a>';
}
function EmptyState(title, body, actions){
  return '<div class="empty"><b>' + esc(title) + '</b>' + esc(body) +
    (actions ? '<div class="acts">' + actions + '</div>' : '') + '</div>';
}

/* ================= Home ================= */
function CategoryCard(s){
  var slugs = SEC[s] || [], m = metaOf(s);
  return '<a class="ccard" href="#/c/' + encodeURIComponent(s) + '" style="--accent:' + accentOf(s) + '">' +
    '<span class="h">' + glyph(s, 11) + esc(s) + '</span>' +
    '<p>' + esc(m.blurb) + '</p>' +
    '<span class="f">' + slugs.length + ' entries' +
    ((SUBS[s] || []).length > 1 ? ' &middot; ' + esc((SUBS[s] || []).slice(0, 3).join(', ')) : '') +
    '</span></a>';
}
var QUICK = ['Skills', 'Attributes', 'Recipes', 'Map_of_Arenum', 'Chests',
             'Work_Efficiency', 'Glossary', 'Toolbelt'];
function renderHome(){
  currentActive = '@home';
  shownSlug = null; catState.section = null;
  document.getElementById('mtitle').textContent = 'WalkScape Companion';
  document.documentElement.classList.remove('hastoc');
  var start = P['Tutorial'] ? 'Tutorial' : (SEC['Start Here'] || [])[0];
  var quick = QUICK.filter(function(s){ return P[s]; }).slice(0, 8);
  var recents = lsGet('ws-recent', []).filter(function(s){ return P[s]; }).slice(0, 6);

  var h = '<div class="home">' +
    '<div class="hhead"><div><h1>What do you want to look up?</h1>' +
    '<p class="hsub">An offline field companion for WalkScape &mdash; ' + DATA.count +
    ' pages from the community wiki, reorganised so you can find one while you are walking.</p></div></div>' +
    '<button class="hsearch" id="homesearch">' +
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg>' +
    '<span>Search skills, items, activities, locations&hellip;</span><span class="k">Ctrl K</span></button>';

  if (start) h += '<div class="startline"><b>New to WalkScape?</b> ' +
    '<span style="color:var(--ink-2)">Begin with the walkthrough.</span>' +
    '<a href="' + hrefFor(start) + '">Start here &rarr;</a></div>';

  h += '<div class="hsec"><h2>Browse by category</h2><span class="rule"></span></div>' +
    '<div class="cgrid">' + ORDER.map(CategoryCard).join('') + '</div>';

  if (quick.length) h += '<div class="hsec"><h2>Quick references</h2><span class="rule"></span></div>' +
    '<div class="quick">' + quick.map(function(s){
      return '<a class="qa" href="' + hrefFor(s) + '" style="--accent:' + accentOf(P[s].section) + '">' +
        glyph(P[s].section, 9) + esc(P[s].title) + '</a>';
    }).join('') + '</div>';

  if (recents.length) h += '<div class="hsec"><h2>Recently viewed</h2><span class="rule"></span></div>' +
    '<div class="quick">' + recents.map(function(s){
      return '<a class="qa" href="' + hrefFor(s) + '" style="--accent:' + accentOf(P[s].section) + '">' +
        glyph(P[s].section, 9) + esc(P[s].title) + '</a>';
    }).join('') + '</div>';

  h += '<div class="hfoot">Unofficial companion. All game content belongs to the WalkScape team and the ' +
    '<a href="https://wiki.walkscape.app" target="_blank" rel="noopener">community wiki</a> contributors; ' +
    'this app only reorganises it for faster reading offline. Recently viewed pages are stored on this device only.</div></div>';

  main.innerHTML = h;
  document.getElementById('homesearch').onclick = function(){ openPalette(); };
  Sidebar(currentActive);
}

/* ================= Category page ================= */
var catState = {sub:'All', sort:'rec', view:null, q:''};
function renderCategory(sec){
  if (!SEC[sec]) return renderMissing(sec);
  currentActive = sec;
  shownSlug = null;
  document.getElementById('mtitle').textContent = sec;
  document.documentElement.classList.remove('hastoc');
  if (catState.section !== sec){
    catState = {section:sec, sub:'All', sort:'rec', q:'',
      view:(sec === 'Items & Equipment' || sec === 'Locations') ? 'grid' : 'list'};
  }
  if (openSection !== sec){ openSection = sec; }
  paintCategory();
  Sidebar(currentActive);
}
function paintCategory(){
  var sec = catState.section, m = metaOf(sec), subs = SUBS[sec] || [];
  var all = (SEC[sec] || []).slice();
  var q = catState.q.trim().toLowerCase();
  var list = all.filter(function(s){
    if (catState.sub !== 'All' && P[s].sub !== catState.sub) return false;
    if (q && P[s].title.toLowerCase().indexOf(q) < 0 &&
        (P[s].text || '').toLowerCase().indexOf(q) < 0) return false;
    return true;
  });
  if (catState.sort === 'rec'){
    var rank = {};
    subs.forEach(function(x, i){ rank[x] = i; });
    list.sort(function(a, b){
      var pa = P[a], pb = P[b];
      var ia = (pa.sub === 'Index' ? 90 : (rank[pa.sub] == null ? 50 : rank[pa.sub]));
      var ib = (pb.sub === 'Index' ? 90 : (rank[pb.sub] == null ? 50 : rank[pb.sub]));
      return ia - ib || (pa.title.toLowerCase() < pb.title.toLowerCase() ? -1 : 1);
    });
  } else {
    list.sort(function(a, b){ return P[a].title.toLowerCase() < P[b].title.toLowerCase() ? -1 : 1; });
  }

  var h = '<div class="wrap solo" style="--accent:' + accentOf(sec) + '">' +
    '<div class="col" style="max-width:none">' +
    Breadcrumbs([{label:'Home', href:'#/'}, {label:sec}]) +
    '<div class="ahead"><h1>' + glyph(sec, 16) + ' ' + esc(sec) + '</h1>' +
    '<p class="lede">' + esc(m.blurb) + '</p></div>';

  h += '<div class="bar">' +
    '<span class="field"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg>' +
    '<input id="catq" type="search" value="' + attr(catState.q) + '" placeholder="Filter within ' + attr(sec) + '&hellip;" aria-label="Filter within ' + attr(sec) + '"></span>' +
    '<span class="seg" role="group" aria-label="Sort">' +
    '<button data-sort="rec" aria-pressed="' + (catState.sort === 'rec') + '">Recommended</button>' +
    '<button data-sort="az" aria-pressed="' + (catState.sort === 'az') + '">A&ndash;Z</button></span>' +
    '<span class="seg" role="group" aria-label="Layout">' +
    '<button data-view="list" aria-pressed="' + (catState.view === 'list') + '" aria-label="Compact list">List</button>' +
    '<button data-view="grid" aria-pressed="' + (catState.view === 'grid') + '" aria-label="Grid">Grid</button></span>' +
    '</div>';

  if (subs.length > 1){
    h += '<div class="chips" style="margin:-4px 0 16px" role="group" aria-label="Filter by type">' +
      '<button class="chip" data-sub="All" aria-pressed="' + (catState.sub === 'All') + '">All<span class="n">' + all.length + '</span></button>' +
      subs.map(function(x){
        var n = all.filter(function(s){ return P[s].sub === x; }).length;
        return '<button class="chip" data-sub="' + attr(x) + '" aria-pressed="' + (catState.sub === x) + '">' +
          esc(x) + '<span class="n">' + n + '</span></button>';
      }).join('') + '</div>';
  }

  if (!list.length){
    h += EmptyState('Nothing matches that filter',
      catState.q ? 'No entries in ' + sec + ' contain \u201c' + catState.q + '\u201d. Try a shorter word, or search across every category.'
                 : 'This subcategory has no entries yet.',
      '<button class="chip" data-reset="1">Clear filters</button>' +
      '<button class="chip" data-openpal="1">Search everything</button>');
  } else if (catState.view === 'grid'){
    h += '<div class="grid">' + list.map(function(s){ return EntryCard(s, catState.q); }).join('') + '</div>';
  } else if (catState.sort === 'az' && list.length > 24){
    var letter = '';
    h += '<div class="list">';
    list.forEach(function(s){
      var L = P[s].title.charAt(0).toUpperCase();
      if (!/[A-Z]/.test(L)) L = '#';
      if (L !== letter){ letter = L; h += '<div class="alpha">' + esc(L) + '</div>'; }
      h += EntryRow(s, catState.q, false);
    });
    h += '</div>';
  } else {
    h += '<div class="list">' + list.map(function(s){ return EntryRow(s, catState.q, false); }).join('') + '</div>';
  }

  h += '<p style="font-family:var(--mono);font-size:.72rem;color:var(--ink-3);margin-top:20px">' +
    list.length + ' of ' + all.length + ' entries</p></div></div>';
  main.innerHTML = h;

  var qi = document.getElementById('catq');
  qi.addEventListener('input', function(){
    catState.q = qi.value;
    var pos = qi.selectionStart;
    paintCategory();
    var n = document.getElementById('catq');
    n.focus(); try { n.setSelectionRange(pos, pos); } catch(e){}
  });
}
/* one delegated listener for every category control, for the life of the app */
main.addEventListener('click', function(e){
  var t = e.target.closest('[data-sub],[data-sort],[data-view],[data-reset],[data-openpal]');
  if (!t || !catState.section || !document.getElementById('catq')) return;
  if (t.dataset.openpal){ openPalette(); return; }
  if (t.dataset.sub) catState.sub = t.dataset.sub;
  else if (t.dataset.sort) catState.sort = t.dataset.sort;
  else if (t.dataset.view) catState.view = t.dataset.view;
  else if (t.dataset.reset){ catState.q = ''; catState.sub = 'All'; }
  paintCategory();
});

/* ================= Article ================= */
var shownSlug = null;
function renderPage(slug){
  var p = P[slug];
  if (!p) return renderMissing(slug);
  currentActive = slug;
  shownSlug = slug;
  catState.section = null;
  openSection = p.section;
  pushRecent(slug);
  document.getElementById('mtitle').textContent = p.title;
  var sec = p.section, sibs = SEC[sec] || [], pos = sibs.indexOf(slug);

  var tags = (p.tags || []).filter(function(t){ return t && t !== p.sub; }).slice(0, 4);
  var h = '<div class="wrap" style="--accent:' + accentOf(sec) + '"><article class="col">' +
    Breadcrumbs([{label:'Home', href:'#/'},
                 {label:sec, href:'#/c/' + encodeURIComponent(sec)},
                 {label:p.title}]) +
    '<header class="ahead"><h1>' + esc(p.title) + '</h1><div class="meta">' +
    '<span class="pill kind">' + glyph(sec, 8) + esc(p.sub && p.sub !== 'Reference' ? p.sub : sec) + '</span>' +
    tags.map(function(t){ return '<span class="pill">' + esc(t) + '</span>'; }).join('') +
    '</div></header>' +
    '<div class="body" id="body">' + p.html + '</div>';

  h += '<div class="hsec" style="margin-top:40px"><h2>Continue</h2><span class="rule"></span></div>' +
    '<div class="quick">' +
    '<a class="qa" href="#/c/' + encodeURIComponent(sec) + '">&larr; All ' + esc(sec) + '</a>' +
    (pos > 0 ? '<a class="qa" href="' + hrefFor(sibs[pos - 1]) + '">' + esc(P[sibs[pos - 1]].title) + '</a>' : '') +
    (pos > -1 && pos < sibs.length - 1 ? '<a class="qa" href="' + hrefFor(sibs[pos + 1]) + '">' + esc(P[sibs[pos + 1]].title) + '</a>' : '') +
    '<a class="qa" href="' + attr(p.url || 'https://wiki.walkscape.app') + '" target="_blank" rel="noopener">Original wiki page</a>' +
    '</div>' +
    (pos > -1 ? '<p style="font-family:var(--mono);font-size:.72rem;color:var(--ink-3);margin-top:12px">' +
      (pos + 1) + ' of ' + sibs.length + ' in ' + esc(sec) + '</p>' : '') +
    '</article><aside class="rail" id="rail"></aside></div>';

  main.innerHTML = h;
  enhance(document.getElementById('body'));
  buildRail(slug);
  Sidebar(currentActive);
  window.scrollTo(0, 0);
}

function renderMissing(what){
  currentActive = null;
  main.innerHTML = '<div class="wrap solo"><div class="col">' +
    Breadcrumbs([{label:'Home', href:'#/'}, {label:'Not found'}]) +
    EmptyState('That page is not in this companion',
      'We could not resolve \u201c' + what + '\u201d. It may exist on the official wiki, or the link may be out of date.',
      '<a class="chip" href="#/">Back to home</a>' +
      '<a class="chip" href="https://wiki.walkscape.app/wiki/' + encodeURIComponent(what) +
      '" target="_blank" rel="noopener">Try the official wiki</a>') +
    '</div></div>';
  Sidebar(null);
}

/* ---------- content enhancement: images, headings, tables ---------- */
function slugify(s){
  return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'section';
}
function enhance(root){
  if (!root) return;
  root.querySelectorAll('img[data-i]').forEach(function(img){
    var uri = IMG[img.dataset.i];
    if (!uri){
      var ph = document.createElement('span');
      ph.className = 'imgmiss';
      ph.textContent = img.alt ? img.alt + ' \u00b7 image unavailable' : 'Image unavailable';
      img.replaceWith(ph);
      return;
    }
    img.src = uri;
    var block = false;
    if (!img.closest('td,th')){
      var par = img.parentElement;
      if (par && (par.tagName === 'P' || par.tagName === 'FIGURE' || par.tagName === 'DIV')){
        if ((par.textContent || '').trim().length < 3) block = true;
      }
    }
    img.className = block ? 'bl' : 'ic';
    if (block && img.alt && img.alt.length > 2 && !img.closest('figure')){
      var fig = document.createElement('figure');
      var cap = document.createElement('figcaption');
      cap.textContent = img.alt;
      img.replaceWith(fig); fig.appendChild(img); fig.appendChild(cap);
    }
  });

  var used = {};
  root.querySelectorAll('h2, h3').forEach(function(hd){
    var base = slugify(hd.textContent), id = base, n = 2;
    while (used[id]) id = base + '-' + (n++);
    used[id] = 1; hd.id = id;
    var b = document.createElement('button');
    b.className = 'anchor'; b.type = 'button';
    b.setAttribute('aria-label', 'Copy link to "' + hd.textContent.trim() + '"');
    b.textContent = '#';
    b.onclick = function(){
      var target = location.href.replace(/#.*$/, '') + '#/' +
                   encodeURIComponent(shownSlug) + '#' + id;
      if (navigator.clipboard && navigator.clipboard.writeText){
        navigator.clipboard.writeText(target).then(function(){ say('Link to section copied'); },
                                                   function(){});
      }
      history.replaceState(null, '', '#/' + encodeURIComponent(shownSlug) + '#' + id);
    };
    hd.appendChild(b);
  });

  root.querySelectorAll('table').forEach(function(t){
    if (t.closest('.tw')) return;
    var wrap = document.createElement('div'); wrap.className = 'tw';
    var sc = document.createElement('div'); sc.className = 'tscroll';
    t.parentNode.insertBefore(wrap, t);
    wrap.appendChild(sc); sc.appendChild(t);

    var heads = [].map.call(t.querySelectorAll('thead th'), function(th){
      th.setAttribute('scope', 'col');
      return th.textContent.trim();
    });
    if (!heads.length){
      var fr = t.querySelector('tr');
      if (fr && fr.querySelectorAll('th').length){
        heads = [].map.call(fr.querySelectorAll('th'), function(th){
          th.setAttribute('scope', 'col'); return th.textContent.trim();
        });
      }
    }
    var cols = heads.length || (t.querySelector('tr') ? t.querySelector('tr').children.length : 0);
    if (cols > 3) wrap.setAttribute('data-stick', '');

    // numeric alignment + header association for the mobile card view
    [].forEach.call(t.querySelectorAll('tbody tr'), function(tr){
      [].forEach.call(tr.children, function(td, i){
        if (heads[i]) td.setAttribute('data-l', heads[i]);
        var txt = td.textContent.trim();
        if (txt && /^[+\-]?[\d.,%\u00d7x\s/]+$/.test(txt) && /\d/.test(txt)) td.classList.add('num');
      });
    });

    var hint = document.createElement('p');
    hint.className = 'thint';
    hint.innerHTML = '<span aria-hidden="true">&#8596;</span> Scroll the table sideways for more columns';
    wrap.appendChild(hint);

    // mobile card view for narrow-enough tables, built from the real table so
    // the semantic table is never destroyed - it is simply swapped out by CSS
    if (heads.length >= 2 && heads.length <= 5){
      var rows = t.querySelectorAll('tbody tr');
      if (rows.length && rows.length <= 60){
        var box = document.createElement('div');
        box.className = 'tcards';
        box.setAttribute('aria-hidden', 'true');
        [].forEach.call(rows, function(tr){
          var cells = tr.children;
          if (!cells.length) return;
          var c = document.createElement('div'); c.className = 'tcard';
          var head = document.createElement('div'); head.className = 'th';
          head.innerHTML = cells[0].innerHTML;
          c.appendChild(head);
          var dl = document.createElement('dl');
          for (var i = 1; i < cells.length; i++){
            var dt = document.createElement('dt'); dt.textContent = heads[i] || ('Column ' + (i + 1));
            var dd = document.createElement('dd'); dd.innerHTML = cells[i].innerHTML;
            dl.appendChild(dt); dl.appendChild(dd);
          }
          c.appendChild(dl); box.appendChild(c);
        });
        wrap.appendChild(box);
        wrap.setAttribute('data-cards', '');
      }
    }

    var upd = function(){
      if (sc.scrollWidth - sc.clientWidth > 4 && sc.scrollLeft + sc.clientWidth < sc.scrollWidth - 4)
        wrap.setAttribute('data-over', '');
      else wrap.removeAttribute('data-over');
    };
    sc.addEventListener('scroll', upd, {passive:true});
    addEventListener('resize', upd);
    setTimeout(upd, 30);
  });
}

/* ---------- right rail: TOC + related ---------- */
var tocObserver = null;
function tocItems(){
  var body = document.getElementById('body');
  if (!body) return [];
  return [].map.call(body.querySelectorAll('h2, h3'), function(h){
    return {id:h.id, text:h.textContent.replace(/#$/, '').trim(), lvl:h.tagName === 'H3' ? 3 : 2, el:h};
  }).filter(function(x){ return x.text.length > 1; });
}
function tocMarkup(items, cls){
  var base = '#/' + encodeURIComponent(shownSlug || '');
  return '<ul class="toc' + (cls || '') + '">' + items.map(function(i){
    return '<li><a class="' + (i.lvl === 3 ? 'l3' : '') + '" href="' + base + '#' + attr(i.id) + '" data-toc="' + attr(i.id) + '">' +
      esc(i.text) + '</a></li>';
  }).join('') + '</ul>';
}
function buildRail(slug){
  var rail = document.getElementById('rail'), p = P[slug];
  if (!rail) return;
  var items = tocItems(), h = '';
  document.documentElement.classList.toggle('hastoc', items.length >= 3);
  if (items.length >= 3) h += '<p class="rlabel">On this page</p>' + tocMarkup(items);
  var rel = (p.related || []).filter(function(s){ return P[s]; });
  if (rel.length){
    h += '<p class="rlabel">Related entries</p><ul class="rel">' + rel.map(function(s){
      return '<li><a href="' + hrefFor(s) + '" style="--accent:' + accentOf(P[s].section) + '">' +
        glyph(P[s].section, 8) + '<span>' + esc(P[s].title) + '</span></a></li>';
    }).join('') + '</ul>';
  }
  rail.innerHTML = h;

  if (tocObserver) tocObserver.disconnect();
  if (items.length >= 3 && 'IntersectionObserver' in window){
    var links = {};
    rail.querySelectorAll('[data-toc]').forEach(function(a){ links[a.dataset.toc] = a; });
    var visible = {};
    tocObserver = new IntersectionObserver(function(entries){
      entries.forEach(function(en){ visible[en.target.id] = en.isIntersecting; });
      var first = items.filter(function(i){ return visible[i.id]; })[0];
      Object.keys(links).forEach(function(k){ links[k].classList.toggle('on', !!first && k === first.id); });
    }, {rootMargin:'-70px 0px -70% 0px'});
    items.forEach(function(i){ tocObserver.observe(i.el); });
  }
}

/* ================= Search palette ================= */
var pal = document.getElementById('pal'), palq = document.getElementById('palq'),
    palout = document.getElementById('palout'), scrim = document.getElementById('scrim'),
    palcount = document.getElementById('palcount');
var palSel = 0, palRows = [], lastFocus = null;

function say(msg){ live.textContent = msg; }

function palSuggestions(){
  var rq = lsGet('ws-recentq', []), rp = lsGet('ws-recent', []).filter(function(s){ return P[s]; });
  var h = '';
  if (rq.length) h += '<div class="pgroup">Recent searches</div>' + rq.map(function(q){
    return '<a class="pres" href="#" data-q="' + attr(q) + '"><span class="pt">' + esc(q) + '</span></a>';
  }).join('');
  if (rp.length) h += '<div class="pgroup">Recently viewed</div>' + rp.slice(0, 5).map(function(s){
    return '<a class="pres" href="' + hrefFor(s) + '">' + thumb(s) +
      '<span style="min-width:0"><span class="pt">' + esc(P[s].title) + '</span></span>' +
      '<span class="pk">' + esc(P[s].section) + '</span></a>';
  }).join('');
  h += '<div class="pgroup">Jump to a category</div>' + ORDER.map(function(s){
    return '<a class="pres" href="#/c/' + encodeURIComponent(s) + '" style="--accent:' + accentOf(s) + '">' +
      '<span class="thumb">' + glyph(s, 11) + '</span><span class="pt">' + esc(s) + '</span>' +
      '<span class="pk">' + (SEC[s] || []).length + '</span></a>';
  }).join('');
  palout.innerHTML = h;
  palcount.textContent = '';
  indexRows();
}
function palResults(term){
  var hits = query(term, 40);
  if (!hits.length){
    palout.innerHTML = '<div class="palempty"><b>No entries found for \u201c' + esc(term) + '\u201d</b>' +
      'Try a shorter word or a different spelling &mdash; or browse ' +
      '<a href="#/c/' + encodeURIComponent('Items & Equipment') + '" data-close="1">Items &amp; Equipment</a>.</div>';
    palcount.textContent = '0 results';
    say('No results for ' + term);
    palRows = []; return;
  }
  var groups = {};
  hits.forEach(function(e){ (groups[e.section] = groups[e.section] || []).push(e); });
  var h = '';
  ORDER.concat(Object.keys(groups)).filter(function(s, i, a){ return groups[s] && a.indexOf(s) === i; })
    .forEach(function(s){
      h += '<div class="pgroup" style="--accent:' + accentOf(s) + '">' + glyph(s, 8) + esc(s) +
        ' <span style="color:var(--ink-3)">' + groups[s].length + '</span></div>';
      groups[s].slice(0, 8).forEach(function(e){
        h += '<a class="pres" href="' + hrefFor(e.slug) + '" role="option">' + thumb(e.slug) +
          '<span style="min-width:0"><span class="pt">' + highlight(e.title, term) + '</span>' +
          '<span class="px">' + highlight(e.text.slice(0, 90), term) + '</span></span>' +
          '<span class="pk">' + esc(e.sub || '') + '</span></a>';
      });
    });
  palout.innerHTML = h;
  palcount.textContent = hits.length + (hits.length === 1 ? ' result' : ' results');
  say(hits.length + ' results for ' + term);
  indexRows();
}
function indexRows(){
  palRows = [].slice.call(palout.querySelectorAll('.pres'));
  palSel = 0; markSel();
}
function markSel(){
  palRows.forEach(function(r, i){
    if (i === palSel){ r.setAttribute('data-sel', '1'); r.setAttribute('aria-selected', 'true'); }
    else { r.removeAttribute('data-sel'); r.removeAttribute('aria-selected'); }
  });
  var el = palRows[palSel];
  if (el){
    var pr = palout.getBoundingClientRect(), er = el.getBoundingClientRect();
    if (er.bottom > pr.bottom) palout.scrollTop += er.bottom - pr.bottom + 8;
    else if (er.top < pr.top) palout.scrollTop -= pr.top - er.top + 8;
  }
}
function openPalette(seed){
  lastFocus = document.activeElement;
  pal.classList.add('on'); scrim.classList.add('on');
  palq.value = seed || '';
  if (palq.value) palResults(palq.value); else palSuggestions();
  palq.focus();
}
function closePalette(){
  pal.classList.remove('on'); scrim.classList.remove('on');
  if (lastFocus && lastFocus.focus) lastFocus.focus();
}
var palTimer;
palq.addEventListener('input', function(){
  clearTimeout(palTimer);
  var v = palq.value;
  palTimer = setTimeout(function(){
    if (v.trim().length) palResults(v); else palSuggestions();
  }, 90);
});
palq.addEventListener('keydown', function(e){
  if (e.key === 'ArrowDown'){ e.preventDefault(); if (palRows.length){ palSel = (palSel + 1) % palRows.length; markSel(); } }
  else if (e.key === 'ArrowUp'){ e.preventDefault(); if (palRows.length){ palSel = (palSel - 1 + palRows.length) % palRows.length; markSel(); } }
  else if (e.key === 'Enter'){
    e.preventDefault();
    var el = palRows[palSel];
    if (!el) return;
    if (el.dataset.q){ palq.value = el.dataset.q; palResults(el.dataset.q); return; }
    pushRecentQuery(palq.value.trim());
    location.hash = el.getAttribute('href').slice(1);
    closePalette();
  } else if (e.key === 'Escape'){ e.preventDefault(); closePalette(); }
  else if (e.key === 'Tab'){ e.preventDefault(); }
});
palout.addEventListener('click', function(e){
  var r = e.target.closest('.pres');
  if (r && r.dataset.q){ e.preventDefault(); palq.value = r.dataset.q; palResults(r.dataset.q); palq.focus(); return; }
  if (r || e.target.closest('[data-close]')){ pushRecentQuery(palq.value.trim()); closePalette(); }
});
palout.addEventListener('mousemove', function(e){
  var r = e.target.closest('.pres');
  if (!r) return;
  var i = palRows.indexOf(r);
  if (i > -1 && i !== palSel){ palSel = i; markSel(); }
});

/* ================= mobile TOC sheet ================= */
var sheet = document.getElementById('sheet');
function openSheet(){
  var items = tocItems();
  if (!items.length) return;
  sheet.innerHTML = '<p class="rlabel">On this page</p>' + tocMarkup(items) +
    '<button class="chip" data-closesheet="1" style="width:100%;margin-top:8px">Close</button>';
  sheet.classList.add('on'); scrim.classList.add('on');
  document.getElementById('mtoc').setAttribute('aria-expanded', 'true');
  var f = sheet.querySelector('a'); if (f) f.focus();
}
function closeSheet(){
  sheet.classList.remove('on');
  if (!pal.classList.contains('on') && document.documentElement.dataset.side !== 'on') scrim.classList.remove('on');
  document.getElementById('mtoc').setAttribute('aria-expanded', 'false');
}
sheet.addEventListener('click', function(e){
  if (e.target.closest('[data-closesheet]') || e.target.closest('a')) closeSheet();
});

/* ================= drawer / sidebar ================= */
var root = document.documentElement;
function openDrawer(){
  root.dataset.side = 'on'; scrim.classList.add('on');
  document.getElementById('mburger').setAttribute('aria-expanded', 'true');
  var f = document.getElementById('opensearch'); if (f) f.focus();
}
function closeDrawer(){
  if (root.dataset.side === 'on'){
    root.dataset.side = '';
    if (!pal.classList.contains('on') && !sheet.classList.contains('on')) scrim.classList.remove('on');
    document.getElementById('mburger').setAttribute('aria-expanded', 'false');
  }
}
document.getElementById('mburger').onclick = openDrawer;
document.getElementById('msearch').onclick = function(){ openPalette(); };
document.getElementById('mtoc').onclick = function(){
  sheet.classList.contains('on') ? closeSheet() : openSheet();
};
document.getElementById('opensearch').onclick = function(){ openPalette(); };
document.getElementById('sidetoggle').onclick = function(){
  var off = root.getAttribute('data-side') === 'off';
  root.setAttribute('data-side', off ? '' : 'off');
  this.setAttribute('aria-expanded', String(off));
  lsSet('ws-side', off ? '' : 'off');
};
scrim.onclick = function(){ closeDrawer(); closePalette(); closeSheet(); };

/* ================= keyboard ================= */
document.addEventListener('keydown', function(e){
  var tag = (document.activeElement && document.activeElement.tagName) || '';
  var typing = tag === 'INPUT' || tag === 'TEXTAREA' || document.activeElement.isContentEditable;
  if ((e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey)){
    e.preventDefault(); pal.classList.contains('on') ? closePalette() : openPalette();
  } else if (e.key === '/' && !typing && !pal.classList.contains('on')){
    e.preventDefault(); openPalette();
  } else if (e.key === 'Escape'){
    if (pal.classList.contains('on')) closePalette();
    else if (sheet.classList.contains('on')) closeSheet();
    else closeDrawer();
  }
});
/* focus trap for the palette */
document.addEventListener('focusin', function(e){
  if (pal.classList.contains('on') && !pal.contains(e.target)) palq.focus();
});

/* ================= theme ================= */
function setTheme(t){
  root.setAttribute('data-theme', t);
  try { localStorage.setItem('ws-theme', t); } catch(e){}
  var b = document.getElementById('themebtn');
  b.setAttribute('aria-label', t === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
  document.getElementById('ic-theme').innerHTML = t === 'dark'
    ? '<path d="M20 14.5A8.2 8.2 0 0 1 9.5 4 8.4 8.4 0 1 0 20 14.5Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>'
    : '<circle cx="12" cy="12" r="4.2"/><path d="M12 2.6v2.2M12 19.2v2.2M3.6 12H1.4M22.6 12h-2.2M5.6 5.6l1.6 1.6M16.8 16.8l1.6 1.6M18.4 5.6l-1.6 1.6M7.2 16.8l-1.6 1.6"/>';
}
(function(){
  var t; try { t = localStorage.getItem('ws-theme'); } catch(e){}
  if (!t) t = matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'light';
  setTheme(t);
  try { if (localStorage.getItem('ws-side') === 'off' && innerWidth > 900) root.setAttribute('data-side', 'off'); } catch(e){}
})();
document.getElementById('themebtn').onclick = function(){
  setTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
};

/* ================= router ================= */
function scrollToId(id){
  var el = id && document.getElementById(id);
  if (!el) return;
  var y = el.getBoundingClientRect().top + (window.pageYOffset || 0) - 74;
  window.scrollTo({top:y, behavior:matchMedia('(prefers-reduced-motion:reduce)').matches ? 'auto' : 'smooth'});
}
function route(){
  closeDrawer(); closeSheet();
  var raw = location.hash.replace(/^#/, '');
  if (!raw || raw === '/'){ shownSlug = null; renderHome(); return; }
  if (raw.charAt(0) !== '/'){ scrollToId(decodeURIComponent(raw)); return; }
  var path = raw.slice(1);
  if (path.indexOf('c/') === 0){ shownSlug = null; renderCategory(decodeURIComponent(path.slice(2))); return; }
  if (path.indexOf('browse/') === 0){ location.replace('#/c/' + path.slice(7)); return; }
  var parts = path.split('#'), slug = decodeURIComponent(parts[0]);
  if (slug === shownSlug){ if (parts[1]) scrollToId(parts[1]); return; }
  renderPage(slug);
  if (parts[1]) setTimeout(function(){ scrollToId(parts[1]); }, 20);
}
addEventListener('hashchange', route);

document.getElementById('pcount').textContent = DATA.count + ' pages';
Sidebar('@home');
route();
</script>
</html>
"""

html_out = TEMPLATE.replace("__DATA__", payload)
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print("index.html written: %.0f KB, %d pages" %
      (os.path.getsize("index.html") / 1024, data["count"]))
