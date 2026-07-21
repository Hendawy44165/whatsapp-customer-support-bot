import os
import sqlite3
import json
import logging
import re
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger("database")


class DatabaseClient:
    """Local SQLite database client for the Nuit Bot.

    Provides initialization, queries, and updates for all system tables:
    - conversations
    - messages
    - tickets
    - products
    - system_logs
    - message_buffer
    - documents
    - settings
    - experts
    """

    def __init__(self) -> None:
        db_env = os.getenv("SQLITE_SIM_DB")
        if db_env:
            self.sqlite_db_path = db_env
        else:
            # Set absolute path in the backend directory
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            self.sqlite_db_path = os.path.join(backend_dir, "local_supabase_sim.db")

        logger.info(
            "DatabaseClient: Initialising local SQLite DB at: %s", self.sqlite_db_path
        )
        self._init_sqlite_tables()

    def _init_sqlite_tables(self) -> None:
        """Creates all tables in local SQLite and seeds default records."""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()

        # 1. Conversations Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            customer_phone TEXT NOT NULL,
            platform TEXT DEFAULT 'whatsapp',
            status TEXT DEFAULT 'active',
            handoff_summary TEXT,
            hubspot_contact_id TEXT,
            assigned_expert_id TEXT,
            cost_usd REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 2. Messages Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            sender_type TEXT NOT NULL,
            content TEXT NOT NULL,
            sentiment TEXT,
            intent TEXT,
            sentiment_data TEXT,
            tokens_used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 3. Tickets Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            customer_phone TEXT NOT NULL,
            summary TEXT,
            status TEXT DEFAULT 'open',
            assigned_to TEXT,
            hubspot_note_id TEXT,
            reason TEXT,
            urgency REAL,
            recommended_action TEXT,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            resolved_at TEXT
        )
        """)

        # Migrate tickets table if columns don't exist
        cursor.execute("PRAGMA table_info(tickets)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        for col_name, col_type in [
            ("reason", "TEXT"),
            ("urgency", "REAL"),
            ("recommended_action", "TEXT"),
            ("metadata", "TEXT"),
        ]:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE tickets ADD COLUMN {col_name} {col_type}")

        # 4. Products Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            promo_price REAL,
            variant TEXT,
            stock_quantity INTEGER DEFAULT 0,
            is_available BOOLEAN DEFAULT 1,
            description TEXT
        )
        """)

        # 5. System Logs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            level TEXT,
            message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 6. Message Buffer Table (Outbound queue)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS message_buffer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            scheduled_for TEXT DEFAULT CURRENT_TIMESTAMP,
            sent_at TEXT,
            error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 7. Documents Table (RAG Reference docs)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            category TEXT,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 8. Settings Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 9. Experts Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS experts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            chat_redirect_url TEXT,
            is_active BOOLEAN DEFAULT 1
        )
        """)

        # Seed products if empty
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            self._seed_products(cursor)

        # Seed experts if empty
        cursor.execute("SELECT COUNT(*) FROM experts")
        if cursor.fetchone()[0] == 0:
            experts_seed = [
                (
                    "exp-1",
                    "Ahmed Sayed",
                    "ahmed@nuit.com",
                    "http://localhost:5173/chat/exp-1",
                    1,
                ),
                (
                    "exp-2",
                    "Rania Hassan",
                    "rania@nuit.com",
                    "http://localhost:5173/chat/exp-2",
                    1,
                ),
            ]
            cursor.executemany(
                "INSERT INTO experts VALUES (?, ?, ?, ?, ?)", experts_seed
            )
            logger.info("DatabaseClient: Seeded local experts profiles.")

        # Seed conversations and tickets if empty
        cursor.execute("SELECT COUNT(*) FROM conversations")
        if cursor.fetchone()[0] == 0:
            self._seed_conversations_and_tickets(cursor)

        conn.commit()
        conn.close()

    def _seed_products(self, cursor) -> None:
        """Seed the local products table with Nuit catalogue data."""
        flagship_variants = [
            ("Rum", 0),
            ("Dulce de Leche", 15),
            ("Head Turner", 8),
            ("Born in Milano", 25),
            ("Born in Vegas", 12),
            ("Bounty Hunter", 3),
            ("Red Flag", 0),
            ("Green Flag", 9),
            ("Espresso Martini", 14),
            ("Forbidden Fruit", 7),
            ("Casa Di Rosa", 0),
            ("Lindo Día", 18),
            ("Monroe", 22),
            ("Warm Vanilla", 30),
            ("French Foulard", 5),
            ("True Hipster", 11),
            ("Leather Jacket", 6),
            ("Cappuccina", 4),
            ("Choco Frappe", 0),
            ("Hazelwood", 16),
            ("Heritage", 13),
            ("I am Harvey", 20),
        ]
        for var_name, stock in flagship_variants:
            cursor.execute(
                "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"prod-edp-{var_name.lower().replace(' ', '-')}",
                    "flagship_edp_50ml",
                    f"Flagship Eau de Parfum - {var_name}",
                    855.00,
                    599.00,
                    var_name,
                    stock,
                    1 if stock > 0 else 0,
                    f"Nuit Flagship 50ml Eau de Parfum in the exquisite {var_name} variant. "
                    "Scent profile features warm, premium, elegant fragrance notes.",
                ),
            )

        # Luxury Collaboration
        cursor.execute(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "prod-lux-hatshepsut",
                "luxury_collaboration",
                "Avec Hatshepsut (Nuit X Temraza)",
                1950.00,
                None,
                None,
                5,
                1,
                "Exclusive art flacon collaboration with Temraza. Highly exclusive luxury "
                "collector's edition, not eligible for standard EDP discounts. Rich woody, "
                "warm spicy, and deep amber fragrance notes.",
            ),
        )

        # Concentrated Perfume Oil Shots
        shots = [
            ("Vanilla Shot", 12),
            ("Born in Milano Shot", 0),
            ("Caramel Shot", 8),
            ("Head Turner Shot", 15),
        ]
        for shot_name, stock in shots:
            cursor.execute(
                "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"prod-oil-{shot_name.lower().replace(' ', '-')}",
                    "perfume_oils_shots_khamrias",
                    shot_name,
                    475.00,
                    None,
                    None,
                    stock,
                    1 if stock > 0 else 0,
                    f"Highly concentrated premium Nuit perfume oil / khamria in {shot_name} variant. "
                    "Scent profile features sweet vanilla, caramel, floral accords, and amber notes.",
                ),
            )

        # Body Splash & Mists
        mists = [
            ("Soft Cloud Heart", 20),
            ("Very Delicate Vanilla", 15),
            ("The Harvey Splash", 0),
        ]
        for mist_name, stock in mists:
            cursor.execute(
                "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"prod-mist-{mist_name.lower().replace(' ', '-')}",
                    "body_splash_mists",
                    mist_name,
                    315.00,
                    None,
                    None,
                    stock,
                    1 if stock > 0 else 0,
                    f"Refreshing premium Nuit body splash / mist in {mist_name} variant. "
                    "Light, clean, sweet vanilla, fresh floral scent notes.",
                ),
            )

    def _seed_conversations_and_tickets(self, cursor) -> None:
        """Seed conversations, messages, and tickets tables from mock_seed_data.json."""
        import json
        import re

        backend_dir = os.path.dirname(os.path.abspath(__file__))
        seed_path = os.path.join(backend_dir, "mock_seed_data.json")
        if not os.path.exists(seed_path):
            logger.warning(
                "DatabaseClient: mock_seed_data.json not found, skipping seeding."
            )
            return

        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error("DatabaseClient: Failed to load mock_seed_data.json: %s", e)
            return

        conversations = data.get("conversations", [])
        tickets = data.get("tickets", [])

        # Helpers for timestamps
        def parse_msg_timestamp(conv_timestamp: str, msg_time_str: str) -> str:
            date_part = conv_timestamp.split("T")[0]
            match = re.match(
                r"(\d+):(\d+):(\d+)\s*(AM|PM)", msg_time_str, re.IGNORECASE
            )
            if match:
                h, m, s, ampm = match.groups()
                hour = int(h)
                minute = int(m)
                second = int(s)
                if ampm.upper() == "PM" and hour < 12:
                    hour += 12
                elif ampm.upper() == "AM" and hour == 12:
                    hour = 0
                return f"{date_part}T{hour:02d}:{minute:02d}:{second:02d}Z"
            return conv_timestamp

        logger.info("DatabaseClient: Seeding conversations and messages...")
        now = datetime.now(timezone.utc)
        thread_offsets = {
            "thread-1": timedelta(minutes=15),
            "thread-2": timedelta(minutes=45),
            "thread-3": timedelta(hours=2),
            "thread-4": timedelta(hours=3),
            "thread-5": timedelta(hours=5),
            "thread-6": timedelta(hours=8),
            "thread-7": timedelta(hours=12),
            "thread-8": timedelta(hours=24),
            "thread-9": timedelta(hours=28),
            "thread-10": timedelta(hours=48),
        }

        for c in conversations:
            platform = c.get("channel", "whatsapp")
            status = c.get("status", "active")
            assigned_expert_id = None
            if status == "escalated":
                matching_ticket = next(
                    (t for t in tickets if t["conversation_id"] == c["id"]), None
                )
                if matching_ticket:
                    if matching_ticket["status"] == "open":
                        status = "pending_handoff"
                    elif matching_ticket["status"] == "claimed":
                        status = "handed_off"
                        assigned_expert_id = (
                            "exp-2"
                            if matching_ticket["assigned_to"] == "Rania Hassan"
                            else "exp-1"
                        )
                    elif matching_ticket["status"] == "resolved":
                        status = "resolved"
                        assigned_expert_id = (
                            "exp-1"
                            if matching_ticket["assigned_to"] == "Ahmed Sayed"
                            else "exp-2"
                        )

            customer_phone = c.get("phoneNumber", "")
            if customer_phone == "Unknown":
                customer_phone = "Unknown"

            c_offset = thread_offsets.get(c["id"], timedelta(hours=2))
            c_timestamp = (now - c_offset).isoformat()

            cursor.execute(
                """
                INSERT INTO conversations (
                    id, customer_phone, platform, status, handoff_summary, 
                    assigned_expert_id, cost_usd, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c["id"],
                    customer_phone,
                    platform,
                    status,
                    c.get("handoff_summary", ""),
                    assigned_expert_id,
                    c.get("cost", 0.0),
                    c_timestamp,
                    c_timestamp,
                ),
            )

            messages_list = c.get("messages", [])
            customer_msgs = [m for m in messages_list if m["sender"] == "user"]
            agent_msgs = [m for m in messages_list if m["sender"] == "bot"]

            tokens_input = c.get("tokens", {}).get("input", 0)
            tokens_output = c.get("tokens", {}).get("output", 0)

            n_cust = len(customer_msgs)
            cust_tokens = []
            if n_cust > 0:
                base = tokens_input // n_cust
                rem = tokens_input % n_cust
                cust_tokens = [base] * n_cust
                cust_tokens[-1] += rem

            n_agent = len(agent_msgs)
            agent_tokens = []
            if n_agent > 0:
                base = tokens_output // n_agent
                rem = tokens_output % n_agent
                agent_tokens = [base] * n_agent
                agent_tokens[-1] += rem

            cust_idx = 0
            agent_idx = 0
            for idx, m in enumerate(messages_list):
                sender = m["sender"]
                sender_type = "customer" if sender == "user" else "agent"

                msg_tokens = 0
                if sender_type == "customer":
                    if cust_idx < len(cust_tokens):
                        msg_tokens = cust_tokens[cust_idx]
                        cust_idx += 1
                else:
                    if agent_idx < len(agent_tokens):
                        msg_tokens = agent_tokens[agent_idx]
                        agent_idx += 1

                msg_time = (now - c_offset + timedelta(minutes=idx * 2)).isoformat()

                sentiment_data_str = None
                sentiment = None
                intent = None
                if idx == len(messages_list) - 1:
                    sentiment = c.get("emotion", "neutral")
                    intent = c.get("intent", "general_faq")
                    sentiment_data_str = json.dumps(
                        {"vibe": sentiment, "intent": intent}
                    )

                cursor.execute(
                    """
                    INSERT INTO messages (
                        conversation_id, sender_type, content, sentiment, 
                        intent, sentiment_data, tokens_used, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        c["id"],
                        sender_type,
                        m["text"],
                        sentiment,
                        intent,
                        sentiment_data_str,
                        msg_tokens,
                        msg_time,
                    ),
                )

        logger.info("DatabaseClient: Seeding tickets...")
        for t in tickets:
            t_offset = thread_offsets.get(t["conversation_id"], timedelta(hours=2))
            t_created = (now - t_offset).isoformat()
            t_resolved = (now - t_offset + timedelta(minutes=45)).isoformat() if t["status"] == "resolved" else None

            cursor.execute(
                """
                INSERT INTO tickets (
                    id, conversation_id, customer_phone, summary, status, 
                    assigned_to, reason, urgency, recommended_action, metadata, created_at, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t["id"],
                    t["conversation_id"],
                    t["customer_phone"],
                    t["summary"],
                    t["status"],
                    t["assigned_to"],
                    t.get("reason", "Customer Service Escalation"),
                    t.get("urgency", 0.8),
                    t.get("recommended_action", "Review conversation and contact client."),
                    t.get("metadata", "{}"),
                    t_created,
                    t_resolved,
                ),
            )
        logger.info(
            "DatabaseClient: Seeded local conversations, messages, and tickets."
        )

    # -----------------------------------------------------------------------
    # System Logs
    # -----------------------------------------------------------------------

    def add_system_log(self, source: str, level: str, message: str) -> None:
        """Route system logs through standard logging and batch to SQLite."""
        log_logger = logging.getLogger(source)
        level_upper = level.upper()
        if level_upper == "DEBUG":
            log_logger.debug(message)
        elif level_upper == "INFO":
            log_logger.info(message)
        elif level_upper == "WARNING":
            log_logger.warning(message)
        elif level_upper == "ERROR":
            log_logger.error(message)
        elif level_upper == "CRITICAL":
            log_logger.critical(message)
        else:
            log_logger.info(message)

    # -----------------------------------------------------------------------
    # Message Buffer (outbound queue)
    # -----------------------------------------------------------------------

    def get_pending_buffered_messages(self) -> List[Dict[str, Any]]:
        """Return all pending buffered messages whose scheduled_for <= now."""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        pending = []
        try:
            now = datetime.utcnow().isoformat() + "Z"
            cursor.execute(
                "SELECT * FROM message_buffer WHERE status = 'pending' AND scheduled_for <= ?",
                (now,),
            )
            pending = [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error("get_pending_buffered_messages failed: %s", e)
        finally:
            conn.close()
        return pending

    def mark_buffered_message_sent(self, message_id: int) -> None:
        """Mark a buffered message as successfully sent."""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        try:
            now = datetime.utcnow().isoformat() + "Z"
            cursor.execute(
                "UPDATE message_buffer SET status = 'sent', sent_at = ? WHERE id = ?",
                (now, message_id),
            )
            conn.commit()
        except Exception as e:
            logger.error("mark_buffered_message_sent failed: %s", e)
        finally:
            conn.close()

    def mark_buffered_message_failed(self, message_id: int, error: str) -> None:
        """Mark a buffered message as failed and record the error."""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE message_buffer SET status = 'failed', error = ? WHERE id = ?",
                (error, message_id),
            )
            conn.commit()
        except Exception as e:
            logger.error("mark_buffered_message_failed failed: %s", e)
        finally:
            conn.close()

    def queue_outbound_message(
        self, conversation_id: str, content: str, delay_seconds: int = 0
    ) -> None:
        """Insert a new outbound message into the message_buffer queue."""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        try:
            from datetime import timedelta

            scheduled_for = (
                datetime.utcnow() + timedelta(seconds=delay_seconds)
            ).isoformat() + "Z"
            cursor.execute(
                "INSERT INTO message_buffer (conversation_id, content, status, scheduled_for) VALUES (?, ?, 'pending', ?)",
                (conversation_id, content, scheduled_for),
            )
            conn.commit()
        except Exception as e:
            logger.error("queue_outbound_message failed: %s", e)
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # Messages
    # -----------------------------------------------------------------------

    def add_message(
        self,
        conversation_id: str,
        sender_type: str,
        content: str,
        sentiment: Optional[str] = None,
        intent: Optional[str] = None,
        sentiment_data: Optional[Dict] = None,
        tokens_used: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Insert a message into the messages table."""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        inserted_id = None
        try:
            sentiment_data_str = json.dumps(sentiment_data) if sentiment_data else None
            now = datetime.utcnow().isoformat() + "Z"
            cursor.execute(
                "INSERT INTO messages (conversation_id, sender_type, content, sentiment, intent, sentiment_data, tokens_used, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    conversation_id,
                    sender_type,
                    content,
                    sentiment,
                    intent,
                    sentiment_data_str,
                    tokens_used,
                    now,
                ),
            )
            conn.commit()
            inserted_id = cursor.lastrowid
        except Exception as e:
            logger.error("add_message failed: %s", e)
        finally:
            conn.close()

        if inserted_id:
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE id = ?", (inserted_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                res = dict(row)
                if res.get("sentiment_data"):
                    try:
                        res["sentiment_data"] = json.loads(res["sentiment_data"])
                    except:
                        pass
                return res
        return None

    def get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Return all messages for a given conversation, oldest first."""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        messages = []
        try:
            cursor.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (conversation_id,),
            )
            rows = cursor.fetchall()
            for r in rows:
                d = dict(r)
                if d.get("sentiment_data"):
                    try:
                        d["sentiment_data"] = json.loads(d["sentiment_data"])
                    except:
                        pass
                messages.append(d)
        except Exception as e:
            logger.error("get_messages failed: %s", e)
        finally:
            conn.close()
        return messages

    # -----------------------------------------------------------------------
    # Conversations
    # -----------------------------------------------------------------------

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single conversation by its ID."""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        conv = None
        try:
            cursor.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            )
            row = cursor.fetchone()
            if row:
                conv = dict(row)
        except Exception as e:
            logger.error("get_conversation failed: %s", e)
        finally:
            conn.close()
        return conv

    def create_conversation(
        self,
        conversation_id: str,
        customer_phone: str,
        platform: str = "whatsapp",
    ) -> Optional[Dict[str, Any]]:
        """Create a new conversation record and return it."""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        try:
            now = datetime.utcnow().isoformat() + "Z"
            cursor.execute(
                "INSERT INTO conversations (id, customer_phone, platform, status, created_at, updated_at) VALUES (?, ?, ?, 'active', ?, ?)",
                (conversation_id, customer_phone, platform, now, now),
            )
            conn.commit()
        except Exception as e:
            logger.error("create_conversation failed: %s", e)
        finally:
            conn.close()
        return self.get_conversation(conversation_id)

    def delete_conversation(self, conversation_id: str) -> bool:
        """Completely delete a conversation and its associated messages, tickets, and buffered messages."""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.execute(
                "DELETE FROM messages WHERE conversation_id = ?", (conversation_id,)
            )
            cursor.execute(
                "DELETE FROM tickets WHERE conversation_id = ?", (conversation_id,)
            )
            cursor.execute(
                "DELETE FROM message_buffer WHERE conversation_id = ?",
                (conversation_id,),
            )
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            conn.commit()
            logger.info(
                "Deleted conversation and associated data for id: %s", conversation_id
            )
            return True
        except Exception as e:
            logger.error("delete_conversation failed: %s", e)
            return False
        finally:
            conn.close()

    def update_conversation(
        self, conversation_id: str, updates_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Apply a partial update to a conversation record."""
        if not updates_dict:
            return self.get_conversation(conversation_id)

        updates_dict["updated_at"] = datetime.utcnow().isoformat() + "Z"
        keys = list(updates_dict.keys())
        set_clause = ", ".join([f"{k} = ?" for k in keys])
        values = list(updates_dict.values()) + [conversation_id]

        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"UPDATE conversations SET {set_clause} WHERE id = ?", values
            )
            conn.commit()
        except Exception as e:
            logger.error("update_conversation failed: %s", e)
        finally:
            conn.close()
        return self.get_conversation(conversation_id)

    def get_conversations(
        self, search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return all conversations, optionally filtered by search_query, newest first."""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        convs = []
        try:
            if search_query:
                like_pattern = f"%{search_query}%"
                query = """
                    SELECT DISTINCT c.* FROM conversations c
                    LEFT JOIN messages m ON c.id = m.conversation_id
                    WHERE c.customer_phone LIKE ?
                       OR c.platform LIKE ?
                       OR c.status LIKE ?
                       OR c.handoff_summary LIKE ?
                       OR m.content LIKE ?
                    ORDER BY c.created_at DESC
                """
                cursor.execute(
                    query,
                    (
                        like_pattern,
                        like_pattern,
                        like_pattern,
                        like_pattern,
                        like_pattern,
                    ),
                )
            else:
                cursor.execute("SELECT * FROM conversations ORDER BY created_at DESC")
            convs = [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error("get_conversations failed: %s", e)
        finally:
            conn.close()
        return convs

    # -----------------------------------------------------------------------
    # Documents (RAG knowledge base)
    # -----------------------------------------------------------------------

    def get_documents(self) -> List[Dict[str, Any]]:
        """Return all documents in the knowledge base."""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        docs = []
        try:
            cursor.execute("SELECT * FROM documents ORDER BY created_at ASC")
            docs = [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error("get_documents failed: %s", e)
        finally:
            conn.close()
        return docs

    def add_document(
        self, filename: str, category: str, content: str
    ) -> Optional[Dict[str, Any]]:
        """Insert or replace a document in the knowledge base."""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO documents (filename, category, content) VALUES (?, ?, ?)",
                (filename, category, content),
            )
            conn.commit()
        except Exception as e:
            logger.error("add_document failed: %s", e)
        finally:
            conn.close()

        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE filename = ?", (filename,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_document(self, filename: str) -> None:
        """Remove a document from the knowledge base by filename."""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM documents WHERE filename = ?", (filename,))
            conn.commit()
        except Exception as e:
            logger.error("delete_document failed: %s", e)
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # Settings
    # -----------------------------------------------------------------------

    def get_setting(self, key: str) -> Optional[Any]:
        """Retrieve the value of a system setting by key."""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        val = None
        try:
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                val = json.loads(row[0])
        except Exception as e:
            logger.error("get_setting failed: %s", e)
        finally:
            conn.close()
        return val

    def update_setting(self, key: str, value: Any) -> None:
        """Create or update a system setting."""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        try:
            now = datetime.utcnow().isoformat() + "Z"
            val_str = json.dumps(value)
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                (key, val_str, now),
            )
            conn.commit()
        except Exception as e:
            logger.error("update_setting failed: %s", e)
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # Experts
    # -----------------------------------------------------------------------

    def get_expert(self, expert_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single expert profile by ID."""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        expert = None
        try:
            cursor.execute("SELECT * FROM experts WHERE id = ?", (expert_id,))
            row = cursor.fetchone()
            if row:
                expert = dict(row)
        except Exception as e:
            logger.error("get_expert failed: %s", e)
        finally:
            conn.close()
        return expert

    def get_experts(self) -> List[Dict[str, Any]]:
        """Return all active expert profiles."""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        experts = []
        try:
            cursor.execute("SELECT * FROM experts WHERE is_active = 1")
            experts = [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error("get_experts failed: %s", e)
        finally:
            conn.close()
        return experts

    # -----------------------------------------------------------------------
    # Tickets
    # -----------------------------------------------------------------------

    def add_to_tickets(
        self,
        conversation_id: str,
        customer_phone: str,
        summary: Optional[str] = None,
        reason: Optional[str] = None,
        urgency: Optional[float] = None,
        recommended_action: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new support ticket for an escalated conversation."""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        inserted_id = None
        try:
            now = datetime.utcnow().isoformat() + "Z"
            metadata_str = json.dumps(metadata) if metadata is not None else None
            cursor.execute(
                """
                INSERT INTO tickets (
                    conversation_id, customer_phone, summary, status,
                    reason, urgency, recommended_action, metadata, created_at
                ) VALUES (?, ?, ?, 'open', ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    customer_phone,
                    summary,
                    reason,
                    urgency,
                    recommended_action,
                    metadata_str,
                    now,
                ),
            )
            conn.commit()
            inserted_id = cursor.lastrowid
        except Exception as e:
            logger.error("add_to_tickets failed: %s", e)
        finally:
            conn.close()

        if inserted_id:
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tickets WHERE id = ?", (inserted_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        return None

    def get_tickets(self) -> List[Dict[str, Any]]:
        """Return all tickets, newest first."""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        tickets = []
        try:
            cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC")
            tickets = [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error("get_tickets failed: %s", e)
        finally:
            conn.close()
        return tickets

    def update_ticket(
        self, ticket_id: int, updates_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Apply a partial update to a ticket (e.g. status, assigned_to)."""
        if not updates_dict:
            return None
        keys = list(updates_dict.keys())
        set_clause = ", ".join([f"{k} = ?" for k in keys])
        values = list(updates_dict.values()) + [ticket_id]

        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(f"UPDATE tickets SET {set_clause} WHERE id = ?", values)
            conn.commit()
        except Exception as e:
            logger.error("update_ticket failed: %s", e)
        finally:
            conn.close()

        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # -----------------------------------------------------------------------
    # Products (Local SQLite helpers, TF-IDF cosine-similarity search)
    # -----------------------------------------------------------------------

    def get_products(self) -> List[Dict[str, Any]]:
        """Return all products from the local database."""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        rows = []
        try:
            cursor.execute("SELECT * FROM products")
            rows = [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error("get_products failed: %s", e)
        finally:
            conn.close()
        return rows

    def get_product_details(
        self, name: str, variant: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return product details matching name (and optionally variant)."""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        rows = []
        try:
            if variant:
                cursor.execute(
                    "SELECT * FROM products WHERE (name LIKE ? OR category = ?) AND variant LIKE ?",
                    (f"%{name}%", name, f"%{variant}%"),
                )
            else:
                cursor.execute(
                    "SELECT * FROM products WHERE name LIKE ? OR category = ?",
                    (f"%{name}%", name),
                )
            rows = [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error("get_product_details failed: %s", e)
        finally:
            conn.close()
        return rows

    def semantic_search_products(
        self, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search products by description using a TF-IDF cosine-similarity model."""
        products = self.get_products()
        if not products:
            return []

        def compute_tf(text: str) -> dict:
            words = re.findall(r"\b\w+\b", text.lower())
            tf: dict = {}
            for word in words:
                tf[word] = tf.get(word, 0) + 1
            total = len(words) or 1
            for word in tf:
                tf[word] = tf[word] / total
            return tf

        def compute_idf(documents: list) -> dict:
            N = len(documents)
            idf: dict = {}
            for doc in documents:
                words = set(re.findall(r"\b\w+\b", doc.lower()))
                for word in words:
                    idf[word] = idf.get(word, 0) + 1
            for word in idf:
                idf[word] = math.log((N + 1) / (idf[word] + 1)) + 1
            return idf

        def cosine_similarity(vec1: dict, vec2: dict) -> float:
            intersection = set(vec1.keys()) & set(vec2.keys())
            numerator = sum(vec1[x] * vec2[x] for x in intersection)
            sum1 = sum(v**2 for v in vec1.values())
            sum2 = sum(v**2 for v in vec2.values())
            denominator = math.sqrt(sum1) * math.sqrt(sum2)
            return numerator / denominator if denominator else 0.0

        descriptions = [p.get("description", "") or "" for p in products]
        documents = descriptions + [query]
        idf = compute_idf(documents)

        query_tf = compute_tf(query)
        query_vec = {w: t * idf.get(w, 0.0) for w, t in query_tf.items()}

        scored: List[tuple] = []
        for product in products:
            p_desc = product.get("description", "") or ""
            p_tf = compute_tf(p_desc)
            p_vec = {w: t * idf.get(w, 0.0) for w, t in p_tf.items()}
            sim = cosine_similarity(query_vec, p_vec)
            if sim > 0.05:
                scored.append((sim, product))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored][:limit]


# Module-level singleton
db = DatabaseClient()
