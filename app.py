import os, sqlite3
from pathlib import Path
from datetime import date
import streamlit as st
from collector import run, test_serpapi, DEFAULT_ACCOUNTS, SearchError

DB = Path('events.db')
DEFAULT_PLACE = 'Marina di Ravenna'
DEFAULT_DATE = date(2026, 9, 12)

st.set_page_config(page_title='Event Aggregator', page_icon='📍', layout='wide')

if 'calls_used' not in st.session_state:
    st.session_state.calls_used = 0
if 'test_ok' not in st.session_state:
    st.session_state.test_ok = False
if 'last_error' not in st.session_state:
    st.session_state.last_error = ''


def get_key():
    return st.secrets.get('SERPAPI_KEY', os.getenv('SERPAPI_KEY', ''))


def get_events(place, day):
    if not DB.exists():
        return []
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute('''
        SELECT title, event_date, event_time, venue, category,
               source_type, source_name, url, snippet, confidence
        FROM events
        WHERE lower(place)=lower(?) AND event_date=?
        ORDER BY CASE WHEN event_time IS NULL OR event_time='' THEN 1 ELSE 0 END,
                 event_time, title
    ''', (place, day)).fetchall()
    con.close()
    return [dict(r) for r in rows]


st.title('📍 Event Aggregator')
st.caption('Ricerca manuale di eventi sul web · Instagram verrà aggiunto separatamente')
st.info('⚡ Ricerca usa Google Light di SerpAPI: più rapida e adatta a questo aggregatore, che usa solo risultati organici.')

with st.sidebar:
    st.header('Ricerca')
    place = st.text_input('Luogo', DEFAULT_PLACE)
    day = st.date_input('Data', DEFAULT_DATE)
    st.checkbox('Instagram (temporaneamente disattivato)', value=False, disabled=True,
                help='V11: Instagram è disattivato mentre stabilizziamo la ricerca web.')
    search_instagram = False
    mode_label = '💰 Economica — 1 ricerca max'
    mode = 'full' if mode_label.startswith('🔎') else 'economy'
    st.divider()
    st.write('**Account Instagram monitorati**')
    for a in DEFAULT_ACCOUNTS:
        st.write('@' + a)
    st.divider()
    st.caption('Nessun aggiornamento automatico. Nessun retry automatico. Una sola chiamata per ricerca.')

    budget = st.number_input('Budget indicativo crediti SerpAPI', min_value=1, max_value=10000, value=250, step=10)
    st.metric('Chiamate in questa sessione', st.session_state.calls_used)
    st.caption(f'Budget indicativo residuo: {max(0, budget - st.session_state.calls_used)}')

    st.divider()
    if st.button('🧪 Test SerpAPI', use_container_width=True):
        key = get_key()
        if not key:
            st.error('SERPAPI_KEY non configurata in Streamlit → Settings → Secrets.')
            st.session_state.test_ok = False
        else:
            with st.spinner('Test in corso… (1 chiamata)'):
                try:
                    test_serpapi(key)
                    st.session_state.calls_used += 1
                    st.session_state.test_ok = True
                    st.session_state.last_error = ''
                    st.success('SerpAPI risponde correttamente.')
                except SearchError as e:
                    st.session_state.calls_used += 1
                    st.session_state.test_ok = False
                    st.session_state.last_error = str(e)
                    st.error(str(e))

    refresh = st.button('🔎 Cerca / aggiorna eventi', type='primary', use_container_width=True)

if refresh:
    key = get_key()
    if not key:
        st.error('SERPAPI_KEY non configurata in Streamlit → Settings → Secrets.')
    elif st.session_state.calls_used >= budget:
        st.error('Budget indicativo raggiunto. Non viene effettuata alcuna chiamata.')
    else:
        max_calls = 8 if mode == 'full' and search_instagram else 1
        if mode == 'economy' and search_instagram:
            max_calls = 2
        if st.session_state.calls_used + max_calls > budget:
            st.warning(f'Questa ricerca può usare fino a {max_calls} chiamate e supererebbe il budget indicativo di {budget}. Nessuna chiamata effettuata.')
        else:
            with st.spinner('Ricerca in corso…'):
                try:
                    analyzed, queries = run(place, day.isoformat(), search_instagram=search_instagram, api_key=key, mode=mode)
                    st.session_state.calls_used += queries
                    st.session_state.test_ok = True
                    st.session_state.last_error = ''
                    st.success(f'Ricerca completata: {analyzed} risultati analizzati con {queries} chiamate SerpAPI.')
                except SearchError as e:
                    # A timeout/error may or may not have reached SerpAPI; count the attempted calls conservatively.
                    attempted = getattr(e, 'attempted_calls', 1)
                    st.session_state.calls_used += attempted
                    st.session_state.last_error = str(e)
                    st.error(str(e))
                except Exception as e:
                    st.error(f'Errore durante la ricerca: {e}')

if st.session_state.last_error:
    st.info('Consiglio: non premere ripetutamente il pulsante. Se il problema persiste, aspetta qualche minuto e usa prima il Test SerpAPI.')

events = get_events(place, day.isoformat())
st.subheader(f'{place} — {day.strftime("%d/%m/%Y")}')
st.caption('I risultati vengono filtrati sulla data scelta e deduplicati nel database locale.')

if not events:
    st.info("Nessun evento archiviato. Usa prima 'Test SerpAPI' oppure 'Cerca / aggiorna eventi'.")
else:
    c1, c2, c3 = st.columns(3)
    c1.metric('Eventi', len(events))
    c2.metric('Confermati', sum(e['confidence'] == 'confirmed' for e in events))
    c3.metric('Instagram', sum('Instagram' in (e['source_type'] or '') for e in events))
    for e in events:
        with st.container(border=True):
            left, right = st.columns([6, 1])
            with left:
                st.markdown('### ' + e['title'])
                meta = []
                if e['event_time']: meta.append('🕒 ' + e['event_time'])
                if e['venue']: meta.append('📍 ' + e['venue'])
                if e['category']: meta.append('🏷️ ' + e['category'])
                if e['source_type']: meta.append(e['source_type'])
                st.write(' · '.join(meta))
                if e['snippet']: st.caption(e['snippet'])
                st.write('🟢 Confermato' if e['confidence'] == 'confirmed' else '🟡 Da verificare')
            with right:
                if e['url']:
                    st.link_button('Fonte', e['url'])

st.divider()
st.caption('Ricerca esclusivamente manuale. Il contatore è locale alla sessione e serve come protezione indicativa: il consumo reale dipende dal tuo piano SerpAPI.')
