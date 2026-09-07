"""
SMC Pro X — TradingView Webhook → Telegram Relay
รันด้วย: uvicorn main:app --host 0.0.0.0 --port 8000
"""
import os
import json
import logging
from datetime import datetime

import httpx
from fastapi import FastAPI, Request, HTTPException

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("smc-bot")

app = FastAPI(title="SMC Pro X Signal Bot")

TG_TOKEN   = os.getenv("TG_TOKEN", "")
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "")
SECRET     = os.getenv("WH_SECRET", "MY_SECRET_123")
TG_API     = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"

STARS = {5: "★★★", 4: "★★", 3: "★", 2: "", 1: "", 0: ""}
LINE  = "━━━━━━━━━━━━━━━━━━━━"


async def send_telegram(text: str) -> bool:
    if not TG_TOKEN or not TG_CHAT_ID:
        log.error("Missing TG_TOKEN or TG_CHAT_ID")
        return False
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(TG_API, json=payload)
            if r.status_code != 200:
                log.error("Telegram error %s: %s", r.status_code, r.text)
                return False
        return True
    except Exception as e:
        log.exception("send_telegram failed: %s", e)
        return False


def fmt_signal(d: dict) -> str:
    side  = d.get("side", "?")
    icon  = "🟢" if side == "BUY" else "🔴"
    score = int(d.get("score", 0))
    stars = STARS.get(score, "")
    grade = "PERFECT" if score == 5 else "STRONG" if score == 4 else "VALID"

    return (
        f"{icon} <b>{side}  {d.get('symbol','')}</b>  {stars}\n"
        f"<code>{LINE}</code>\n"
        f"⏱ <b>TF</b> {d.get('tf','')}  •  <b>Score</b> {score}/5  <i>({grade})</i>\n\n"
        f"🎯 <b>Entry</b>  <code>{d.get('entry')}</code>\n"
        f"🛑 <b>SL</b>     <code>{d.get('sl')}</code>  ({d.get('risk')} pts)\n"
        f"✅ <b>TP</b>     <code>{d.get('tp')}</code>  (RR 1:{d.get('rr')})\n"
        f"📦 <b>Lot</b>    <code>{d.get('lot')}</code>\n"
        f"<code>{LINE}</code>\n"
        f"📊 RSI {d.get('rsi')}  •  {d.get('zone')}  •  HTF {d.get('htf')}\n"
        f"🕐 {d.get('time')}"
    )


def fmt_sweep(d: dict) -> str:
    side = d.get("side", "")
    icon = "🔺" if side == "HIGH" else "🔻"
    return (
        f"{icon} <b>LIQUIDITY SWEEP {side}</b>\n"
        f"<code>{LINE}</code>\n"
        f"{d.get('symbol','')} • {d.get('tf','')} @ <code>{d.get('entry')}</code>\n"
        f"🕐 {d.get('time')}"
    )


@app.get("/")
async def health():
    return {"status": "ok", "service": "SMC Pro X Bot", "time": datetime.utcnow().isoformat()}


@app.post("/tv")
async def tradingview_hook(req: Request):
    raw = (await req.body()).decode("utf-8").strip()
    log.info("Incoming: %s", raw[:300])

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid json")

    if data.get("secret") != SECRET:
        log.warning("Bad secret")
        raise HTTPException(403, "forbidden")

    msg_type = data.get("type", "SIGNAL")
    text = fmt_sweep(data) if msg_type == "SWEEP" else fmt_signal(data)

    ok = await send_telegram(text)
    return {"ok": ok, "type": msg_type}


@app.post("/test")
async def test_message():
    await send_telegram("✅ <b>SMC Pro X Bot</b> เชื่อมต่อสำเร็จแล้วครับ!")
    return {"ok": True}
