import os
import logging
from telebot.async_telebot import AsyncTeleBot
from telebot import types

logger = logging.getLogger("telegram_client")

# Load token from environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ""
bot = (
    AsyncTeleBot(TELEGRAM_BOT_TOKEN, parse_mode=None)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN != "your-telegram-bot-token"
    else None
)


async def send_telegram_message(chat_id: str, message_text: str) -> dict:
    """
    Send a Telegram text message via AsyncTeleBot.

    Args:
        chat_id: Unique identifier for the target chat or username of the target channel
        message_text: Text message to send

    Returns:
        A simple dict describing success or failure.
    """
    if not bot:
        logger.warning(
            "[STUB] Telegram not configured or token is placeholder. Would send to %s: %s",
            chat_id,
            message_text[:80],
        )
        return {"status": "stub", "chat_id": chat_id, "message": message_text}

    try:
        result = await bot.send_message(chat_id, message_text)
        logger.info("Telegram message sent successfully", chat_id=chat_id)
        return {
            "status": "ok",
            "message_id": getattr(result, "message_id", None),
        }
    except Exception as e:
        logger.error("Telegram send failed: %s", str(e))
        return {"status": "error", "error": str(e)}


def parse_telegram_webhook(payload: dict) -> list:
    """
    Parse a Telegram webhook payload into a list of normalized message dicts.
    """
    messages = []
    try:
        update = types.Update.de_json(payload)
        message = update.message
        if message and hasattr(message, "text") and message.text:
            first_name = getattr(message.from_user, "first_name", "") or ""
            last_name = getattr(message.from_user, "last_name", "") or ""
            contact_name = f"{first_name} {last_name}".strip() or "Unknown"

            messages.append(
                {
                    "chat_id": str(message.chat.id),
                    "message_body": message.text,
                    "message_id": str(message.message_id),
                    "username": getattr(message.from_user, "username", "") or "",
                    "contact_name": contact_name,
                }
            )
        logger.info("Parsed Telegram webhook", messages_count=len(messages))
    except Exception as e:
        logger.error("Failed to parse Telegram webhook: %s", str(e))
    return messages



async def delete_telegram_message(chat_id: str, message_id: int) -> bool:
    """Delete a single message from Telegram UI by message ID."""
    if not bot:
        return False
    try:
        await bot.delete_message(chat_id, message_id)
        return True
    except Exception:
        return False


async def clear_telegram_chat_messages(
    chat_id: str,
    last_message_id: int = None,
    known_message_ids: list = None,
    depth: int = 150,
) -> int:
    """
    Delete messages in Telegram UI up to depth.
    """
    import asyncio

    if not bot:
        return 0

    ids_to_delete = set(known_message_ids or [])
    if last_message_id:
        try:
            current_id = int(last_message_id)
            start = max(1, current_id - depth)
            for m_id in range(current_id, start - 1, -1):
                ids_to_delete.add(m_id)
        except (ValueError, TypeError):
            pass

    if not ids_to_delete:
        return 0

    tasks = [
        delete_telegram_message(chat_id, m_id)
        for m_id in sorted(ids_to_delete, reverse=True)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    deleted_count = sum(1 for r in results if r is True)
    logger.info(
        "Cleared Telegram UI messages", chat_id=chat_id, deleted_count=deleted_count
    )
    return deleted_count


# If you ever switch from webhook mode to polling mode, use skip_pending=True to avoid
# processing the backlog of all missed Telegram messages when the bot was offline.
# Example:
#   bot.infinity_polling(skip_pending=True)
