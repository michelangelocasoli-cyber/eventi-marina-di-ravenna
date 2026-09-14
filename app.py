import os, sqlite3
from pathlib import Path
import streamlit as st
from collector import run, DEFAULT_ACCOUNTS

DB = Path("events.db")
DEFAULT_PLACE = "Marina di Ravenna"
DEFAULT_DATE = __import__('datetime').date(2026, 9, 12)

st.set_page_config(page_title="Event Aggregator", page_icon="📍", layout="wide")

def get_events(place, day):
    if not DB.exists():
        return []
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        SELECT title, event_date, event_time, venue, category,
               source_type, source_name, url, snippet, confidence
        FROM events
        WHERE lower(place)=lower(?) AND event_date=?
        ORDER BY CASE WHEN event_time IS NULL OR event_time='' THEN 1 ELSE 0 END,
                 event_time, title
    """, (place, day)).fetchall()
    con.close()
    return [dict(r) for r in rows]

st.title("📍 Event Aggregator")
st.caption("Ricerca manuale di eventi · Web + Instagram pubblicamente indicizzati")

with st.sidebar:
    place = st.text_input("Luogo", DEFAULT_PLACE)
    day = st.date_input("Data", DEFAULT_DATE)
    st.divider()
    st.write("**Fonti Instagram monitorate**")
    for a in DEFAULT_ACCOUNTS:
        st.write("@" + a)
    st.divider()
    st.warning("Nessun aggiornamento automatico. I crediti SerpAPI vengono consumati solo quando avvii una ricerca.")
    search_instagram = st.checkbox("Cerca anche Instagram", value=True)
    mode_label = st.radio(
        "Modalità di ricerca",
        ["💰 Economica — 2 ricerche max", "🔎 Completa — 8 ricerche max"],
        index=0,
        help="Economica: 1 ricerca web + 1 ricerca Instagram combinata. Completa: 1 web + 1 per ciascuno dei 7 account."
    )
    mode = "full" if mode_label.startswith("🔎") else "economy"
    refresh = st.button("🔎 Cerca / aggiorna eventi", type="primary", use_container_width=True)

if refresh:
    key = st.secrets.get("SERPAPI_KEY", os.getenv("SERPAPI_KEY", ""))
    if not key:
        st.error("SERPAPI_KEY non configurata in Streamlit → Settings → Secrets.")
    else:
        with st.spinner("Ricerca in corso…"):
            try:
                analyzed, queries = run(place, day.isoformat(), search_instagram=search_instagram, api_key=key, mode=mode)
                st.success(f"Ricerca completata: {analyzed} risultati analizzati con {queries} chiamate SerpAPI.")
            except Exception as e:
                st.error(f"Errore durante la ricerca: {e}")

events = get_events(place, day.isoformat())

st.subheader(f"{place} — {day.strftime('%d/%m/%Y')}")
if not events:
    st.info("Nessun evento archiviato. Premi 'Cerca / aggiorna eventi' per effettuare una ricerca manuale.")
else:
    c1, c2, c3 = st.columns(3)
    c1.metric("Eventi", len(events))
    c2.metric("Confermati", sum(e["confidence"] == "confirmed" for e in events))
    c3.metric("Instagram", sum("Instagram" in (e["source_type"] or "") for e in events))

    for e in events:
        with st.container(border=True):
            left, right = st.columns([6, 1])
            with left:
                st.markdown("### " + e["title"])
                meta = []
                if e["event_time"]: meta.append("🕒 " + e["event_time"])
                if e["venue"]: meta.append("📍 " + e["venue"])
                if e["category"]: meta.append("🏷️ " + e["category"])
                if e["source_type"]: meta.append(e["source_type"])
                st.write(" · ".join(meta))
                if e["snippet"]: st.caption(e["snippet"])
                st.write("🟢 Confermato" if e["confidence"] == "confirmed" else "🟡 Da verificare")
            with right:
                if e["url"]:
                    st.link_button("Fonte", e["url"])

st.divider()
st.caption("Aggiornamento esclusivamente manuale. Modalità economica: massimo 2 chamadas SerpAPI per ricerca (1 web + 1 Instagram combinata). Modalità completa: massimo 8.")
