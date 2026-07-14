import base64
import io
import qrcode
from fastapi import APIRouter
from pydantic import BaseModel
from .. import scryfall_client as sf
from ..utils import parse_decklist, analyze_power

router = APIRouter()


class DecklistRequest(BaseModel):
    decklist: str


@router.post("/power")
async def power_check(req: DecklistRequest):
    names = parse_decklist(req.decklist)
    found, not_found = await sf.collection(names)
    if len(found) < 5:
        return {"error": "Troppe poche carte riconosciute."}

    stats = analyze_power(found)
    qr_text = (
        f"POWER CHECK\nScore: {stats['score']}/10 - {stats['category'].upper()}\n"
        f"FastMana:{stats['fast_mana']} Tutor:{stats['tutors']} "
        f"FreeInt:{stats['free_interaction']} Combo:{stats['combo']}\n"
        f"AvgCMC:{stats['avg_cmc']} Carte:{stats['total']}"
    )
    img = qrcode.make(qr_text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return {"stats": stats, "not_found": not_found, "qr_png_base64": qr_b64}
