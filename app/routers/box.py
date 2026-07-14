from fastapi import APIRouter, Query
from pydantic import BaseModel
from ..database import get_conn

router = APIRouter()


class BoxAddRequest(BaseModel):
    user_id: str
    name: str
    box: str
    slot: str


@router.post("/box")
def add_location(req: BoxAddRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO box_locations (user_id, card_name, box, slot) VALUES (?,?,?,?)",
        (req.user_id, req.name, req.box, req.slot),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/box")
def list_locations(user_id: str = Query(...)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, card_name, box, slot FROM box_locations WHERE user_id=? ORDER BY card_name",
        (user_id,),
    )
    rows = [{"id": r["id"], "name": r["card_name"], "box": r["box"], "slot": r["slot"]} for r in cur.fetchall()]
    conn.close()
    return {"locations": rows}


@router.delete("/box/{loc_id}")
def delete_location(loc_id: int, user_id: str = Query(...)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM box_locations WHERE id=? AND user_id=?", (loc_id, user_id))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/box/search")
def search_location(q: str = Query(...), user_id: str = Query(...)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT card_name, box, slot FROM box_locations WHERE user_id=? AND lower(card_name) LIKE ?",
        (user_id, f"%{q.lower()}%"),
    )
    rows = [{"name": r["card_name"], "box": r["box"], "slot": r["slot"]} for r in cur.fetchall()]
    conn.close()
    return {"matches": rows}
