# Event Aggregator v7

App Streamlit per cercare manualmente eventi a Marina di Ravenna (o altri luoghi), usando Google tramite SerpAPI e contenuti Instagram pubblicamente indicizzati.

## Caratteristiche
- Nessun aggiornamento automatico.
- Nessun retry automatico.
- Test SerpAPI separato: **1 chiamata reale**, quindi 1 credito di ricerca.
- Modalità economica: massimo 2 chiamate per una ricerca (web + Instagram combinata).
- Modalità completa: massimo 8 chiamate (web + 7 account Instagram).
- Contatore delle chiamate nella sessione e budget indicativo configurabile.

## Streamlit Secrets
Impostare in Settings → Secrets:

```toml
SERPAPI_KEY = "la_tua_chiave"
```

## Nota sui crediti
Il test SerpAPI è una vera query Google e può consumare un credito. Il contatore dell'app è locale alla sessione e non sostituisce il contatore ufficiale del proprio account SerpAPI.


## v8 – correzione località Italia
La versione v8 rimuove il parametro `location=Ravenna, Italy`, che SerpApi ha segnalato come temporaneamente poco affidabile per località fuori dagli USA. Usa `gl=it`, `hl=it` e `google_domain=google.it`. Inoltre evita gli operatori Google `site:` nelle query Instagram, che possono causare timeout intermittenti.
