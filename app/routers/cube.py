from fastapi import APIRouter
from pydantic import BaseModel
from .. import scryfall_client as sf
from ..utils import parse_decklist, price_num

router = APIRouter()


class DecklistRequest(BaseModel):
    decklist: str


@router.post("/cube")
async def analyze_cube(req: DecklistRequest):
    names = parse_decklist(req.decklist)
    if len(names) < 20:
        return {"error": "Serve una lista di almeno 20 carte."}

    found, not_found = await sf.collection(names)
    color_count = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0}
    curve = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, "6+": 0}
    kw_freq: dict = {}

    for c in found:
        ids = c.get("color_identity") or []
        if not ids:
            color_count["C"] += 1
        else:
            for x in ids:
                color_count[x] += 1
        if "land" not in (c.get("type_line") or "").lower():
            cmc = c.get("cmc") or 0
            bucket = "6+" if cmc >= 6 else int(cmc)
            curve[bucket] = curve.get(bucket, 0) + 1
        for k in c.get("keywords", []):
            kw_freq[k] = kw_freq.get(k, 0) + 1

    dead_picks = [
        c
        for c in found
        if (c.get("edhrec_rank") or 0) > 15000
        and not any(kw_freq.get(k, 0) > 3 for k in c.get("keywords", []))
    ]

    return {
        "color_balance": color_count,
        "curve": curve,
        "dead_picks": [
            {
                "name": c["name"],
                "edhrec_rank": c.get("edhrec_rank"),
                "price": price_num(c),
                "scryfall_uri": c.get("scryfall_uri"),
            }
            for c in dead_picks[:20]
        ],
        "not_found": not_found,
        "total_analyzed": len(found),
    }
