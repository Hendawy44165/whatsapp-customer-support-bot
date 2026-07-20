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
        "id": "showcase-1",
        "customer_phone": "+201019876543",
        "platform": "whatsapp",
        "status": "active",
        "hubspot_contact_id": "hs_8839201",
        "cost_usd": 0.0012,
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat(),
        "messages": [
            {
                "sender_type": "customer",
                "content": "Hi! Is Nuit Noir Intense 50ml in stock? And how fast can you deliver to Alexandria?",
                "sentiment": "calm",
                "intent": "product_stock_inquiry",
                "tokens_used": 45,
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(minutes=15)
                ).isoformat(),
            },
            {
                "sender_type": "agent",
                "content": "Hello! 🔮 Yes, **Noir Intense (50ml)** is in stock! Price is 850 EGP.\n\n🚚 **Alexandria Delivery**: Express delivery via Bosta takes **24 to 48 hours**.\nWould you like me to reserve a bottle for you or send the order link?",
                "sentiment": "satisfied",
                "intent": "product_stock_inquiry",
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
                    "step": "Intent Classification",
                    "detail": "Routed to 'product_stock_inquiry' (Confidence: 99.2%)",
                },
                {
                    "step": "Tool Execution",
                    "detail": "Executed get_product_stock('Noir Intense 50ml') -> Stock: 24 units",
                },
                {
                    "step": "CRM Integration",
                    "detail": "HubSpot Contact upserted: +201019876543 (ID: hs_8839201)",
                },
                {
                    "step": "Guardrail Check",
                    "detail": "Passed fact verification & brand voice check",
                },
            ],
        },
    },
    {
        "id": "showcase-2",
        "customer_phone": "+201201122334",
        "platform": "whatsapp",
        "status": "resolved",
        "hubspot_contact_id": "hs_9918273",
        "cost_usd": 0.00095,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "messages": [
            {
                "sender_type": "customer",
                "content": "Where is my order NUIT-1008? Can I get a tracking link?",
                "sentiment": "calm",
                "intent": "order_tracking",
                "tokens_used": 35,
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(hours=2)
                ).isoformat(),
            },
            {
                "sender_type": "agent",
                "content": "Hello! Order **NUIT-1008** was dispatched today via Bosta.\nTracking Code: `BS-998822-EG`\nStatus: In Transit (Est. delivery tomorrow).",
                "sentiment": "satisfied",
                "intent": "order_tracking",
                "tokens_used": 140,
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(hours=1, minutes=59)
                ).isoformat(),
            },
        ],
        "metadata": {
            "crm_synced": True,
            "latency_ms": 1420,
            "trace_id": "tr_ls_11b34c90",
            "trace_steps": [
                {
                    "step": "Intent Classification",
                    "detail": "Routed to 'order_tracking' (Confidence: 98.8%)",
                },
                {
                    "step": "Tool Execution",
                    "detail": "Executed lookup_order('NUIT-1008') -> Courier: Bosta, Status: SHIPPED",
                },
                {
                    "step": "CRM Integration",
                    "detail": "Logged interaction to HubSpot Contact hs_9918273",
                },
                {"step": "Guardrail Check", "detail": "Passed factual policy check"},
            ],
        },
    },
    {
        "id": "showcase-3",
        "customer_phone": "+201155443322",
        "platform": "whatsapp",
        "status": "manual_override",
        "hubspot_contact_id": "hs_7726154",
        "cost_usd": 0.00210,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
        "messages": [
            {
                "sender_type": "customer",
                "content": "I received my bottle yesterday but the sprayer nozzle is leaking! I need a replacement right now.",
                "sentiment": "frustrated",
                "intent": "damaged_item_complaint",
                "tokens_used": 60,
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(hours=5)
                ).isoformat(),
            },
            {
                "sender_type": "agent",
                "content": "I am so sorry to hear that! We replace damaged items immediately at zero cost. I am connecting you with a care specialist right now.",
                "sentiment": "anxious",
                "intent": "damaged_item_complaint",
                "tokens_used": 190,
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(hours=4, minutes=59)
                ).isoformat(),
            },
            {
                "sender_type": "human",
                "content": "Hello! This is Hendawy from Nuit Care. I've personally dispatched a brand new replacement bottle for you via express delivery. Here is your reference number: NUIT-REPL-402.",
                "sentiment": "satisfied",
                "intent": "human_resolution",
                "tokens_used": 0,
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(hours=4, minutes=30)
                ).isoformat(),
            },
        ],
        "metadata": {
            "crm_synced": True,
            "latency_ms": 2100,
            "trace_id": "tr_ls_77d88e00",
            "trace_steps": [
                {
                    "step": "Intent Classification",
                    "detail": "Routed to 'damaged_item_complaint'",
                },
                {
                    "step": "Guardrail Check",
                    "detail": "Frustration score > 0.85 -> Triggered Human Handoff",
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
