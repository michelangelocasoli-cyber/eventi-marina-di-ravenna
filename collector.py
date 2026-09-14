import os, re, sqlite3, requests
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

DB = Path("events.db")
PLACE = os.getenv("EVENT_PLACE", "Marina di Ravenna")
TARGET_DATE = os.getenv("EVENT_DATE", "2026-09-12")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
ACCOUNTS = [
    "donnarosa38","formentera_marinadiravenna","bagnozanzibar",
    "matilda_disco","hookipaeventi","bbk_peasurebeach",
    "singitamarinadiravenna"
]

def search(q, n=10):
    p={"engine":"google","q":q,"api_key":SERPAPI_KEY,"num":n,"hl":"it","gl":"it"}
    r=requests.get("https://serpapi.com/search.json",params=p,timeout=30)
    r.raise_for_status()
    return r.json().get("organic_results", [])

def init():
    con=sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      place TEXT NOT NULL, event_date TEXT NOT NULL, event_time TEXT,
      title TEXT NOT NULL, venue TEXT, category TEXT,
      source_type TEXT, source_name TEXT, url TEXT, snippet TEXT,
      confidence TEXT, first_seen TEXT, last_seen TEXT,
      UNIQUE(place,event_date,title,venue,source_name)
    )""")
    con.commit(); return con

def has_date(text):
    t=text.lower()
    d=datetime.strptime(TARGET_DATE,"%Y-%m-%d")
    names=["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
    pats=[d.strftime("%d/%m/%Y"),d.strftime("%d-%m-%Y"),
          f"{d.day} {names[d.month-1]} {d.year}",
          f"{d.day:02d} {names[d.month-1]} {d.year}"]
    return any(p in t for p in pats)

def get_time(text):
    m=re.search(r'\b(?:[01]?\d|2[0-3])[:.][0-5]\d\b',text)
    return m.group(0).replace(".",":") if m else ""

def classify(text):
    t=text.lower()
    if any(x in t for x in ["dj","party","disco","night","serata"]): return "Nightlife"
    if any(x in t for x in ["concerto","live","music","band"]): return "Musica"
    if any(x in t for x in ["aperitivo","apericena"]): return "Aperitivo"
    if any(x in t for x in ["festival","evento"]): return "Evento"
    return "Altro"

def run():
    if not SERPAPI_KEY:
        raise SystemExit("SERPAPI_KEY non impostata")
    con=init()
    queries=[
      f'"{PLACE}" "{TARGET_DATE[8:10]}/{TARGET_DATE[5:7]}/{TARGET_DATE[:4]}" eventi',
      f'"{PLACE}" "{TARGET_DATE[8:10]} settembre 2026" eventi',
      f'"{PLACE}" "12 settembre 2026" party OR dj OR concerto OR festa',
    ]
    for a in ACCOUNTS:
        queries += [
          f'site:instagram.com/{a} "12 settembre 2026"',
          f'site:instagram.com/{a} "12/09/2026"',
          f'site:instagram.com/{a} "{PLACE}" "12"',
        ]
    now=datetime.utcnow().isoformat()
    for q in queries:
        account=""
        m=re.search(r'site:instagram\.com/([a-z0-9_.]+)',q,re.I)
        if m: account="@"+m.group(1)
        for r in search(q):
            title=re.sub(r"\s+"," ",r.get("title","")).strip()
            snippet=re.sub(r"\s+"," ",r.get("snippet","")).strip()
            url=r.get("link","")
            blob=title+" "+snippet
            if not title or not has_date(blob): continue
            host=urlparse(url).netloc.lower()
            source="Instagram" if account or "instagram." in host else ("Facebook" if "facebook." in host else "Web")
            source_name=account or host
            venue=""
            con.execute("""INSERT INTO events
              (place,event_date,event_time,title,venue,category,source_type,source_name,url,snippet,confidence,first_seen,last_seen)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(place,event_date,title,venue,source_name)
              DO UPDATE SET last_seen=excluded.last_seen,snippet=excluded.snippet,url=excluded.url
            """,(PLACE,TARGET_DATE,get_time(blob),title,venue,classify(blob),
                 source,source_name,url,snippet,"confirmed",now,now))
    con.commit(); con.close()

if __name__=="__main__":
    run()
