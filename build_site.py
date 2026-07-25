#!/usr/bin/env python3
"""Generate the single-file WalkScape Companion web app (index.html)
from data/wiki_data.json."""
import json, io

with open("data/wiki_data.json", encoding="utf-8") as f:
    data = json.load(f)

# embed compressed image data-URIs, if the image pipeline has run
try:
    with open("data/images.json", encoding="utf-8") as f:
        data["images"] = json.load(f)
except FileNotFoundError:
    data["images"] = {}

# order sections for the sidebar
SECTION_ORDER = ["Basics & Reference", "Skills", "Activities", "Items",
                 "Locations", "Keywords", "Guides"]
sections = data["sections"]
ordered = [s for s in SECTION_ORDER if s in sections] + \
          [s for s in sections if s not in SECTION_ORDER]
data["order"] = ordered

payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

TEMPLATE = r"""<meta charset="utf-8">
<title>WalkScape Companion</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{
  --paper:#eef1ea; --paper-2:#e4e9dd; --panel:#f6f8f2;
  --ink:#1b2620; --ink-soft:#556158; --faint:#7c887e;
  --line:#cfd8c8; --line-soft:#dde3d5;
  --pine:#2f5d43; --pine-deep:#244a35; --moss:#5f8a56;
  --blaze:#c46a2b; --blaze-soft:#e7d3bf;
  --good:#3e7d53; --warn:#b98a26;
  --shadow:0 1px 2px rgba(28,38,32,.06),0 8px 24px -12px rgba(28,38,32,.18);
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono","Cascadia Code",Menlo,Consolas,monospace;
  --measure:66ch;
}
[data-theme="dark"]{
  --paper:#121b16; --paper-2:#18221c; --panel:#1b271f;
  --ink:#dde6db; --ink-soft:#93a398; --faint:#74827a;
  --line:#293a30; --line-soft:#22302a;
  --pine:#84bd90; --pine-deep:#9ccaa6; --moss:#8fb283;
  --blaze:#e08b44; --blaze-soft:#3a2e22;
  --good:#61ad78; --warn:#d8ab48;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px -14px rgba(0,0,0,.6);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{animation:none!important;transition:none!important}}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
  font-size:16px;line-height:1.62;-webkit-font-smoothing:antialiased;}
a{color:var(--pine);text-decoration:none}
a:hover{text-decoration:underline;text-decoration-color:var(--blaze);text-underline-offset:3px}
:focus-visible{outline:2px solid var(--blaze);outline-offset:2px;border-radius:3px}

/* ---------- layout ---------- */
.app{display:grid;grid-template-columns:300px minmax(0,1fr);min-height:100vh}
.side{position:sticky;top:0;height:100vh;overflow-y:auto;background:var(--paper-2);
  border-right:1px solid var(--line);padding:0;display:flex;flex-direction:column}
.main{min-width:0;display:flex;flex-direction:column}
.scrim{display:none;position:fixed;inset:0;background:rgba(10,16,12,.45);z-index:15}

/* ---------- masthead ---------- */
.brand{position:relative;padding:22px 20px 18px;border-bottom:1px solid var(--line);overflow:hidden}
.brand canvas{position:absolute;inset:0;width:100%;height:100%;opacity:.5;pointer-events:none}
.brand .row{position:relative;display:flex;align-items:center;gap:11px}
.mark{width:34px;height:34px;flex:none;border-radius:50%;border:1.5px solid var(--pine);
  display:grid;place-items:center;color:var(--pine);background:var(--panel)}
.mark svg{width:20px;height:20px}
.wordmark{font-family:var(--serif);font-size:1.32rem;font-weight:600;letter-spacing:.01em;line-height:1.05}
.wordmark small{display:block;font-family:var(--sans);font-weight:600;font-size:.6rem;
  letter-spacing:.22em;text-transform:uppercase;color:var(--blaze);margin-top:3px}

/* ---------- search ---------- */
.search{position:relative;padding:14px 16px;border-bottom:1px solid var(--line)}
.search input{width:100%;padding:9px 12px 9px 34px;border:1px solid var(--line);
  background:var(--panel);color:var(--ink);border-radius:8px;font-size:.9rem;font-family:var(--sans)}
.search input::placeholder{color:var(--faint)}
.search svg{position:absolute;left:28px;top:50%;transform:translateY(-50%);
  width:15px;height:15px;color:var(--faint)}
.kbd{position:absolute;right:26px;top:50%;transform:translateY(-50%);font-family:var(--mono);
  font-size:.68rem;color:var(--faint);border:1px solid var(--line);border-radius:4px;padding:1px 5px}

/* ---------- nav ---------- */
nav{padding:8px 8px 24px;flex:1}
.sec{margin-top:12px}
.sec>h4{display:flex;align-items:center;gap:8px;margin:0;padding:6px 12px;
  font-size:.68rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--faint)}
.sec>h4 .n{margin-left:auto;font-family:var(--mono);font-weight:600;letter-spacing:0;
  font-size:.66rem;color:var(--faint);background:var(--paper);border:1px solid var(--line);
  border-radius:20px;padding:0 7px}
.sec ul{list-style:none;margin:2px 0 0;padding:0}
.sec li a{display:block;padding:5px 12px 5px 22px;font-size:.855rem;color:var(--ink-soft);
  border-left:2px solid transparent;line-height:1.35}
.sec li a:hover{color:var(--ink);background:var(--panel);text-decoration:none}
.sec li a.active{color:var(--pine-deep);font-weight:600;border-left-color:var(--blaze);
  background:var(--panel)}
[data-theme="dark"] .sec li a.active{color:var(--pine)}

/* ---------- content ---------- */
.topbar{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:12px;
  padding:12px 26px;background:color-mix(in srgb,var(--paper) 88%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--line-soft)}
.crumb{font-size:.7rem;letter-spacing:.16em;text-transform:uppercase;color:var(--faint)}
.spacer{flex:1}
.iconbtn{display:grid;place-items:center;width:34px;height:34px;border-radius:8px;
  border:1px solid var(--line);background:var(--panel);color:var(--ink-soft);cursor:pointer}
.iconbtn:hover{color:var(--ink);border-color:var(--pine)}
.iconbtn svg{width:17px;height:17px}
.menu-toggle{display:none}

.article{width:100%;max-width:calc(var(--measure) + 60px);margin:0 auto;padding:34px 30px 90px;
  animation:rise .4s ease both}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.eyebrow{font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:var(--blaze);
  font-weight:700;margin-bottom:8px}
.article h1{font-family:var(--serif);font-weight:600;font-size:2.15rem;line-height:1.1;
  margin:0 0 6px;text-wrap:balance;letter-spacing:-.01em}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 26px}
.tag{font-size:.68rem;letter-spacing:.04em;color:var(--ink-soft);background:var(--panel);
  border:1px solid var(--line);border-radius:20px;padding:2px 10px}

/* rendered wiki content */
.body{font-size:1rem}
.body>*{max-width:var(--measure)}
.body table{max-width:100%}
.body h2{font-family:var(--serif);font-weight:600;font-size:1.42rem;margin:2.1em 0 .5em;
  padding-bottom:.28em;border-bottom:1px solid var(--line);text-wrap:balance;letter-spacing:-.005em}
.body h3{font-size:1.08rem;font-weight:700;margin:1.7em 0 .4em;color:var(--pine-deep)}
[data-theme="dark"] .body h3{color:var(--pine)}
.body h4{font-size:.95rem;font-weight:700;margin:1.4em 0 .3em;color:var(--ink-soft)}
.body p{margin:.85em 0}
.body ul,.body ol{margin:.7em 0;padding-left:1.4em}
.body li{margin:.28em 0}
.body li::marker{color:var(--moss)}
.body a[target]::after{content:"↗";font-size:.72em;color:var(--faint);margin-left:2px;vertical-align:super}
.body blockquote{margin:1.1em 0;padding:.4em 1.1em;border-left:3px solid var(--blaze);
  background:var(--panel);color:var(--ink-soft);border-radius:0 8px 8px 0}
.body code{font-family:var(--mono);font-size:.86em;background:var(--panel);
  border:1px solid var(--line-soft);border-radius:4px;padding:.08em .35em}
.body pre{overflow-x:auto;background:var(--panel);border:1px solid var(--line);
  border-radius:10px;padding:14px 16px}
.body pre code{background:none;border:none;padding:0}
.body hr{border:none;border-top:1px solid var(--line);margin:2em 0}
.tablewrap{overflow-x:auto;margin:1.2em 0;border:1px solid var(--line);border-radius:10px}
.body table{border-collapse:collapse;width:100%;font-size:.9rem;font-variant-numeric:tabular-nums}
.body thead th{background:var(--paper-2);text-align:left;font-weight:700;color:var(--pine-deep)}
[data-theme="dark"] .body thead th{color:var(--pine)}
.body th,.body td{border-bottom:1px solid var(--line-soft);padding:8px 12px;vertical-align:top}
.body tbody tr:hover{background:var(--panel)}
.body img{max-width:100%}
.body img.ic{height:1.4em;width:auto;vertical-align:-.24em;margin:0 1px}
.body img.bl{display:block;max-height:200px;width:auto;margin:14px 0;
  border-radius:8px;background:var(--panel);padding:6px}
.body td img.ic,.body th img.ic{height:1.7em}
.body h1 img,.body h2 img,.body h3 img{height:1em;vertical-align:-.12em}

/* ---------- search results ---------- */
.results{max-width:calc(var(--measure) + 60px);margin:0 auto;padding:30px 30px 80px}
.results h1{font-family:var(--serif);font-weight:600;font-size:1.7rem;margin:0 0 4px}
.results .meta{color:var(--faint);font-size:.85rem;margin-bottom:20px}
.hit{display:block;padding:14px 16px;border:1px solid var(--line);border-radius:10px;
  background:var(--panel);margin-bottom:10px;color:inherit}
.hit:hover{border-color:var(--pine);text-decoration:none;box-shadow:var(--shadow)}
.hit .t{font-family:var(--serif);font-size:1.08rem;color:var(--pine-deep);font-weight:600}
[data-theme="dark"] .hit .t{color:var(--pine)}
.hit .s{font-size:.66rem;letter-spacing:.12em;text-transform:uppercase;color:var(--blaze);margin-left:8px}
.hit .x{color:var(--ink-soft);font-size:.88rem;margin-top:4px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
mark{background:var(--blaze-soft);color:inherit;border-radius:2px;padding:0 1px}

/* ---------- home landing ---------- */
.hero-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
  gap:12px;margin:26px 0 8px}
.hcard{padding:16px;border:1px solid var(--line);border-radius:12px;background:var(--panel);
  transition:transform .15s ease,border-color .15s ease}
.hcard:hover{transform:translateY(-2px);border-color:var(--pine);text-decoration:none;box-shadow:var(--shadow)}
.hcard .hn{font-family:var(--serif);font-size:1.06rem;font-weight:600;color:var(--pine-deep)}
[data-theme="dark"] .hcard .hn{color:var(--pine)}
.hcard .hc{font-family:var(--mono);font-size:.72rem;color:var(--faint);margin-top:2px}
.foot{color:var(--faint);font-size:.78rem;border-top:1px solid var(--line);
  margin-top:40px;padding-top:16px}

/* ---------- responsive ---------- */
@media (max-width:820px){
  .app{grid-template-columns:1fr}
  .side{position:fixed;z-index:20;width:290px;transform:translateX(-100%);transition:transform .22s ease}
  .side.open{transform:none;box-shadow:0 0 40px rgba(0,0,0,.3)}
  .menu-toggle{display:grid}
  .scrim.show{display:block}
}
</style>

<div class="app">
  <aside class="side" id="side">
    <div class="brand">
      <canvas id="topo"></canvas>
      <div class="row">
        <span class="mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13 4l-2 5h4l-3 11"/><circle cx="12" cy="12" r="9"/></svg>
        </span>
        <span class="wordmark">WalkScape<small>Companion</small></span>
      </div>
    </div>
    <div class="search">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg>
      <input id="q" type="search" placeholder="Search the almanac…" autocomplete="off" spellcheck="false" aria-label="Search">
      <span class="kbd">/</span>
    </div>
    <nav id="nav" aria-label="Wiki index"></nav>
  </aside>

  <div class="scrim" id="scrim"></div>

  <div class="main">
    <div class="topbar">
      <button class="iconbtn menu-toggle" id="menu" aria-label="Menu">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
      </button>
      <span class="crumb" id="crumb">Almanac</span>
      <span class="spacer"></span>
      <button class="iconbtn" id="theme" aria-label="Toggle theme">
        <svg id="ic-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19"/></svg>
      </button>
    </div>
    <div id="view" role="main"></div>
  </div>
</div>

<script type="application/json" id="data">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const P = DATA.pages, SEC = DATA.sections, ORDER = DATA.order;
const view = document.getElementById('view');
const crumb = document.getElementById('crumb');
const nav = document.getElementById('nav');
const side = document.getElementById('side');
const scrim = document.getElementById('scrim');

/* ----- build sidebar ----- */
function buildNav(filter){
  nav.innerHTML='';
  const f = (filter||'').trim().toLowerCase();
  ORDER.forEach(secName=>{
    let slugs = SEC[secName]||[];
    if(f) slugs = slugs.filter(s=>P[s].title.toLowerCase().includes(f));
    if(!slugs.length) return;
    const box=document.createElement('div');box.className='sec';
    box.innerHTML='<h4>'+secName+'<span class="n">'+slugs.length+'</span></h4>';
    const ul=document.createElement('ul');
    slugs.forEach(s=>{
      const li=document.createElement('li');
      const a=document.createElement('a');
      a.href='#/'+encodeURIComponent(s);
      a.textContent=P[s].title;
      a.dataset.slug=s;
      li.appendChild(a);ul.appendChild(li);
    });
    box.appendChild(ul);nav.appendChild(box);
  });
}

function markActive(slug){
  nav.querySelectorAll('a').forEach(a=>a.classList.toggle('active',a.dataset.slug===slug));
}

/* ----- resolve inline images + wrap tables for scroll ----- */
const IMG=DATA.images||{};
function enhance(container){
  container.querySelectorAll('img[data-i]').forEach(img=>{
    const uri=IMG[img.dataset.i];
    if(!uri){img.remove();return;}
    img.src=uri;
    let block=false;
    if(!img.closest('td,th')){
      const p=img.parentElement;
      if(p&&(p.tagName==='P'||p.tagName==='FIGURE'||p.tagName==='DIV')){
        if((p.textContent||'').trim().length<3) block=true;
      }
    }
    img.className=block?'bl':'ic';
  });
  container.querySelectorAll('table').forEach(t=>{
    if(t.parentElement.classList.contains('tablewrap'))return;
    const w=document.createElement('div');w.className='tablewrap';
    t.parentNode.insertBefore(w,t);w.appendChild(t);
  });
}

/* ----- render a page ----- */
function renderPage(slug){
  const p=P[slug];
  if(!p){renderHome();return;}
  crumb.textContent=p.section;
  const tags=(p.categories||[]).filter(c=>!/^Pages /.test(c)).slice(0,5)
    .map(c=>'<span class="tag">'+c+'</span>').join('');
  view.innerHTML='<article class="article"><div class="eyebrow">'+p.section+
    '</div><h1>'+p.title+'</h1>'+(tags?'<div class="tags">'+tags+'</div>':'<div style="height:10px"></div>')+
    '<div class="body">'+p.html+'</div></article>';
  enhance(view);
  markActive(slug);
  document.querySelector('.main').scrollTop=0;window.scrollTo(0,0);
}

/* ----- home landing ----- */
function renderHome(){
  crumb.textContent='Almanac';
  const home=P[DATA.home];
  let cards='';
  ORDER.forEach(s=>{cards+='<a class="hcard" href="#/browse/'+encodeURIComponent(s)+'">'+
    '<div class="hn">'+s+'</div><div class="hc">'+(SEC[s]||[]).length+' entries</div></a>';});
  view.innerHTML='<article class="article">'+
    '<div class="eyebrow">Field Almanac · '+DATA.count+' entries</div>'+
    '<h1>'+ (home?home.title:'WalkScape Companion') +'</h1>'+
    '<div class="body">'+(home?home.html:'')+'</div>'+
    '<div class="hero-cards">'+cards+'</div>'+
    '<div class="foot">Unofficial companion · content from the community WalkScape wiki, reorganized for easier reading.</div>'+
    '</article>';
  enhance(view);markActive(DATA.home);
}

/* ----- browse a section as a list ----- */
function renderBrowse(sec){
  crumb.textContent=sec;
  const slugs=SEC[sec]||[];
  let hits=slugs.map(s=>'<a class="hit" href="#/'+encodeURIComponent(s)+'"><span class="t">'+
    P[s].title+'</span><div class="x">'+(P[s].text||'').slice(0,140)+'</div></a>').join('');
  view.innerHTML='<div class="results"><h1>'+sec+'</h1><div class="meta">'+slugs.length+
    ' entries</div>'+hits+'</div>';
  markActive(null);
}

/* ----- search ----- */
function search(term){
  const t=term.toLowerCase();
  const res=[];
  for(const s in P){
    const p=P[s];
    const ti=p.title.toLowerCase();
    let score=0;
    if(ti===t)score=100;else if(ti.startsWith(t))score=60;
    else if(ti.includes(t))score=40;
    else if((p.text||'').toLowerCase().includes(t))score=12;
    if(score)res.push([score,s]);
  }
  res.sort((a,b)=>b[0]-a[0]||P[a[1]].title.localeCompare(P[b[1]].title));
  const top=res.slice(0,60);
  crumb.textContent='Search';
  const esc=term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  const re=new RegExp('('+esc+')','ig');
  const hl=x=>x.replace(re,'<mark>$1</mark>');
  let html=top.map(([sc,s])=>{const p=P[s];
    return '<a class="hit" href="#/'+encodeURIComponent(s)+'"><span class="t">'+hl(p.title)+
      '</span><span class="s">'+p.section+'</span><div class="x">'+hl((p.text||'').slice(0,150))+'</div></a>';
  }).join('');
  if(!top.length)html='<p style="color:var(--faint)">No entries match “'+term+'”.</p>';
  view.innerHTML='<div class="results"><h1>Search</h1><div class="meta">'+top.length+
    ' result'+(top.length===1?'':'s')+' for “'+term+'”</div>'+html+'</div>';
  markActive(null);
}

/* ----- router ----- */
function route(){
  const h=decodeURIComponent(location.hash.replace(/^#\//,''));
  closeSide();
  if(!h){renderHome();return;}
  if(h.startsWith('browse/')){renderBrowse(decodeURIComponent(h.slice(7)));return;}
  renderPage(h);
}
window.addEventListener('hashchange',route);

/* ----- search input ----- */
const q=document.getElementById('q');
let sTimer;
q.addEventListener('input',()=>{
  buildNav(q.value);
  clearTimeout(sTimer);
  const v=q.value.trim();
  sTimer=setTimeout(()=>{ if(v.length>=2) search(v); else if(!location.hash||location.hash==='#/') renderHome(); else route(); },140);
});
q.addEventListener('keydown',e=>{if(e.key==='Enter'){const first=nav.querySelector('a');if(first){location.hash=first.getAttribute('href').slice(1);q.blur();}}});
document.addEventListener('keydown',e=>{
  if(e.key==='/'&&document.activeElement!==q){e.preventDefault();q.focus();}
  if(e.key==='Escape'&&document.activeElement===q){q.value='';buildNav('');q.blur();route();}
});

/* ----- mobile menu ----- */
function openSide(){side.classList.add('open');scrim.classList.add('show');}
function closeSide(){side.classList.remove('open');scrim.classList.remove('show');}
document.getElementById('menu').onclick=openSide;
scrim.onclick=closeSide;

/* ----- theme ----- */
const root=document.documentElement;
function setTheme(t){root.setAttribute('data-theme',t);try{localStorage.setItem('ws-theme',t);}catch(e){}}
(function(){let t;try{t=localStorage.getItem('ws-theme');}catch(e){}
  if(!t)t=matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';setTheme(t);})();
document.getElementById('theme').onclick=()=>setTheme(root.getAttribute('data-theme')==='dark'?'light':'dark');

/* ----- topographic masthead ----- */
(function(){
  const c=document.getElementById('topo');if(!c)return;
  function draw(){
    const r=c.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);
    c.width=r.width*dpr;c.height=r.height*dpr;const x=c.getContext('2d');x.scale(dpr,dpr);
    x.clearRect(0,0,r.width,r.height);
    const col=getComputedStyle(root).getPropertyValue('--pine').trim();
    x.strokeStyle=col;x.globalAlpha=.16;x.lineWidth=1;
    const cx=r.width*0.78,cy=r.height*0.5;
    for(let i=0;i<7;i++){
      x.beginPath();
      for(let a=0;a<=Math.PI*2+0.1;a+=0.1){
        const rad=16+i*13+Math.sin(a*3+i)*5+Math.cos(a*2)*4;
        const px=cx+Math.cos(a)*rad*1.35, py=cy+Math.sin(a)*rad;
        a===0?x.moveTo(px,py):x.lineTo(px,py);
      }
      x.stroke();
    }
  }
  draw();addEventListener('resize',draw);
  new MutationObserver(draw).observe(root,{attributes:true,attributeFilter:['data-theme']});
})();

/* ----- init ----- */
buildNav('');
route();
</script>
"""

html = TEMPLATE.replace("__DATA__", payload)
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

import os
print(f"index.html written: {os.path.getsize('index.html')/1024:.0f} KB, {data['count']} pages")
