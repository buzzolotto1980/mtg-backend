from fastapi import APIRouter
from pydantic import BaseModel
from .. import scryfall_client as sf
from ..utils import parse_decklist

router = APIRouter()


class DecklistRequest(BaseModel):
    decklist: str


@router.post("/gems")
async def hidden_gems(req: DecklistRequest):
    names = parse_decklist(req.decklist)
    found, _ = await sf.collection(names)
    if len(found) < 5:
        return {"error": "Servono almeno 5 carte riconosciute."}

    identity_set, types, keywords = set(), set(), set()
    deck_names = {c["name"].lower() for c in found}
    for c in found:
        for x in c.get("color_identity", []):
            identity_set.add(x)
        type_line = (c.get("type_line") or "").replace("\u2014", "-")
        parts = type_line.split("-")
        if len(parts) > 1:
            for t in parts[1].split():
                if len(t.strip()) > 2:
                    types.add(t.strip())
        for k in c.get("keywords", []):
            keywords.add(k)

    identity = "".join(identity_set) or "C"
    top_types = list(types)[:3]
    top_kw = list(keywords)[:3]

    queries = []
    if top_types:
        queries.append(f"id<={identity} type:{top_types[0]}")
    for k in top_kw:
        queries.append(f'id<={identity} keyword:"{k}"')
    if not queries:
        queries.append(f"id<={identity}")

    results = {}
    for q in queries:
        cards = await sf.search(f"{q} game:paper", order="edhrec")
        for c in cards:
            if c["name"].lower() not in deck_names and (c.get("edhrec_rank") or 0) > 9000:
                results[c["name"]] = c

    gems = sorted(results.values(), key=lambda c: c.get("edhrec_rank", 0), reverse=True)[:15]
    return {
        "identity": identity,
        "gems": [
            {
                "name": c["name"],
                "type_line": c.get("type_line"),
                "color_identity": c.get("color_identity"),
                "price": c.get("prices", {}).get("eur") or c.get("prices", {}).get("usd"),
                "edhrec_rank": c.get("edhrec_rank"),
                "scryfall_uri": c.get("scryfall_uri"),
            }
            for c in gems
        ],
    }
