import os, re, sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import serpapi

DB = Path("events.db")
DEFAULT_ACCOUNTS = [
    "donnarosa38", "formentera_marinadiravenna", "bagnozanzibar",
    "matilda_disco", "hookipaeventi", "bbk_peasurebeach",
    "singitamarinadiravenna"
]

class SearchError(RuntimeError):
    pass


def search(q, api_key, n=10):
    """Single SerpApi request, deliberately without automatic retries.

    We avoid automatic retries because the user has a limited monthly search quota.
    The official SerpApi client is used with a short timeout so a network problem
    does not leave Streamlit waiting for 30 seconds.
    """
    try:
        client = serpapi.Client(api_key=api_key, timeout=12)
        data = client.search({
            "engine": "google",
            "q": q,
            "num": n,
            "hl": "it",
            "gl": "it",
            "location": "Ravenna, Italy",
        })
        # SerpResults behaves like a dict, but converting makes this robust across SDK versions.
        data = dict(data)
    except Exception as e:
        msg = str(e)
        if "timeout" in msg.lower() or "timed out" in msg.lower():
            raise SearchError(
                "SerpAPI non ha risposto entro 12 secondi. "
                "Non viene effettuato alcun tentativo automatico, per non consumare altri crediti."
            ) from e
        raise SearchError(f"SerpAPI: {msg}") from e

    if data.get("error"):
        raise SearchError(f"SerpAPI: {data['error']}")
    status = data.get("search_metadata", {}).get("status")
    if status == "Error":
        raise SearchError(f"SerpAPI: {data.get('error', 'ricerca non riuscita')}")
    return data.get("organic_results", [])


def init():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      place TEXT NOT NULL, event_date TEXT NOT NULL, event_time TEXT,
      title TEXT NOT NULL, venue TEXT, category TEXT,
      source_type TEXT, source_name TEXT, url TEXT, snippet TEXT,
      confidence TEXT, first_seen TEXT, last_seen TEXT,
      UNIQUE(place,event_date,title,venue,source_name)
    )""")
    con.commit()
    return con


def date_terms(target_date):
    d = datetime.strptime(target_date, "%Y-%m-%d")
    names = ["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
    return [d.strftime("%d/%m/%Y"), f"{d.day} {names[d.month-1]} {d.year}"]


def has_date(text, target_date):
    t = text.lower()
    d = datetime.strptime(target_date, "%Y-%m-%d")
    terms = date_terms(target_date)
    terms += [f"{d.day:02d} {terms[1].split(' ', 1)[1]}", d.strftime("%d-%m-%Y")]
    return any(p.lower() in t for p in terms)


def get_time(text):
    m = re.search(r'\b(?:[01]?\d|2[0-3])[:.][0-5]\d\b', text)
    return m.group(0).replace(".", ":") if m else ""


def classify(text):
    t = text.lower()
    if any(x in t for x in ["dj", "party", "disco", "night", "serata"]): return "Nightlife"
    if any(x in t for x in ["concerto", "live", "music", "band"]): return "Musica"
    if any(x in t for x in ["aperitivo", "apericena"]): return "Aperitivo"
    if any(x in t for x in ["festival", "evento"]): return "Evento"
    return "Altro"


def _store_results(con, place, target_date, results, account=""):
    now = datetime.utcnow().isoformat()
    analyzed = 0
    for r in results:
        analyzed += 1
        title = re.sub(r"\s+", " ", r.get("title", "")).strip()
        snippet = re.sub(r"\s+", " ", r.get("snippet", "")).strip()
        url = r.get("link", "")
        blob = title + " " + snippet
        if not title or not has_date(blob, target_date):
            continue
        host = urlparse(url).netloc.lower()
        source = "Instagram" if account or "instagram." in host else ("Facebook" if "facebook." in host else "Web")
        source_name = account or host
        con.execute("""INSERT INTO events
          (place,event_date,event_time,title,venue,category,source_type,source_name,url,snippet,confidence,first_seen,last_seen)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(place,event_date,title,venue,source_name)
          DO UPDATE SET last_seen=excluded.last_seen,snippet=excluded.snippet,url=excluded.url
        """, (place, target_date, get_time(blob), title, "", classify(blob), source,
              source_name, url, snippet, "confirmed", now, now))
    return analyzed


def run(place, target_date, search_instagram=True, api_key=None, accounts=None, mode="economy"):
    """Manual search only. No scheduled or automatic requests.

    economy: 2 SerpAPI searches max (one web + one combined Instagram search).
    full: 1 web search + 1 search per Instagram account.
    """
    api_key = api_key or os.getenv("SERPAPI_KEY", "")
    if not api_key:
        raise RuntimeError("SERPAPI_KEY non impostata")
    accounts = accounts or DEFAULT_ACCOUNTS
    con = init()
    analyzed = 0
    queries_used = 0
    date_label = date_terms(target_date)[1]

    try:
        q_web = f'"{place}" "{date_label}" eventi party concerto musica'
        analyzed += _store_results(con, place, target_date, search(q_web, api_key, n=8))
        queries_used += 1

        if search_instagram and accounts:
            if mode == "full":
                for a in accounts:
                    q = f'site:instagram.com/{a} "{date_label}"'
                    analyzed += _store_results(con, place, target_date, search(q, api_key, n=8), account="@" + a)
                    queries_used += 1
            else:
                sites = " OR ".join(f'site:instagram.com/{a}' for a in accounts)
                q = f'({sites}) "{date_label}"'
                analyzed += _store_results(con, place, target_date, search(q, api_key, n=10), account="Instagram (ricerca compatta)")
                queries_used += 1
        con.commit()
    finally:
        con.close()
    return analyzed, queries_used
