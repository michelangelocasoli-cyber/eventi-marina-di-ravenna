# Event Aggregator Marina di Ravenna — v10

Versione manuale ed economica dell'aggregatore.

- Nessun aggiornamento automatico.
- Nessun retry automatico.
- Google Light tramite SerpAPI.
- Modalità economica: massimo 2 chiamate (1 web + 1 Instagram combinata).
- Modalità completa: massimo 8 chiamate (1 web + 7 account Instagram).
- I risultati vengono identificati come Instagram solo quando il link restituito è realmente su Instagram; questo evita di etichettare erroneamente risultati web come Instagram.
- Il test SerpAPI consuma 1 ricerca.

## Streamlit Secrets

Impostare `SERPAPI_KEY` nei Secrets dell'app Streamlit.
