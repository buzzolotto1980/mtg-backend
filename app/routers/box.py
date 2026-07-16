from fastapi import APIRouter, Query
from pydantic import BaseModel
from .. import scryfall_client as sf
from ..database import get_conn
from ..utils import price_num

router = APIRouter()


def _extract_image(card: dict):
    img = card.get("image_uris")
    if not img and card.get("card_faces"):
        img = card["card_faces"][0].get("image_uris")
    if not img:
        return None
    return img.get("normal") or img.get("small") or img.get("png")


class BoxAddRequest(BaseModel):
    user_id: str
    name: str
    box: str
    slot: str


@router.post("/box")
async def add_location(req: BoxAddRequest):
    # Recuperiamo il nome canonico, l'immagine ufficiale e il prezzo da
    # Scryfall al momento del salvataggio, cosi' la collezione mostra sempre
    # dati reali (non la foto scattata dall'utente, che resta solo un aiuto
    # temporaneo lato client per riconoscere/battere il nome).
    canonical_name, image_url, price = req.name, None, None
    found, _ = await sf.collection([req.name])
    if found:
        card = found[0]
        canonical_name = card["name"]
        image_url = _extract_image(card)
        price = price_num(card)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO box_locations (user_id, card_name, box, slot, image_url, price) VALUES (?,?,?,?,?,?)",
        (req.user_id, canonical_name, req.box, req.slot, image_url, price),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "name": canonical_name, "image_url": image_url, "price": price}


@router.get("/box")
def list_locations(user_id: str = Query(...)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, card_name, box, slot, image_url, price FROM box_locations WHERE user_id=? ORDER BY card_name",
        (user_id,),
    )
    rows = [
        {
            "id": r["id"], "name": r["card_name"], "box": r["box"], "slot": r["slot"],
            "image_url": r["image_url"], "price": r["price"],
        }
        for r in cur.fetchall()
    ]
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
        "SELECT card_name, box, slot, image_url FROM box_locations WHERE user_id=? AND lower(card_name) LIKE ?",
        (user_id, f"%{q.lower()}%"),
    )
    rows = [{"name": r["card_name"], "box": r["box"], "slot": r["slot"], "image_url": r["image_url"]} for r in cur.fetchall()]
    conn.close()
    return {"matches": rows}


@router.get("/cards/autocomplete")
async def autocomplete(q: str = Query(...)):
    if len(q.strip()) < 2:
        return {"suggestions": []}
    names = await sf.autocomplete(q.strip())
    return {"suggestions": names[:8]}
