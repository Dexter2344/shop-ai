import os
import logging
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shop-ai")

app = FastAPI(title="Shop-AI", version="0.1.0")

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
GRAPH_URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    logger.info(f"Webhook verification attempt: mode={hub_mode}")
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return PlainTextResponse(content=hub_challenge, status_code=200)
    logger.warning("Webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_webhook(request: Request):
    body = await request.json()
    logger.info(f"Incoming webhook: {body}")

    try:
        entry = body.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "no_message"}

        message = messages[0]
        sender = message.get("from")
        msg_type = message.get("type")

        if msg_type == "text":
            text = message.get("text", {}).get("body", "")
            logger.info(f"Text from {sender}: {text}")
            await send_text(sender, f"Echo: {text}")

        elif msg_type == "image":
            logger.info(f"Image from {sender}")
            await send_text(sender, "Got your image. Image handling coming soon.")

        else:
            logger.info(f"Unsupported type: {msg_type}")
            await send_text(sender, f"Unsupported message type: {msg_type}")

    except (IndexError, KeyError) as e:
        logger.error(f"Payload parse error: {e}")

    return {"status": "ok"}


async def send_text(to: str, text: str):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.post(GRAPH_URL, headers=headers, json=payload)
        if res.status_code >= 400:
            logger.error(f"Send failed: {res.status_code} {res.text}")
        else:
            logger.info(f"Sent to {to}: {text}")


@app.get("/")
async def health():
    return {
        "status": "alive",
        "service": "Shop-AI",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
