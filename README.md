# MTG Command Deck — Backend (FastAPI)

API REST che centralizza tutte le chiamate a Scryfall e la persistenza
(portfolio, collezione, scambi, snapshot prezzi) su SQLite. Pensata per
essere l'unico backend condiviso da: frontend web, futura app Android,
futura app iOS.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Avvio (sviluppo)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Documentazione interattiva (Swagger UI): http://localhost:8000/docs

## Note

- Il database SQLite `data.db` viene creato automaticamente al primo avvio.
- Le chiamate a Scryfall sono cachate in memoria per 1 ora, per rispettare i rate limit.
- CORS è aperto a tutte le origin di default — restringi `allow_origins` in
  `app/main.py` prima di un deploy pubblico.
- Per far raggiungere questo backend da un'app mobile reale (non emulatore
  locale), va **deployato** su un host raggiungibile da internet (Render,
  Railway, Fly.io, un VPS, ecc.) — `localhost` funziona solo sulla stessa
  macchina o su un emulatore configurato per instradarci.
- Identificazione utente: al momento è un semplice `user_id` generato lato
  client e passato come query param — va bene per un prototipo personale,
  ma prima di un rilascio pubblico multi-utente serve un vero sistema di
  autenticazione (es. OAuth, JWT).
