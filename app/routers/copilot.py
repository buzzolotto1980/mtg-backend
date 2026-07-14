import re
from fastapi import APIRouter
from pydantic import BaseModel
from .. import scryfall_client as sf
from ..utils import parse_decklist, analyze_power, oracle_of, FAST_MANA

router = APIRouter()

RAMP_RE = re.compile(r"add (\{[wubrg]\}|one mana|\{c\})|search your library for a( basic)? land", re.I)


class DecklistRequest(BaseModel):
    decklist: str


@router.post("/copilot")
async def deck_copilot(req: DecklistRequest):
    names = parse_decklist(req.decklist)
    if len(names) < 10:
        return {"error": "Serve una decklist più completa (almeno 10 carte)."}

    found, _ = await sf.collection(names)
    stats = analyze_power(found)

    identity_set = set()
    for c in found:
        for x in c.get("color_identity", []):
            identity_set.add(x)
    identity = "".join(identity_set) or "C"

    ramp_count = sum(
        1 for c in found if RAMP_RE.search(oracle_of(c)) or any(f in c["name"].lower() for f in FAST_MANA)
    )
    deck_size = len(found)

    advice = []
    if stats["land_count"] < 34 and deck_size >= 90:
        advice.append(
            f"Hai solo {stats['land_count']} terre per un mazzo di {deck_size} carte: "
            "nel 99 di Commander si consiglia generalmente 34-38 terre."
        )
    if stats["avg_cmc"] > 3.2 and ramp_count < 8:
        advice.append(
            f"Il CMC medio è {stats['avg_cmc']} ma hai solo {ramp_count} fonti di accelerazione: "
            "rischi di bloccarti nei turni iniziali."
        )
    if stats["tutors"] == 0:
        advice.append("Nessun tutor rilevato: potresti avere difficoltà a trovare i pezzi chiave del piano di gioco.")
    if not advice:
        advice.append("La struttura del mazzo sembra ragionevolmente bilanciata.")

    ramp_suggestions = await sf.search(f"id<={identity} otag:ramp -type:land game:paper", order="edhrec")
    deck_names_lower = {c["name"].lower() for c in found}
    top_ramp = [c for c in ramp_suggestions if c["name"].lower() not in deck_names_lower][:5]

    return {
        "stats": stats,
        "ramp_count": ramp_count,
        "identity": identity,
        "advice": advice,
        "ramp_suggestions": [
            {
                "name": c["name"],
                "price": c.get("prices", {}).get("eur") or c.get("prices", {}).get("usd"),
                "scryfall_uri": c.get("scryfall_uri"),
            }
            for c in top_ramp
        ],
    }
