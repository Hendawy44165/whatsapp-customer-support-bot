import os
import sys
import json
import sqlite3
from datetime import datetime, timezone, timedelta

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import db

SHOWCASE_CONVERSATIONS = [
    {
        "id": "thread-1",
        "customer_phone": "+201023456789",
        "platform": "whatsapp",
        "status": "active",
        "hubspot_contact_id": "hs_8839201",
        "cost_usd": 0.00065,
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat(),
        "messages": [
            {
                "sender_type": "customer",
                "content": "hiii 3ayza a3raf al discovery box feha eh exactly?",
                "sentiment": "positive",
                "intent": "product_details_inquiry",
                "tokens_used": 45,
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(minutes=15)
                ).isoformat(),
            },
            {
                "sender_type": "agent",
                "content": "Our Discovery Box features *3ml* atomizers of *Signature Sauvage*, *Oud Royale*, and *Noir Intense*. Priced at *450 EGP* with complimentary shipping, it includes a *450 EGP* voucher redeemable toward any *50ml* full bottle.",
                "sentiment": "satisfied",
                "intent": "product_details_inquiry",
                "tokens_used": 180,
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(minutes=14, seconds=58)
                ).isoformat(),
            },
        ],
        "metadata": {
            "crm_synced": True,
            "latency_ms": 1850,
            "trace_id": "tr_ls_98a72b10",
            "trace_steps": [
                {
                    "step": "Router Node (router_node)",
                    "detail": "Classified intent as 'product_details_inquiry' (Sentiment: positive)",
                },
                {
                    "step": "Simple QA Node (simple_qa)",
                    "detail": "Retrieved catalog facts & Discovery Box 450 EGP voucher terms",
                },
                {
                    "step": "CRM Subroutine (hubspot_upsert)",
                    "detail": "HubSpot Contact upserted: +201023456789 (ID: hs_8839201)",
                },
                {
                    "step": "Output Sanitizer Middleware",
                    "detail": "Verified zero prompt leakage & WhatsApp single-asterisk formatting",
                },
            ],
        },
    },
    {
        "id": "thread-2",
        "customer_phone": "+201288877665",
        "platform": "whatsapp",
        "status": "pending_handoff",
        "hubspot_contact_id": "hs_9918273",
        "cost_usd": 0.00095,
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat(),
        "messages": [
            {
                "sender_type": "customer",
                "content": "NUIT-1008 status? 5 days late.",
                "sentiment": "negative",
                "intent": "order_delay_complaint",
                "tokens_used": 35,
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(minutes=45)
                ).isoformat(),
            },
            {
                "sender_type": "agent",
                "content": "I apologize for the delay regarding your order *NUIT-1008*. I have escalated your issue to our *care team* so they can immediately follow up with *Bosta logistics* and provide you with an updated delivery status.",
                "sentiment": "frustrated",
                "intent": "order_delay_complaint",
                "tokens_used": 140,
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(minutes=44, seconds=59)
                ).isoformat(),
            },
        ],
        "metadata": {
            "crm_synced": True,
            "latency_ms": 1420,
            "trace_id": "tr_ls_11b34c90",
            "trace_steps": [
                {
                    "step": "Router Node (router_node)",
                    "detail": "Classified intent as 'order_delay_complaint' (Sentiment: negative)",
                },
                {
                    "step": "Escalator Node (escalator)",
                    "detail": "Evaluated courier_delay trigger (Urgency: 0.70)",
                },
                {
                    "step": "CRM Integration",
                    "detail": "Logged interaction to HubSpot Contact hs_9918273",
                },
                {"step": "Guardrail Check", "detail": "Generated structured escalation report for Ticket #1"},
            ],
        },
    },
    {
        "id": "thread-3",
        "customer_phone": "+201011223344",
        "platform": "whatsapp",
        "status": "manual_override",
        "hubspot_contact_id": "hs_7726154",
        "cost_usd": 0.00210,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "messages": [
            {
                "sender_type": "customer",
                "content": "omg I just opened the package and the bottle is leaking everywhere!! I need this for a birthday party tonight!!",
                "sentiment": "negative",
                "intent": "damaged_product_incident",
                "tokens_used": 60,
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(hours=2)
                ).isoformat(),
            },
            {
                "sender_type": "agent",
                "content": "I am deeply sorry to hear about your leaking bottle. I have escalated this as a *top priority* to our *care team* so they can arrange an immediate replacement for your event tonight.",
                "sentiment": "anxious",
                "intent": "damaged_product_incident",
                "tokens_used": 190,
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(hours=1, minutes=59)
                ).isoformat(),
            },
            {
                "sender_type": "human",
                "content": "Hello Habiba. This is Hendawy from Nuit Care. I have personally dispatched a replacement bottle for you via express delivery. Reference ID: *NUIT-REPL-402*.",
                "sentiment": "satisfied",
                "intent": "human_resolution",
                "tokens_used": 0,
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(hours=1, minutes=30)
                ).isoformat(),
            },
        ],
        "metadata": {
            "crm_synced": True,
            "latency_ms": 2100,
            "trace_id": "tr_ls_77d88e00",
            "trace_steps": [
                {
                    "step": "Router Node (router_node)",
                    "detail": "Classified intent as 'damaged_product_incident' (Urgency: 0.95)",
                },
                {
                    "step": "Escalator Node (escalator)",
                    "detail": "Evaluated damaged_item & time sensitivity (event tonight)",
                },
                {
                    "step": "Human Takeover",
                    "detail": "Conversation set to manual_override by Store Manager",
                },
            ],
        },
    },
]


def seed_database():
    print("🌱 Starting Showcase Data Seeding...")
    db_path = db.sqlite_db_path
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for conv in SHOWCASE_CONVERSATIONS:
        # Insert or update conversation
        cursor.execute(
            """
            INSERT OR REPLACE INTO conversations (
                id, customer_phone, platform, status, hubspot_contact_id, cost_usd, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                conv["id"],
                conv["customer_phone"],
                conv["platform"],
                conv["status"],
                conv["hubspot_contact_id"],
                conv["cost_usd"],
                conv["created_at"],
                conv["created_at"],
            ),
        )

        # Clear existing messages for this conversation to prevent duplicate rendering
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conv["id"],))

        # Insert messages
        for msg in conv["messages"]:
            s_data = json.dumps(
                {
                    "vibe": msg.get("sentiment", "neutral"),
                    "intent": msg.get("intent", "general"),
                    "metadata": conv.get("metadata", {}),
                }
            )
            cursor.execute(
                """
                INSERT INTO messages (
                    conversation_id, sender_type, content, sentiment, intent, sentiment_data, tokens_used, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    conv["id"],
                    msg["sender_type"],
                    msg["content"],
                    msg.get("sentiment"),
                    msg.get("intent"),
                    s_data,
                    msg.get("tokens_used", 0),
                    msg["created_at"],
                ),
            )

        # Add system log entry for CRM sync
        cursor.execute(
            """
            INSERT INTO system_logs (source, level, message, created_at)
            VALUES (?, ?, ?, ?)
        """,
            (
                "hubspot_sync",
                "INFO",
                f"⚡ HubSpot Contact Synced: {conv['customer_phone']} (Contact ID: {conv['hubspot_contact_id']})",
                conv["created_at"],
            ),
        )

    conn.commit()
    conn.close()
    print("✅ Showcase Data Successfully Seeded into SQLite!")


if __name__ == "__main__":
    seed_database()
