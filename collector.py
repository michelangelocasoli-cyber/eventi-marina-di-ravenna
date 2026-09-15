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
            timeout=(5, 30),
        )
    except requests.Timeout as e:
        raise SearchError('SerpAPI Google Light non ha risposto entro 30 secondi. Nessun retry automatico.', 1) from e
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


def fetch_page_text(url):
    """Fetch the original source page without using SerpAPI. Best-effort only."""
    if not url or not url.startswith(('http://', 'https://')):
        return ''
    try:
        r = requests.get(url, headers={'User-Agent':'Mozilla/5.0 (compatible; EventAggregator/1.0)'}, timeout=(4, 8), allow_redirects=True)
        if not r.ok:
            return ''
        text = re.sub(r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>', ' ', r.text, flags=re.I|re.S)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&nbsp;|&#160;', ' ', text, flags=re.I)
        text = re.sub(r'\s+', ' ', text)
        return text[:250000]
    except requests.RequestException:
        return ''


def explicit_date_status(text, target_date):
    """Return confirmed / wrong / unknown based on dates visible in source text."""
    if not text:
        return 'unknown'
    d = datetime.strptime(target_date, '%Y-%m-%d')
    t = text.lower()
    target_patterns = [
        rf'\b{d.day:02d}[/-]{d.month:02d}[/-]{d.year}\b',
        rf'\b{d.day}[/-]{d.month:02d}[/-]{str(d.year)[2:]}\b',
        rf'\b{d.day}\s+{date_terms(target_date)[1].split(" ",1)[1]}\b',
        rf'\b{d.day:02d}\s+{date_terms(target_date)[1].split(" ",1)[1]}\b',
    ]
    if any(re.search(p, t, re.I) for p in target_patterns):
        return 'confirmed'
    # Find explicit full numeric dates or Italian month dates and reject if they are different.
    months = '|'.join(['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre'])
    found = []
    for m in re.finditer(r'\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b', t):
        day_n, mon_n, year_n = m.group(1), m.group(2), m.group(3)
        if year_n:
            y = int(year_n); y += 2000 if y < 100 else 0
        else:
            y = d.year
        try:
            found.append(datetime(y, int(mon_n), int(day_n)).date())
        except ValueError:
            pass
    for m in re.finditer(r'\b(\d{1,2})\s+(' + months + r')\s+(\d{4})\b', t, re.I):
        month_map={x:i+1 for i,x in enumerate(['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre'])}
        try: found.append(datetime(int(m.group(3)), month_map[m.group(2).lower()], int(m.group(1))).date())
        except ValueError: pass
    if found and d.date() not in found:
        return 'wrong'
    return 'unknown'

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
        # Verify the original page. Google snippets alone are not reliable for the requested date.
        source_text = fetch_page_text(url)
        status = explicit_date_status(source_text, target_date)
        if status == 'unknown':
            status = 'confirmed' if has_date(blob, target_date) else 'probable'
        if status == 'wrong':
            # Do not show a result whose original source clearly refers to another date.
            continue
        explicit_date = status == 'confirmed'
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


def instagram_account_from_url(url, accounts):
    try:
        parsed = urlparse(url)
        if 'instagram.com' not in parsed.netloc.lower():
            return ''
        parts = [p for p in parsed.path.split('/') if p]
        if not parts:
            return ''
        candidate = parts[0].lower().lstrip('@')
        for account in accounts:
            if candidate == account.lower():
                return account
    except Exception:
        pass
    return ''


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
        # One general web search.
        q_web = f'{place} eventi {date_label}'
        analyzed += _store_results(con, place, target_date, serpapi_request(q_web, api_key, n=5))
        queries_used += 1

        # One combined Instagram search for all monitored accounts. This keeps the
        # economy mode at a maximum of 2 SerpAPI calls, not one call per account.
        if search_instagram:
            account_terms = ' OR '.join(f'"{a}"' for a in accounts)
            q_ig = f'{place} {date_label} Instagram ({account_terms})'
            ig_results = serpapi_request(q_ig, api_key, n=10)
            # Keep only Instagram results and attribute each result to the account
            # when its URL exposes the profile name.
            for r in ig_results:
                url = r.get('link', '')
                account = instagram_account_from_url(url, accounts)
                if 'instagram.com' not in urlparse(url).netloc.lower():
                    continue
                analyzed += _store_results(con, place, target_date, [r], account=account)
            queries_used += 1

        con.commit()
    finally:
        con.close()
    return analyzed, queries_used
