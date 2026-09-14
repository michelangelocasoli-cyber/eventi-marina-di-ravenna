# Event Aggregator v3

Versione con **archivio SQLite + collector automatico + aggiornamento GitHub Actions**.

## Cosa contiene

- `app.py` — interfaccia Streamlit
- `collector.py` — motore di raccolta
- `events.db` — database storico creato al primo avvio
- `.github/workflows/update-events.yml` — aggiornamento automatico giornaliero
- `requirements.txt`

## Configurazione iniziale

Luogo: Marina di Ravenna
Data: 12/09/2026

Account Instagram:
@donnarosa38
@formentera_marinadiravenna
@bagnozanzibar
@matilda_disco
@hookipaeventi
@bbk_peasurebeach
@singitamarinadiravenna

## Avvio locale

pip install -r requirements.txt
streamlit run app.py

Per aggiornare i dati:

set SERPAPI_KEY=LA_TUA_CHIAVE
python collector.py

Su macOS/Linux:
export SERPAPI_KEY=LA_TUA_CHIAVE
python collector.py

## Aggiornamento automatico

Il workflow GitHub Actions esegue il collector ogni giorno alle 06:30 UTC e salva il database nel repository.

Per usarlo:
1. carica i file in un repository GitHub;
2. crea il secret `SERPAPI_KEY`;
3. abilita GitHub Actions;
4. deploya `app.py` su Streamlit Community Cloud.

Streamlit documenta il deploy tramite GitHub e l'uso dei secrets. L'app può essere pubblicata su un sottodominio `streamlit.app`.

## Limite Instagram

Il collector non accede a contenuti privati e non aggira login o protezioni. Cerca contenuti pubblicamente indicizzati. Per un accesso diretto agli account servono le API/autorizzazioni ufficiali Meta quando applicabili.

## Prossimo livello

- riconoscimento AI di titolo, locale, artista, prezzo;
- deduplicazione semantica più forte;
- fonti Facebook;
- notifiche quando appare un nuovo evento;
- supporto a più città/date salvate;
- pannello per aggiungere/rimuovere account senza modificare il codice.
