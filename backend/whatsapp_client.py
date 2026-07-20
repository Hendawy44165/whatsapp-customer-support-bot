"""
Meta WhatsApp Cloud API client.
All credentials are loaded from environment variables.
Set WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env to activate.
"""

import os
import structlog
import requests

logger = structlog.get_logger("whatsapp_client")

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN") or os.getenv("META_WHATSAPP_TOKEN") or ""
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID") or os.getenv("META_PHONE_NUMBER_ID") or ""
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION") or os.getenv("META_WHATSAPP_API_VERSION") or "v18.0"


def send_whatsapp_message(to_phone: str, message_text: str) -> dict:
    """
    Send a WhatsApp text message via Meta Cloud API.

    Args:
        to_phone: Recipient phone number (E.164 format, e.g. '+201012345678')
        message_text: Text message to send

    Returns:
        API response dict or stub response if not configured.
    """
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.warning(
            "[STUB] WhatsApp not configured. Would send to %s: %s",
            to_phone,
            message_text[:80],
        )
        return {"status": "stub", "to": to_phone, "message": message_text}

    url = (
        f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"
        f"/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {"preview_url": False, "body": message_text},
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        logger.info("WhatsApp message sent successfully", to_phone=to_phone)
        return resp.json()
    except Exception as e:
        logger.error("WhatsApp send failed: %s", str(e))
        return {"status": "error", "error": str(e)}


def parse_whatsapp_webhook(payload: dict) -> list:
    """
    Parse an incoming Meta WhatsApp webhook payload into a list of message dicts.

    Returns a list of dicts with keys:
        phone, message_body, message_id, timestamp, contact_name
    Only text-type messages are included; status updates are ignored.
    """
    messages = []
    try:
        entries = payload.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                contacts = value.get("contacts", [])
                contact_name = (
                    contacts[0].get("profile", {}).get("name", "Unknown")
                    if contacts
                    else "Unknown"
                )
                for msg in value.get("messages", []):
                    if msg.get("type") == "text":
                        messages.append(
                            {
                                "phone": msg.get("from", ""),
                                "message_body": msg.get("text", {}).get("body", ""),
                                "message_id": msg.get("id", ""),
                                "timestamp": msg.get("timestamp", ""),
                                "contact_name": contact_name,
                            }
                        )
        logger.info("Parsed WhatsApp webhook", messages_count=len(messages))
    except Exception as e:
        logger.error("Failed to parse WhatsApp webhook: %s", str(e))
    return messages
