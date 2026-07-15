from fastapi import APIRouter
from pydantic import BaseModel
from .. import scryfall_client as sf
from ..utils import price_num

router = APIRouter()

ALLOWED_TYPES = {"creature", "instant", "sorcery", "artifact", "enchantment", "planeswalker", "land", "battle"}


class WatchRequest(BaseModel):
    formats: list[str]
    identity: str = "WUBRG"
    types: list[str] = []


@router.post("/watch")
async def format_watch(req: WatchRequest):
    latest = await sf.latest_set()
    if not latest:
        return {"error": "Nessun set trovato."}

    identity = "".join([c for c in req.identity.upper() if c in "WUBRG"]) or "WUBRG"
    types = [t.lower() for t in req.types if t.lower() in ALLOWED_TYPES]
    type_clause = ""
    if types:
        type_clause = " (" + " or ".join(f"type:{t}" for t in types) + ")"

    seen: dict = {}
    for fmt in req.formats:
        query = f"set:{latest['code']} legal:{fmt} id<={identity}{type_clause}"
        cards = await sf.search(query, order="released")
        for c in cards:
            if c["name"] not in seen:
                seen[c["name"]] = {"card": c, "formats": [fmt]}
            else:
                seen[c["name"]]["formats"].append(fmt)

    results = [
        {
            "name": v["card"]["name"],
            "type_line": v["card"].get("type_line"),
            "color_identity": v["card"].get("color_identity"),
            "formats": v["formats"],
            "price": price_num(v["card"]),
            "scryfall_uri": v["card"].get("scryfall_uri"),
        }
        for v in seen.values()
    ]
    return {
        "set_name": latest["name"],
        "set_code": latest["code"],
        "released_at": latest["released_at"],
        "results": results,
    }
