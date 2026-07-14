from fastapi import APIRouter, Query
from .. import scryfall_client as sf
from ..database import get_conn
from ..utils import price_num

router = APIRouter()


@router.get("/feed")
async def get_feed(profile: str = Query("commander"), user_id: str = Query(...)):
    latest = await sf.latest_set()
    if not latest:
        return {"error": "Nessun set trovato."}

    cards = await sf.search(f"set:{latest['code']} legal:{profile}", order="released")
    cards = cards[:40]

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT card_name, price FROM feed_snapshots WHERE user_id=? AND profile=?",
        (user_id, profile),
    )
    prev = {row["card_name"]: row["price"] for row in cur.fetchall()}

    rows = []
    for c in cards:
        p = price_num(c)
        old = prev.get(c["name"])
        delta_pct = round((p - old) / old * 100, 1) if old and old > 0 else None
        rows.append(
            {
                "name": c["name"],
                "type_line": c.get("type_line"),
                "color_identity": c.get("color_identity"),
                "price": p,
                "scryfall_uri": c.get("scryfall_uri"),
                "delta_pct": delta_pct,
            }
        )
        cur.execute(
            "INSERT OR REPLACE INTO feed_snapshots (user_id, profile, card_name, price) VALUES (?,?,?,?)",
            (user_id, profile, c["name"], p),
        )
    conn.commit()
    conn.close()

    return {
        "set_name": latest["name"],
        "set_code": latest["code"],
        "released_at": latest["released_at"],
        "cards": rows,
    }
