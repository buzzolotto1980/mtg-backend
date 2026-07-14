from fastapi import APIRouter, Query
from .. import scryfall_client as sf
from ..utils import price_num

router = APIRouter()


@router.get("/alternatives")
async def find_alternatives(name: str = Query(...)):
    found, _ = await sf.collection([name])
    if not found:
        return {"error": "Carta non trovata."}

    card = found[0]
    main_type = (card.get("type_line") or "").split("\u2014")[0].strip().split(" ")[-1]
    identity = "".join(card.get("color_identity") or []) or "C"
    cmc = card.get("cmc") or 0

    cards = await sf.search(
        f'type:{main_type} id<={identity} cmc>={max(0, cmc - 1)} cmc<={cmc + 1} '
        f'-"{card["name"]}" game:paper',
        order="usd",
    )
    base_price = price_num(card)
    alternatives = []
    for c in cards:
        p = price_num(c)
        if c["name"].lower() == card["name"].lower() or p <= 0:
            continue
        alternatives.append(
            {
                "name": c["name"],
                "type_line": c.get("type_line"),
                "color_identity": c.get("color_identity"),
                "price": p,
                "savings": round(base_price - p, 2),
                "scryfall_uri": c.get("scryfall_uri"),
            }
        )
        if len(alternatives) >= 12:
            break

    return {
        "card": {"name": card["name"], "price": base_price, "type_line": card.get("type_line")},
        "alternatives": alternatives,
    }
