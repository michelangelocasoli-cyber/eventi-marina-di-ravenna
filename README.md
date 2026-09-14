# Event Aggregator — Marina di Ravenna

App Streamlit per cercare manualmente eventi per luogo e data usando Google tramite SerpAPI, inclusi risultati Instagram pubblicamente indicizzati.

## Ricerca manuale e risparmio crediti
Non esiste alcun aggiornamento automatico. La ricerca parte esclusivamente quando l'utente preme **Cerca / aggiorna eventi**.

Sono disponibili due modalità:
- **Economica:** massimo 2 chiamate SerpAPI (1 web + 1 ricerca Instagram combinata). È la modalità consigliata per risparmiare crediti.
- **Completa:** massimo 8 chiamate (1 web + 1 per ciascuno dei 7 account Instagram).

Se **Cerca anche Instagram** è disattivato, viene fatta una sola chiamata web.

## Streamlit Secrets
In Streamlit → Settings → Secrets:

```toml
SERPAPI_KEY = "la_tua_chiave"
```

## Deploy
- Repository GitHub
- Main file: `app.py`
- Python dependencies: `requirements.txt`

## Nota Instagram
La ricerca Instagram usa contenuti pubblicamente indicizzati nei risultati Google; non è uno scraping diretto dell'account Instagram.
