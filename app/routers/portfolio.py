import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel
from .. import scryfall_client as sf
from ..database import get_conn
from ..utils import price_num

router = APIRouter()


class AddItemRequest(BaseModel):
    user_id: str
    name: str
    qty: int = 1


@router.post("/portfolio/items")
def add_item(req: AddItemRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, qty FROM portfolio_items WHERE user_id=? AND card_name=?",
        (req.user_id, req.name),
    )
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE portfolio_items SET qty=? WHERE id=?", (row["qty"] + req.qty, row["id"]))
    else:
        cur.execute(
            "INSERT INTO portfolio_items (user_id, card_name, qty) VALUES (?,?,?)",
            (req.user_id, req.name, req.qty),
        )
    conn.commit()
    conn.close()
    return {"ok": True}


@router.delete("/portfolio/items/{name}")
def remove_item(name: str, user_id: str = Query(...)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM portfolio_items WHERE user_id=? AND card_name=?", (user_id, name))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/portfolio")
async def get_portfolio(user_id: str = Query(...)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT card_name, qty FROM portfolio_items WHERE user_id=?", (user_id,))
    items = cur.fetchall()
    if not items:
        conn.close()
        return {"items": [], "total": 0, "history": []}

    names = [i["card_name"] for i in items]
    found, not_found = await sf.collection(names)
    total = 0.0
    rows = []
    for i in items:
        c = next((f for f in found if f["name"].lower() == i["card_name"].lower()), None)
        if not c:
            continue
        p = price_num(c) * i["qty"]
        total += p
        rows.append(
            {
                "name": c["name"],
                "qty": i["qty"],
                "unit_price": price_num(c),
                "subtotal": round(p, 2),
                "color_identity": c.get("color_identity"),
                "scryfall_uri": c.get("scryfall_uri"),
            }
        )

    today = datetime.date.today().isoformat()
    cur.execute(
        "INSERT OR REPLACE INTO portfolio_snapshots (user_id, snap_date, value) VALUES (?,?,?)",
        (user_id, today, total),
    )
    conn.commit()
    cur.execute(
        "SELECT snap_date, value FROM portfolio_snapshots WHERE user_id=? ORDER BY snap_date DESC LIMIT 14",
        (user_id,),
    )
    history = [{"date": r["snap_date"], "value": r["value"]} for r in reversed(cur.fetchall())]
    conn.close()

    return {"items": rows, "total": round(total, 2), "history": history, "not_found": not_found}
