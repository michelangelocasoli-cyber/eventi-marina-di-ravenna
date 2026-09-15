# Event Aggregator Marina di Ravenna — V19

Questa versione mantiene la ricerca Web + Instagram via SerpAPI e aggiunge una modalità **Instagram autenticato**, che non usa crediti SerpAPI.

## Configurazione sicura
NON inserire username/password Instagram nel codice o in GitHub.

In Streamlit Cloud → Settings → Secrets aggiungere:

```toml
INSTAGRAM_SESSIONID = "..."
# opzionale
INSTAGRAM_CSRF_TOKEN = "..."
```

`INSTAGRAM_SESSIONID` è una credenziale sensibile: trattala come una password e non condividerla in chat, GitHub o screenshot.

La modalità autenticata usa il cookie di sessione solo in memoria per leggere i profili configurati e non lo salva nel database `events.db`.

La modalità è best-effort: Instagram può richiedere verifiche, cambiare endpoint o limitare richieste automatizzate. Se Instagram risponde con blocco/401, l'app lo segnala senza fare retry automatici.

## Profili monitorati
- donnarosa38
- formentera_marinadiravenna
- bagnozanzibar
- matilda_disco
- hookipaeventi
- bbk_peasurebeach
- singitamarinadiravenna

## SerpAPI
La ricerca Web + Instagram via SerpAPI continua a funzionare come prima. La modalità autenticata Instagram è separata e non consuma crediti SerpAPI.
