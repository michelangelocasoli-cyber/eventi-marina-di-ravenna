# Event Aggregator v6 — Marina di Ravenna

Versione manuale e a basso consumo di SerpAPI.

- Nessun aggiornamento automatico.
- Modalità economica: massimo 2 ricerche per avvio (1 web + 1 Instagram combinata).
- Modalità completa: massimo 8 ricerche.
- Usa il client ufficiale SerpApi con timeout di 12 secondi.
- Nessun retry automatico: un timeout non genera una seconda chiamata involontaria.

## Streamlit Secrets

Impostare `SERPAPI_KEY` in Settings → Secrets:

```toml
SERPAPI_KEY = "la-tua-chiave"
```
