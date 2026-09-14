# Event Aggregator — Marina di Ravenna v12

Versione stabile con ricerca manuale tramite SerpAPI Google Light.

## Caratteristiche
- Una sola chiamata SerpAPI per ricerca web.
- Nessun aggiornamento automatico e nessun retry.
- Filtraggio dei risultati sulla data selezionata.
- Deduplicazione tramite SQLite.
- Estrazione prudente di orario, locale, artista/DJ e prezzo quando presenti nel titolo/snippet.
- Instagram volutamente separato e non attivo in questa versione.

## Streamlit Cloud
Imposta il secret:

```toml
SERPAPI_KEY = "la_tua_chiave"
```

File principale: `app.py`.
