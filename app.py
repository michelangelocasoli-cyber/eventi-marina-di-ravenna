import json, sqlite3, os
from pathlib import Path
import streamlit as st

DB = Path("events.db")
st.set_page_config(page_title="Event Aggregator", page_icon="📍", layout="wide")

DEFAULT_PLACE = "Marina di Ravenna"
DEFAULT_DATE = "2026-09-12"

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
st.caption("Archivio eventi per luogo e data · Web + Instagram pubblicamente indicizzati")

with st.sidebar:
    place = st.text_input("Luogo", DEFAULT_PLACE)
    day = st.date_input("Data")
    st.divider()
    st.write("**Fonti Instagram monitorate**")
    for a in [
        "donnarosa38","formentera_marinadiravenna","bagnozanzibar",
        "matilda_disco","hookipaeventi","bbk_peasurebeach",
        "singitamarinadiravenna"
    ]:
        st.write("@" + a)

events = get_events(place, day.isoformat())

st.subheader(f"{place} — {day.strftime('%d/%m/%Y')}")
if not events:
    st.info("Nessun evento archiviato per questa combinazione. Esegui il collector per aggiornare le fonti.")
else:
    c1,c2,c3 = st.columns(3)
    c1.metric("Eventi", len(events))
    c2.metric("Confermati", sum(e["confidence"]=="confirmed" for e in events))
    c3.metric("Instagram", sum("Instagram" in (e["source_type"] or "") for e in events))

    for e in events:
        with st.container(border=True):
            left, right = st.columns([6,1])
            with left:
                st.markdown("### " + e["title"])
                meta = []
                if e["event_time"]: meta.append("🕒 " + e["event_time"])
                if e["venue"]: meta.append("📍 " + e["venue"])
                if e["category"]: meta.append("🏷️ " + e["category"])
                if e["source_type"]: meta.append(e["source_type"])
                st.write(" · ".join(meta))
                if e["snippet"]: st.caption(e["snippet"])
                st.write("🟢 Confermato" if e["confidence"]=="confirmed" else "🟡 Da verificare")
            with right:
                if e["url"]:
                    st.link_button("Fonte", e["url"])

st.divider()
st.caption("Il collector salva lo storico in SQLite. L'app mostra i risultati senza rifare la ricerca a ogni apertura.")
