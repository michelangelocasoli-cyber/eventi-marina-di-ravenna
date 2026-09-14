import os, re, sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import requests

DB = Path('events.db')
DEFAULT_ACCOUNTS = [
    'donnarosa38', 'formentera_marinadiravenna', 'bagnozanzibar',
    'matilda_disco', 'hookipaeventi', 'bbk_peasurebeach',
    'singitamarinadiravenna'
]

class SearchError(RuntimeError):
    def __init__(self, message, attempted_calls=1):
        super().__init__(message)
        self.attempted_calls = attempted_calls


def serpapi_request(q, api_key, n=5):
    """One and only one SerpAPI HTTP request. No retries."""
    try:
        r = requests.get(
            'https://serpapi.com/search.json',
            params={
                'engine': 'google_light', 'q': q, 'num': min(n, 10),
                'hl': 'it', 'gl': 'it', 'google_domain': 'google.it',
                'api_key': api_key,
            },
            timeout=(5, 15),
        )
    except requests.Timeout as e:
        raise SearchError('SerpAPI Google Light non ha risposto entro 15 secondi. Nessun retry automatico.', 1) from e
    except requests.RequestException as e:
        raise SearchError(f'Impossibile raggiungere SerpAPI: {e}', 1) from e

    if r.status_code == 401:
        raise SearchError('SerpAPI ha rifiutato la chiave API (401). Controlla SERPAPI_KEY.', 1)
    if r.status_code == 429:
        raise SearchError('SerpAPI ha restituito 429: limite/quota raggiunto. Nessun altro tentativo automatico.', 1)
    if r.status_code >= 500:
        raise SearchError(f'SerpAPI ha restituito un errore server ({r.status_code}). Riprova più tardi, senza retry automatici.', 1)
    if not r.ok:
        raise SearchError(f'SerpAPI ha restituito HTTP {r.status_code}: {r.text[:200]}', 1)

    try:
        data = r.json()
    except ValueError as e:
        raise SearchError('Risposta SerpAPI non valida.', 1) from e
    if data.get('error'):
        raise SearchError(f"SerpAPI: {data['error']}", 1)
    return data.get('organic_results', [])


def test_serpapi(api_key):
    """Minimal real Google query; it consumes one SerpAPI search credit."""
    return serpapi_request('Marina di Ravenna eventi', api_key, n=3)


def init():
    con = sqlite3.connect(DB)
    con.execute('''CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      place TEXT NOT NULL, event_date TEXT NOT NULL, event_time TEXT,
      title TEXT NOT NULL, venue TEXT, category TEXT,
      source_type TEXT, source_name TEXT, url TEXT, snippet TEXT,
      confidence TEXT, first_seen TEXT, last_seen TEXT,
      UNIQUE(place,event_date,title,venue,source_name)
    )''')
    con.commit()
    return con


def date_terms(target_date):
    d = datetime.strptime(target_date, '%Y-%m-%d')
    names = ['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre']
    return [d.strftime('%d/%m/%Y'), f'{d.day} {names[d.month-1]} {d.year}']


def has_date(text, target_date):
    t = text.lower()
    d = datetime.strptime(target_date, '%Y-%m-%d')
    terms = date_terms(target_date)
    terms += [f'{d.day:02d} {terms[1].split(" ", 1)[1]}', d.strftime('%d-%m-%Y')]
    return any(p.lower() in t for p in terms)


def get_time(text):
    m = re.search(r'\b(?:[01]?\d|2[0-3])[:.][0-5]\d\b', text)
    return m.group(0).replace('.', ':') if m else ''


def extract_venue(text, place):
    # Conservative extraction from common Italian event wording.
    patterns = [
        r'\b(?:presso|al|alla|allo|agli|alle|@)\s+([A-ZÀ-ÖØ-Ý][^.!?\n]{2,60})',
        r'\b(?:location|locale)\s*[:\-]\s*([A-ZÀ-ÖØ-Ý][^.!?\n]{2,60})',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            v = re.sub(r'\s+', ' ', m.group(1)).strip(' ,;:-')
            if v and place.lower() not in v.lower():
                return v
    return ''

def extract_price(text):
    patterns = [
        r'(?:ingresso|entrata|ticket|biglietto|prezzo)\s*(?:[:\-]?\s*)?(€\s*\d+(?:[,.]\d{1,2})?)',
        r'(€\s*\d+(?:[,.]\d{1,2})?)',
        r'(\d+(?:[,.]\d{1,2})?\s*€)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1).strip()
    if re.search(r'\bingresso\s+gratuito\b|\bfree entry\b', text, re.I):
        return 'Gratuito'
    return ''

def extract_artist(text):
    patterns = [
        r'(?:con|live|dj set|dj|special guest)\s*[:\-]?\s*([A-ZÀ-ÖØ-Ý][^.!?\n]{2,70})',
        r'\b([A-Z][A-Za-zÀ-ÖØ-öø-ÿ&\' .-]{2,40}\s(?:live|band|dj))\b',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            value = re.sub(r'\s+', ' ', m.group(1)).strip(' ,;:-')
            if value and len(value) < 80:
                return value
    return ''

def classify(text):
    t = text.lower()
    if any(x in t for x in ['dj','party','disco','night','serata']): return 'Nightlife'
    if any(x in t for x in ['concerto','live','music','band']): return 'Musica'
    if any(x in t for x in ['aperitivo','apericena']): return 'Aperitivo'
    if any(x in t for x in ['festival','evento']): return 'Evento'
    return 'Altro'


def _store_results(con, place, target_date, results, account=''):
    now = datetime.utcnow().isoformat()
    analyzed = 0
    for r in results:
        analyzed += 1
        title = re.sub(r'\s+', ' ', r.get('title', '')).strip()
        snippet = re.sub(r'\s+', ' ', r.get('snippet', '')).strip()
        url = r.get('link', '')
        blob = title + ' ' + snippet
        if not title:
            continue
        # Google may omit the date from the title/snippet even when the result
        # was returned for a date-specific query. Keep the result and mark it
        # as needing verification instead of silently discarding it.
        explicit_date = has_date(blob, target_date)
        host = urlparse(url).netloc.lower()
        source = 'Instagram' if account or 'instagram.' in host else ('Facebook' if 'facebook.' in host else 'Web')
        source_name = account or host
        venue = extract_venue(blob, place)
        price = extract_price(blob)
        artist = extract_artist(blob)
        enriched = snippet
        extras = []
        if artist: extras.append('Artista/DJ: ' + artist)
        if price: extras.append('Prezzo: ' + price)
        if extras: enriched = enriched + (' · ' if enriched else '') + ' · '.join(extras)
        con.execute('''INSERT INTO events
          (place,event_date,event_time,title,venue,category,source_type,source_name,url,snippet,confidence,first_seen,last_seen)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(place,event_date,title,venue,source_name)
          DO UPDATE SET last_seen=excluded.last_seen,snippet=excluded.snippet,url=excluded.url
        ''', (place, target_date, get_time(blob), title, venue, classify(blob), source,
              source_name, url, enriched, 'confirmed' if explicit_date else 'probable', now, now))
    return analyzed


def run(place, target_date, search_instagram=True, api_key=None, accounts=None, mode='economy'):
    api_key = api_key or os.getenv('SERPAPI_KEY', '')
    if not api_key:
        raise SearchError('SERPAPI_KEY non impostata', 0)
    accounts = accounts or DEFAULT_ACCOUNTS
    con = init()
    analyzed = 0
    queries_used = 0
    date_label = date_terms(target_date)[1]
    try:
        q_web = f'{place} eventi {date_label}'
        analyzed += _store_results(con, place, target_date, serpapi_request(q_web, api_key, n=5))
        queries_used += 1
        # Instagram intentionally disabled in v11: stabilize the web search first.
        con.commit()
    finally:
        con.close()
    return analyzed, queries_used
