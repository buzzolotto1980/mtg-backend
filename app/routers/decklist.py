import base64
import datetime
import html
import io
import secrets

import qrcode
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .. import scryfall_client as sf
from ..database import get_conn
from ..utils import parse_decklist, price_num

router = APIRouter()


class DecklistShareRequest(BaseModel):
    decklist: str
    title: str | None = None


@router.post("/decklist/share")
async def share_decklist(req: DecklistShareRequest, request: Request):
    names = parse_decklist(req.decklist)
    if not names:
        return {"error": "La decklist sembra vuota."}

    share_id = secrets.token_urlsafe(6)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO shared_decklists (id, title, decklist_text, created_at) VALUES (?,?,?,?)",
        (share_id, (req.title or "Decklist"), req.decklist, datetime.datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

    share_url = str(request.base_url).rstrip("/") + f"/api/decklist/{share_id}"

    img = qrcode.make(share_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return {"share_url": share_url, "qr_png_base64": qr_b64, "card_lines": len(names)}


DECKLIST_TEMPLATE = """<!DOCTYPE html>
<html lang="it"><head><meta charset="UTF-8">
<title>{title} — Decklist condivisa</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,650;9..144,850&family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box;}}
  body{{margin:0;min-height:100vh;padding:28px 18px;font-family:'Inter',sans-serif;color:#e9e4d8;
    background:radial-gradient(900px 500px at 15% -10%, rgba(201,162,39,0.10), transparent 60%),
      radial-gradient(700px 400px at 100% 110%, rgba(21,104,166,0.10), transparent 60%), #10161a;}}
  .wrap{{max-width:640px;margin:0 auto;}}
  .eyebrow{{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#c9a227;}}
  h1{{font-family:'Fraunces',serif;font-weight:650;font-size:24px;margin:6px 0 4px;}}
  .meta{{font-family:'JetBrains Mono',monospace;font-size:12px;color:#8a8474;margin-bottom:18px;}}
  .panel{{background:#1c2628;border:1px solid #2c3a3d;border-radius:14px;padding:18px;margin-bottom:16px;}}
  .panel h2{{font-family:'Fraunces',serif;font-size:14px;margin:0 0 10px;color:#f1ecdf;}}
  textarea{{width:100%;min-height:280px;background:#0e1416;border:1px solid #2c3a3d;border-radius:9px;color:#d8e0dc;
    font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.6;padding:12px;resize:vertical;}}
  button{{background:#c9a227;color:#1a1503;border:none;font-weight:700;font-size:13px;padding:10px 16px;
    border-radius:9px;cursor:pointer;margin-top:10px;}}
  button:hover{{background:#dab233;}}
  .stores{{display:flex;gap:10px;flex-wrap:wrap;margin-top:6px;}}
  .store-link{{flex:1;min-width:220px;background:#182124;border:1px solid #2c3a3d;border-radius:10px;padding:12px 14px;
    text-decoration:none;color:#e9e4d8;display:block;transition:border-color .15s;}}
  .store-link:hover{{border-color:#8f7a3e;}}
  .store-link b{{display:block;font-family:'Fraunces',serif;font-size:14px;margin-bottom:3px;}}
  .store-link span{{font-size:11.5px;color:#8a8474;line-height:1.4;display:block;}}
  .note{{font-size:11.5px;color:#8a7c56;background:rgba(201,162,39,0.08);border:1px solid rgba(201,162,39,0.25);
    border-radius:8px;padding:9px 12px;margin-top:14px;line-height:1.5;}}
  #copyMsg{{font-family:'JetBrains Mono',monospace;font-size:11.5px;color:#7fbf9e;margin-left:10px;}}
</style></head><body>
<div class="wrap">
  <div class="eyebrow">MTG Command Deck</div>
  <h1>{title}</h1>
  <div class="meta">{total} carte riconosciute · valore stimato €{price}</div>

  <div class="panel">
    <h2>Lista pronta da copiare</h2>
    <textarea id="dl" readonly>{raw_text}</textarea>
    <button id="copyBtn">Copia lista</button><span id="copyMsg"></span>
  </div>

  <div class="panel">
    <h2>Importala su un deckbuilder</h2>
    <div class="stores">
      <a class="store-link" href="https://moxfield.com/decks" target="_blank" rel="noopener">
        <b>Moxfield →</b>
        <span>Accedi (o registrati) → "+ New Deck" → icona import/testo → incolla (Ctrl+V) la lista copiata sopra.</span>
      </a>
      <a class="store-link" href="https://archidekt.com/decks" target="_blank" rel="noopener">
        <b>Archidekt →</b>
        <span>Accedi → "New Deck" → menu Extras → Import → incolla (Ctrl+V) la lista copiata sopra.</span>
      </a>
    </div>
    <div class="note">Moxfield e Archidekt non offrono un'importazione automatica via link: serve accedere e incollare la lista manualmente — è il loro stesso meccanismo di import testuale, non una limitazione di questa app.</div>
  </div>
</div>
<script>
document.getElementById('copyBtn').addEventListener('click', async () => {{
  const ta = document.getElementById('dl');
  ta.select();
  try {{
    await navigator.clipboard.writeText(ta.value);
    document.getElementById('copyMsg').textContent = 'Copiato!';
  }} catch(e) {{
    document.execCommand('copy');
    document.getElementById('copyMsg').textContent = 'Copiato!';
  }}
  setTimeout(() => {{ document.getElementById('copyMsg').textContent = ''; }}, 2500);
}});
</script>
</body></html>"""


@router.get("/decklist/{share_id}", response_class=HTMLResponse)
async def view_decklist(share_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT title, decklist_text FROM shared_decklists WHERE id=?", (share_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return HTMLResponse(
            "<h1 style='font-family:sans-serif;color:#eee;background:#10161a;padding:40px;'>Decklist non trovata.</h1>",
            status_code=404,
        )

    title, decklist_text = row["title"], row["decklist_text"]
    names = parse_decklist(decklist_text)
    found, _ = await sf.collection(names)
    total_price = sum(price_num(c) for c in found)

    return HTMLResponse(
        DECKLIST_TEMPLATE.format(
            title=html.escape(title),
            total=len(names),
            price=f"{total_price:.2f}",
            raw_text=html.escape(decklist_text),
        )
    )
