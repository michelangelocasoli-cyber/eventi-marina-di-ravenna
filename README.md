# Event Aggregator Marina di Ravenna — v20

## Novità importante
La ricerca Instagram diretta è ora **separata da SerpAPI**.

- `🔎 Cerca / aggiorna eventi` = web + Instagram tramite SerpAPI (consuma crediti).
- `📱 Cerca direttamente su Instagram` = usa la sessione Instagram configurata nei Secrets di Streamlit e **non usa SerpAPI**.
- I profili nella sidebar restano cliccabili.

## Configurazione Streamlit Secrets
In Streamlit → Settings → Secrets:

```toml
SERPAPI_KEY = "..."
INSTAGRAM_SESSIONID = "..."
INSTAGRAM_CSRF_TOKEN = "..."
```

Il `sessionid` è una credenziale sensibile: non inserirlo in GitHub e non inviarlo in chat.

## Importante
Instagram può rifiutare richieste automatizzate o cambiare gli endpoint web. La v20 mostra chiaramente l'errore della ricerca diretta invece di ricadere su SerpAPI.
