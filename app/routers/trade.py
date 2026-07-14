from fastapi import APIRouter
from pydantic import BaseModel
from .. import scryfall_client as sf
from ..database import get_conn
from ..utils import price_num

router = APIRouter()


class TradeAddRequest(BaseModel):
    side: str
    name: str


@router.post("/trade/{code}/add")
def add_card(code: str, req: TradeAddRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO trade_cards (session_code, side, card_name) VALUES (?,?,?)",
        (code, req.side, req.name),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@router.delete("/trade/{code}/{card_id}")
def remove_card(code: str, card_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM trade_cards WHERE id=? AND session_code=?", (card_id, code))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/trade/{code}")
async def get_trade(code: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, side, card_name FROM trade_cards WHERE session_code=?", (code,))
    rows = cur.fetchall()
    conn.close()

    side_a = [r for r in rows if r["side"] == "A"]
    side_b = [r for r in rows if r["side"] == "B"]

    async def build_side(items):
        if not items:
            return [], 0.0
        found, _ = await sf.collection([i["card_name"] for i in items])
        total = 0.0
        out = []
        for i in items:
            c = next((f for f in found if f["name"].lower() == i["card_name"].lower()), None)
            if not c:
                continue
            p = price_num(c)
            total += p
            out.append({"id": i["id"], "name": c["name"], "price": p})
        return out, round(total, 2)

    a_cards, total_a = await build_side(side_a)
    b_cards, total_b = await build_side(side_b)
    diff = round(total_a - total_b, 2)

    if abs(diff) < 0.5:
        message = "Scambio in pareggio: nessuna integrazione necessaria."
    elif diff > 0:
        message = f"A sta offrendo di più: B dovrebbe aggiungere circa €{diff} in carte, oppure A può ricevere €{diff} in contanti."
    else:
        message = f"B sta offrendo di più: A dovrebbe aggiungere circa €{abs(diff)} in carte, oppure B può ricevere €{abs(diff)} in contanti."

    return {
        "side_a": a_cards,
        "side_b": b_cards,
        "total_a": total_a,
        "total_b": total_b,
        "message": message,
    }
