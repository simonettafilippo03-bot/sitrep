#!/usr/bin/env python3
"""SITREP // Morning Briefing - scarica i feed Google News e apre la pagina nel browser."""
import json, os, re, ssl, time, unicodedata, urllib.parse, urllib.request, webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

EN, IT = "hl=en-US&gl=US&ceid=US:en", "hl=it&gl=IT&ceid=IT:it"
FEEDS = [
 ("int","A","NOTIZIE INTERNAZIONALI (PRIME PAGINE)",EN,'(world OR global OR summit OR economy OR crisis) (site:reuters.com OR site:apnews.com OR site:bbc.com OR site:ft.com OR site:nytimes.com OR site:theguardian.com OR site:aljazeera.com OR site:wsj.com OR site:economist.com) when:1d'),
 ("ita","A","NOTIZIE ITALIANE (EVENTI & POLITICA INTERNA)",IT,'(governo OR parlamento OR politica OR cronaca OR economia OR riforma OR Meloni OR Mattarella OR inchiesta) (site:ansa.it OR site:agi.it OR site:ilpost.it OR site:ilsole24ore.com OR site:corriere.it OR site:repubblica.it OR site:lastampa.it OR site:editorialedomani.it) when:1d'),
 ("war","A","GUERRE & CONFLITTI GLOBALI",EN,'(war OR conflict OR frontline OR airstrike OR military OR offensive OR insurgency OR ceasefire) (Ukraine OR Gaza OR Lebanon OR Sudan OR Myanmar OR Sahel OR "Red Sea" OR Yemen OR Congo OR Taiwan) when:1d'),
 ("usa","B","USA // POLITICA & ISTITUZIONI",EN,'("White House" OR Congress OR Senate OR Trump OR Pentagon OR "Supreme Court" OR "US politics") when:1d'),
 ("ukr","B","UCRAINA // FRONTE & POLITICA INTERNA",EN,'(Ukraine OR Kyiv OR Zelensky OR Rada OR Donbas OR "Ukrainian military") when:1d'),
 ("chn","B","CINA // PECHINO, ECONOMIA & GEOPOLITICA",EN,'(China OR Beijing OR "Xi Jinping" OR CCP OR PLA OR "Taiwan Strait") when:1d'),
 ("isr","B","ISRAELE // GOVERNO, SICUREZZA & MO",EN,'(Israel OR Netanyahu OR Knesset OR IDF OR Jerusalem OR Mossad) when:1d'),
 ("mex","B","MESSICO // STATO, SICUREZZA & CARTELLI",EN,'(Mexico OR Sheinbaum OR Morena OR cartel OR CJNG OR Sinaloa OR narcotrafficking OR security) when:2d'),
 ("syr","B","SIRIA // TRANSIZIONE, FAZIONI & GEOPOLITICA",EN,'(Syria OR Damascus OR Syrian OR SDF OR Levant OR Aleppo) when:2d'),
]
MAXN = 12

BIAS = {
 1:["Reuters","Associated Press","AP News","ANSA","AGI","Adnkronos","BBC","Il Sole 24 Ore","InSight Crime","Bellingcat","Defense News","ISW","Financial Times","Bloomberg"],
 2:["Il Post","The Economist","Wall Street Journal","WSJ","New York Times","Corriere della Sera","La Stampa","El País","Politico","Foreign Policy","Foreign Affairs","Der Spiegel","Le Monde","CNN","PBS","NPR","Haaretz","Times of Israel"],
 3:["The Guardian","La Repubblica","Al Jazeera","Washington Post","Domani","Il Foglio","Il Messaggero","Il Giornale","Avvenire","Newsweek","Time","Jerusalem Post","South China Morning Post"],
 4:["Fox News","MSNBC","Il Fatto Quotidiano","Libero","New York Post","Daily Mail","Telegraph","HuffPost","National Review","Vox","The Intercept","Middle East Eye","Anadolu"],
 5:["La Verità","Il Manifesto","Breitbart","Jacobin","RT","Russia Today","Sputnik","Global Times","Xinhua","PressTV","TeleSUR","OAN","Newsmax","Daily Wire","Byoblu"],
}

def norm(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()

BIAS_RX = [(lvl, re.compile(r"(^|[^a-z0-9])" + re.escape(norm(n)) + r"($|[^a-z0-9])"))
           for lvl in (1, 2, 4, 5, 3) for n in BIAS[lvl]]

def kitten(source):
    n = norm(source)
    return next((lvl for lvl, rx in BIAS_RX if rx.search(n)), 3)

def fetch_xml(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SITREP)"})
    last = None
    for ctx in (None, ssl._create_unverified_context()):  # secondo tentativo: certificati Python non aggiornati
        for _ in range(2):
            try:
                with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
                    return r.read()
            except ssl.SSLError as e:
                last = e; break
            except Exception as e:
                last = e; time.sleep(1)
    raise last

def parse(xml_bytes):
    out, seen = [], set()
    for it in ET.fromstring(xml_bytes).iter("item"):
        raw = (it.findtext("title") or "").strip()
        src = (it.findtext("source") or "").strip()
        title = raw
        i = raw.rfind(" - ")
        if i > 0:
            tail = raw[i + 3:].strip()
            if not src: src = tail
            if tail == src: title = raw[:i].strip()
        try:
            ts = int(parsedate_to_datetime(it.findtext("pubDate")).timestamp() * 1000)
        except Exception:
            ts = 0
        link = (it.findtext("link") or "").strip()
        if title and link and title.lower() not in seen:
            seen.add(title.lower())
            src = src or "Sconosciuta"
            out.append({"t": title, "s": src, "k": kitten(src), "u": link, "ts": ts})
    out.sort(key=lambda x: -x["ts"])
    return out[:MAXN]

def build_data():
    data = {}
    for fid, _, name, loc, q in FEEDS:
        url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&" + loc
        print("Scarico:", name, flush=True)
        try:
            data[fid] = {"items": parse(fetch_xml(url)), "err": ""}
        except Exception as e:
            data[fid] = {"items": [], "err": str(e)}
        time.sleep(0.4)
    return data

TEMPLATE = r"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SITREP // Morning Briefing</title>
<style>
:root{--bg:#0a0c0e;--panel:#111518;--line:#262e33;--tx:#dce3e8;--tx2:#7a8891;--green:#00ff88;--blue:#3b82f6;--amber:#f59e0b;--red:#ef4444;--mono:"Fira Code","JetBrains Mono","Roboto Mono",Consolas,monospace;--sans:Inter,system-ui,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);font-family:var(--sans);padding:12px 14px 28px}
header{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;border:1px solid var(--line);background:var(--panel);padding:10px 14px;margin-bottom:12px;font-family:var(--mono);position:sticky;top:0;z-index:5}
h1{font-size:15px;font-weight:600;color:var(--green)}
@media(max-width:700px){header{position:static;padding:8px 10px}#q{flex:1 1 100%;min-width:0}.list{max-height:360px}body{padding:8px}}
#clock{font-size:13px;color:var(--blue)}#legend,#stamp{font-size:11px;color:var(--tx2)}.sp{flex:1}
#q{background:var(--bg);border:1px solid var(--line);color:var(--tx);font:12px var(--mono);padding:6px 10px;min-width:220px}
#q:focus,a:focus-visible{outline:1px solid var(--green)}
.sec{font:600 11px var(--mono);color:var(--tx2);margin:14px 2px 6px;letter-spacing:1px}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
@media(max-width:1100px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
.panel{background:var(--panel);border:1px solid var(--line);display:flex;flex-direction:column;min-width:0}
.ph{display:flex;justify-content:space-between;gap:8px;padding:8px 12px;border-bottom:1px solid var(--line);font:600 12px var(--mono)}
.ph .t{color:var(--green);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.ph .c{font-weight:400;font-size:10px;color:var(--tx2)}
.list{max-height:420px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:#2c373d var(--panel)}
.list::-webkit-scrollbar{width:6px}.list::-webkit-scrollbar-thumb{background:#2c373d}
.item{padding:8px 12px;border-bottom:1px solid var(--line)}.item:last-child{border-bottom:0}
.m{display:flex;justify-content:space-between;gap:8px;font:10.5px var(--mono);margin-bottom:3px;color:var(--tx2)}
.src{border:1px solid;padding:0 5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:78%}
.g{color:var(--green);border-color:#0a5a3a}.a{color:var(--amber);border-color:#6b4a0a}.r{color:var(--red);border-color:#6b2020}
.item a{color:var(--tx);text-decoration:none;font-size:13.5px;line-height:1.35;font-weight:500;display:block}.item a:hover{color:var(--green)}
.msg{padding:14px 12px;font:12px var(--mono);color:var(--red)}
</style></head><body>
<header><h1>SITREP // MORNING BRIEFING</h1><span id="clock"></span>
<span id="legend">KITTEN BIAS: 1🐱 Neutro -&gt; 5🐱 Molto Biased</span><span class="sp"></span>
<span id="stamp"></span><input id="q" type="search" placeholder="filtra titoli..." autocomplete="off"></header>
<div class="sec">// PANORAMICA GENERALE</div><div class="grid" id="gA"></div>
<div class="sec">// FOCUS PAESI</div><div class="grid" id="gB"></div>
<script>
const FEEDS=__FEEDS__,DATA=__DATA__,STAMP="__STAMP__";
const $=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e};
const ago=ts=>{if(!ts)return"--";const m=Math.max(0,Math.round((Date.now()-ts)/60000));return m<60?m+"m fa":m<1440?Math.floor(m/60)+"h fa":Math.floor(m/1440)+"g fa"};
const norm=s=>s.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
FEEDS.forEach(([id,sec,name])=>{
 const d=DATA[id],p=$("section","panel"),h=$("div","ph"),l=$("div","list");
 h.append($("span","t",name),$("span","c",d.items.length+" titoli"));p.append(h,l);
 if(!d.items.length)l.append($("div","msg","Nessun dato scaricato. "+d.err));
 d.items.forEach(a=>{
  const it=$("div","item"),m=$("div","m"),c=a.k<=2?"g":a.k===3?"a":"r";
  const b=$("span","src "+c,a.s+" "+"🐱".repeat(a.k));b.title="Kitten Bias "+a.k+"/5";
  m.append(b,$("span","",ago(a.ts)));
  const k=$("a","",a.t);k.href=a.u;k.target="_blank";k.rel="noopener noreferrer";
  it.append(m,k);l.append(it);
 });
 document.getElementById("g"+sec).append(p);
});
document.getElementById("stamp").textContent="SCARICATO ALLE "+STAMP;
document.getElementById("q").addEventListener("input",e=>{const q=norm(e.target.value.trim());
 document.querySelectorAll(".item").forEach(i=>i.style.display=!q||norm(i.textContent).includes(q)?"":"none")});
const tick=()=>document.getElementById("clock").textContent=new Date().toLocaleString("it-IT",{weekday:"short",day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit",second:"2-digit"}).toUpperCase();
tick();setInterval(tick,1000);
</script></body></html>"""

def now_it():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Rome"))
    except Exception:
        return datetime.now()

def render(data):
    meta = [[f[0], f[1], f[2]] for f in FEEDS]
    js = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
    return (TEMPLATE.replace("__FEEDS__", js(meta)).replace("__DATA__", js(data))
            .replace("__STAMP__", now_it().strftime("%H:%M")))

def main():
    data = build_data()
    online = bool(os.environ.get("GITHUB_ACTIONS"))
    out = Path("public/index.html") if online else Path(__file__).with_name("sitrep.html")
    out.parent.mkdir(exist_ok=True)
    out.write_text(render(data), encoding="utf-8")
    ok = sum(1 for d in data.values() if d["items"])
    print(f"\nFatto: {ok}/{len(FEEDS)} pannelli con notizie.")
    if ok == 0:
        raise SystemExit("Nessun feed scaricato: pubblicazione annullata.")
    if not online:
        webbrowser.open(out.as_uri())

if __name__ == "__main__":
    main()
