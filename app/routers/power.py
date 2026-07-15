import base64
import io
import json
import secrets
import datetime
import qrcode
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from .. import scryfall_client as sf
from ..database import get_conn
from ..utils import parse_decklist, analyze_power

router = APIRouter()

CAT_COLORS = {"Casual": "#0b6e4f", "Fringe": "#1568a6", "Optimized": "#b8332b", "cEDH": "#8f2fb8"}

CERT_TEMPLATE = """<!DOCTYPE html>
<html lang="it"><head><meta charset="UTF-8">
<title>Certificato di Potenza — {score}/10</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,650;9..144,850&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box;}}
  body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;
    font-family:'JetBrains Mono',monospace;
    background:
      radial-gradient(900px 500px at 15% -10%, rgba(201,162,39,0.10), transparent 60%),
      radial-gradient(700px 400px at 100% 110%, rgba(21,104,166,0.10), transparent 60%),
      #10161a;}}
  .certificate{{background:linear-gradient(180deg,#efe6d3,#e6dabd);color:#2a2318;border-radius:16px;
    padding:28px 26px;border:1px solid #cbbb8e;box-shadow:inset 0 0 0 1px rgba(255,255,255,.4), 0 18px 46px rgba(0,0,0,.55);
    max-width:440px;width:100%;position:relative;overflow:hidden;}}
  .certificate::before{{content:"";position:absolute;top:-40%;right:-25%;width:70%;height:180%;
    background:radial-gradient(circle,rgba(201,162,39,.14),transparent 65%);pointer-events:none;}}
  .cert-eyebrow{{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:#8f7a3e;font-weight:700;}}
  .cert-title{{font-family:'Fraunces',serif;font-weight:650;font-size:15px;text-transform:uppercase;
    letter-spacing:.02em;color:#5a5142;border-bottom:1px dashed #b9a878;padding-bottom:12px;margin:4px 0 16px;}}
  .score-row{{display:flex;align-items:baseline;gap:12px;margin-bottom:18px;}}
  .score{{font-family:'Fraunces',serif;font-weight:850;font-size:42px;letter-spacing:-0.02em;}}
  .tag{{display:inline-block;font-size:11px;padding:4px 12px;border-radius:14px;background:{cat_color};
    color:#fff;font-weight:700;letter-spacing:.04em;text-transform:uppercase;}}
  .kv{{display:flex;justify-content:space-between;font-size:12.5px;padding:6px 0;border-bottom:1px solid rgba(0,0,0,0.08);}}
  .kv span:first-child{{color:#8a7c56;}}
  .kv span:last-child{{font-weight:700;}}
  .curve{{display:flex;align-items:flex-end;gap:4px;height:48px;margin-top:14px;}}
  .curve-bar{{flex:1;background:linear-gradient(180deg,#c9a227,#a3821f);border-radius:2px 2px 0 0;min-height:2px;}}
  .curve-labels{{display:flex;gap:4px;margin-top:4px;}}
  .curve-labels span{{flex:1;text-align:center;font-size:9px;color:#8a7c56;}}
  .footer-note{{font-size:10px;color:#8a7c56;margin-top:20px;text-align:center;letter-spacing:.02em;}}
  .seal{{position:absolute;top:22px;right:22px;width:34px;height:34px;border-radius:50%;
    border:2px solid #c9a227;display:flex;align-items:center;justify-content:center;
    font-family:'Fraunces',serif;font-weight:850;font-size:13px;color:#8f7a3e;background:rgba(201,162,39,.08);}}
</style></head><body>
<div class="certificate">
  <div class="seal">MTG</div>
  <div class="cert-eyebrow">MTG Command Deck</div>
  <div class="cert-title">Certificato di Potenza</div>
  <div class="score-row">
    <div class="score">{score}/10</div>
    <span class="tag">{category}</span>
  </div>
  <div class="kv"><span>Fast Mana</span><span>{fast_mana}</span></div>
  <div class="kv"><span>Tutor</span><span>{tutors}</span></div>
  <div class="kv"><span>Interazione gratuita</span><span>{free_interaction}</span></div>
  <div class="kv"><span>Combo pezzi noti</span><span>{combo}</span></div>
  <div class="kv"><span>CMC medio</span><span>{avg_cmc}</span></div>
  <div class="kv"><span>Terre / Carte totali</span><span>{land_count} / {total}</span></div>
  <div class="curve">{curve_bars}</div>
  <div class="curve-labels">{curve_labels}</div>
  <div class="footer-note">Generato il {date} — stima euristica, non un giudizio ufficiale</div>
</div>
</body></html>"""


def render_certificate_html(stats: dict) -> str:
    curve = stats["curve"]
    keys = ["0", "1", "2", "3", "4", "5", "6+"]
    max_v = max([curve.get(k, 0) for k in keys] + [1])
    bars = "".join(f'<div class="curve-bar" style="height:{round(curve.get(k,0)/max_v*100)}%"></div>' for k in keys)
    labels = "".join(f"<span>{k}</span>" for k in keys)
    return CERT_TEMPLATE.format(
        score=stats["score"],
        category=stats["category"],
        cat_color=CAT_COLORS.get(stats["category"], "#8f7a3e"),
        fast_mana=stats["fast_mana"],
        tutors=stats["tutors"],
        free_interaction=stats["free_interaction"],
        combo=stats["combo"],
        avg_cmc=stats["avg_cmc"],
        land_count=stats["land_count"],
        total=stats["total"],
        curve_bars=bars,
        curve_labels=labels,
        date=datetime.date.today().strftime("%d/%m/%Y"),
    )


class DecklistRequest(BaseModel):
    decklist: str


@router.post("/power")
async def power_check(req: DecklistRequest, request: Request):
    names = parse_decklist(req.decklist)
    found, not_found = await sf.collection(names)
    if len(found) < 5:
        return {"error": "Troppe poche carte riconosciute."}

    stats = analyze_power(found)

    cert_id = secrets.token_urlsafe(6)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO power_certificates (id, stats_json, created_at) VALUES (?,?,?)",
        (cert_id, json.dumps(stats), datetime.datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

    # Il QR punta a una pagina pubblica del certificato (stessa grafica),
    # cosi' chi scansiona vede la carta vera, non del testo grezzo.
    certificate_url = str(request.base_url).rstrip("/") + f"/api/power/certificate/{cert_id}"

    img = qrcode.make(certificate_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "stats": stats,
        "not_found": not_found,
        "qr_png_base64": qr_b64,
        "certificate_url": certificate_url,
    }


@router.get("/power/certificate/{cert_id}", response_class=HTMLResponse)
def get_certificate(cert_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT stats_json FROM power_certificates WHERE id=?", (cert_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return HTMLResponse("<h1 style='font-family:sans-serif;color:#eee;background:#10161a;padding:40px;'>Certificato non trovato.</h1>", status_code=404)
    stats = json.loads(row["stats_json"])
    return HTMLResponse(render_certificate_html(stats))
