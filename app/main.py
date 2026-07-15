from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .routers import feed, gems, portfolio, proba, power, watch, box, alt, trade, cube, copilot, decklist

app = FastAPI(title="MTG Command Deck API", version="1.0.0")

# ATTENZIONE: allow_origins=["*"] va bene in sviluppo. Prima di un deploy
# pubblico, restringi alle origin reali del tuo frontend/app.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(feed.router, prefix="/api", tags=["feed"])
app.include_router(gems.router, prefix="/api", tags=["gems"])
app.include_router(portfolio.router, prefix="/api", tags=["portfolio"])
app.include_router(proba.router, prefix="/api", tags=["probability"])
app.include_router(power.router, prefix="/api", tags=["power"])
app.include_router(watch.router, prefix="/api", tags=["watch"])
app.include_router(box.router, prefix="/api", tags=["box"])
app.include_router(alt.router, prefix="/api", tags=["alternatives"])
app.include_router(trade.router, prefix="/api", tags=["trade"])
app.include_router(cube.router, prefix="/api", tags=["cube"])
app.include_router(copilot.router, prefix="/api", tags=["copilot"])
app.include_router(decklist.router, prefix="/api", tags=["decklist"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
