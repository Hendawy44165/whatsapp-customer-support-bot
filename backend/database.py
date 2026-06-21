import os
import sqlite3
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("database")

class DatabaseClient:
    """
    Modular database client. Interacts with Supabase if SUPABASE_URL and SUPABASE_KEY are provided.
    Otherwise, automatically falls back to an SQLite simulation for local testing/development.
    """
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.use_supabase = bool(self.supabase_url and self.supabase_key)
        
        self.sqlite_db_path = os.getenv("SQLITE_SIM_DB", "local_supabase_sim.db")
        self.supabase_client = None

        if self.use_supabase:
            try:
                from supabase import create_client, Client
                self.supabase_client = create_client(self.supabase_url, self.supabase_key)
                logger.info("DatabaseClient: Initialized connection to Supabase.")
            except ImportError:
                logger.warning("DatabaseClient: supabase-py package not installed. Falling back to SQLite simulation.")
                self.use_supabase = False
            except Exception as e:
                logger.error(f"DatabaseClient: Failed to connect to Supabase: {e}. Falling back to SQLite simulation.")
                self.use_supabase = False

        if not self.use_supabase:
            logger.info(f"DatabaseClient: Initializing SQLite Simulation DB at: {self.sqlite_db_path}")
            self._init_sqlite_tables()

    def _init_sqlite_tables(self):
        """Creates tables locally in SQLite matching the Supabase Postgres schema."""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        
        # Experts Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS experts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'offline',
            current_load INTEGER DEFAULT 0,
            chat_redirect_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Conversations Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            customer_phone TEXT NOT NULL,
            platform TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            assigned_expert_id TEXT,
            cost_usd REAL DEFAULT 0.0,
            handoff_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assigned_expert_id) REFERENCES experts(id)
        )
        """)

        # Messages Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            sender_type TEXT NOT NULL,
            content TEXT NOT NULL,
            sentiment_data TEXT, -- JSON text
            tokens_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
        """)

        # Message Buffer Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS message_buffer (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            scheduled_for TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
        """)

        # Reference Documents Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # System Logs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id TEXT PRIMARY KEY,
            service_name TEXT NOT NULL,
            log_level TEXT NOT NULL,
            message TEXT NOT NULL,
            metadata TEXT, -- JSON text
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Settings Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL, -- JSON text
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Carts Table (New)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS carts (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            price REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
        """)

        # Seed initial system settings if not present
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (
            "llm_config",
            json.dumps({
                "provider_model_name": "deepseek-chat",
                "temperature": 0.3,
                "max_tokens": 1000
            })
        ))

        # Seed a default expert for local testing
        cursor.execute("INSERT OR IGNORE INTO experts (id, name, email, status, current_load, chat_redirect_url) VALUES (?, ?, ?, ?, ?, ?)", (
            "exp-101",
            "Mervat Support Expert",
            "mervat@nfragrances.com",
            "online",
            0,
            "https://wa.me/201234567890?text=Assigned+Chat+Redirection"
        ))
        
        conn.commit()
        conn.close()

    # --- Experts Methods ---
    def get_experts(self) -> List[Dict[str, Any]]:
        if self.use_supabase:
            res = self.supabase_client.table("experts").select("*").execute()
            return res.data
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM experts")
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows

    def get_expert(self, expert_id: str) -> Optional[Dict[str, Any]]:
        if self.use_supabase:
            res = self.supabase_client.table("experts").select("*").eq("id", expert_id).execute()
            return res.data[0] if res.data else None
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM experts WHERE id = ?", (expert_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None

    def update_expert_status(self, expert_id: str, status: str) -> None:
        if self.use_supabase:
            self.supabase_client.table("experts").update({"status": status}).eq("id", expert_id).execute()
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE experts SET status = ? WHERE id = ?", (status, expert_id))
            conn.commit()
            conn.close()

    def update_expert_load(self, expert_id: str, load: int) -> None:
        if self.use_supabase:
            self.supabase_client.table("experts").update({"current_load": load}).eq("id", expert_id).execute()
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE experts SET current_load = ? WHERE id = ?", (load, expert_id))
            conn.commit()
            conn.close()

    # --- Conversations Methods ---
    def create_conversation(self, id_: str, customer_phone: str, platform: str) -> Dict[str, Any]:
        data = {
            "id": id_,
            "customer_phone": customer_phone,
            "platform": platform,
            "status": "active",
            "cost_usd": 0.0,
            "assigned_expert_id": None,
            "handoff_summary": None
        }
        if self.use_supabase:
            res = self.supabase_client.table("conversations").insert(data).execute()
            return res.data[0]
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (id, customer_phone, platform, status, cost_usd) VALUES (?, ?, ?, ?, ?)",
                (id_, customer_phone, platform, "active", 0.0)
            )
            conn.commit()
            conn.close()
            return data

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        if self.use_supabase:
            res = self.supabase_client.table("conversations").select("*").eq("id", conversation_id).execute()
            return res.data[0] if res.data else None
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None

    def update_conversation(self, conversation_id: str, updates: Dict[str, Any]) -> None:
        if self.use_supabase:
            self.supabase_client.table("conversations").update(updates).eq("id", conversation_id).execute()
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [conversation_id]
            cursor.execute(f"UPDATE conversations SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
            
            # If status or expert assignment changed, simulate the trigger and recalculate loads
            if "assigned_expert_id" in updates or "status" in updates:
                cursor.execute("SELECT id FROM experts")
                expert_ids = [r[0] for r in cursor.fetchall()]
                for exp_id in expert_ids:
                    cursor.execute(
                        "SELECT COUNT(*) FROM conversations WHERE assigned_expert_id = ? AND status = 'handed_off'",
                        (exp_id,)
                    )
                    count = cursor.fetchone()[0]
                    cursor.execute("UPDATE experts SET current_load = ? WHERE id = ?", (count, exp_id))
            
            conn.commit()
            conn.close()

    def get_conversations(self) -> List[Dict[str, Any]]:
        if self.use_supabase:
            res = self.supabase_client.table("conversations").select("*").execute()
            return res.data
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM conversations ORDER BY updated_at DESC")
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows

    # --- Messages Methods ---
    def add_message(self, conversation_id: str, sender_type: str, content: str, sentiment_data: Optional[Dict] = None, tokens_used: int = 0) -> Dict[str, Any]:
        import uuid
        msg_id = str(uuid.uuid4())
        data = {
            "id": msg_id,
            "conversation_id": conversation_id,
            "sender_type": sender_type,
            "content": content,
            "sentiment_data": sentiment_data,
            "tokens_used": tokens_used
        }
        if self.use_supabase:
            self.supabase_client.table("messages").insert(data).execute()
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (id, conversation_id, sender_type, content, sentiment_data, tokens_used) VALUES (?, ?, ?, ?, ?, ?)",
                (msg_id, conversation_id, sender_type, content, json.dumps(sentiment_data), tokens_used)
            )
            # Update conversation timestamp
            cursor.execute("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conversation_id,))
            conn.commit()
            conn.close()
        return data

    def get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        if self.use_supabase:
            res = self.supabase_client.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at").execute()
            return res.data
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,))
            rows = []
            for r in cursor.fetchall():
                d = dict(r)
                if d.get("sentiment_data"):
                    try:
                        d["sentiment_data"] = json.loads(d["sentiment_data"])
                    except:
                        pass
                rows.append(d)
            conn.close()
            return rows

    # --- Message Buffer Methods ---
    def queue_outbound_message(self, conversation_id: str, content: str, scheduled_for: Optional[str] = None) -> str:
        import uuid
        msg_id = str(uuid.uuid4())
        if self.use_supabase:
            data = {
                "id": msg_id,
                "conversation_id": conversation_id,
                "content": content,
                "status": "pending"
            }
            if scheduled_for:
                data["scheduled_for"] = scheduled_for
            self.supabase_client.table("message_buffer").insert(data).execute()
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            if scheduled_for:
                cursor.execute(
                    "INSERT INTO message_buffer (id, conversation_id, content, status, scheduled_for) VALUES (?, ?, ?, ?, ?)",
                    (msg_id, conversation_id, content, "pending", scheduled_for)
                )
            else:
                cursor.execute(
                    "INSERT INTO message_buffer (id, conversation_id, content, status) VALUES (?, ?, ?, ?)",
                    (msg_id, conversation_id, content, "pending")
                )
            conn.commit()
            conn.close()
        return msg_id

    def get_pending_buffered_messages(self) -> List[Dict[str, Any]]:
        if self.use_supabase:
            # Query pending messages where scheduled_for <= NOW()
            import datetime
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            res = self.supabase_client.table("message_buffer")\
                .select("*")\
                .eq("status", "pending")\
                .lte("scheduled_for", now_iso)\
                .execute()
            return res.data
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM message_buffer WHERE status = 'pending' AND datetime(scheduled_for) <= datetime('now')"
            )
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows

    def mark_buffered_message_sent(self, message_id: str) -> None:
        if self.use_supabase:
            import datetime
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self.supabase_client.table("message_buffer").update({
                "status": "sent",
                "sent_at": now_iso
            }).eq("id", message_id).execute()
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE message_buffer SET status = 'sent', sent_at = CURRENT_TIMESTAMP WHERE id = ?",
                (message_id,)
            )
            conn.commit()
            conn.close()

    def mark_buffered_message_failed(self, message_id: str, error_message: str) -> None:
        if self.use_supabase:
            self.supabase_client.table("message_buffer").update({
                "status": "failed",
                "error_message": error_message
            }).eq("id", message_id).execute()
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE message_buffer SET status = 'failed', error_message = ? WHERE id = ?",
                (error_message, message_id)
            )
            conn.commit()
            conn.close()

    # --- Documents Methods ---
    def get_documents(self) -> List[Dict[str, Any]]:
        if self.use_supabase:
            res = self.supabase_client.table("documents").select("*").execute()
            return res.data
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents")
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows

    def add_document(self, filename: str, category: str, content: str) -> Dict[str, Any]:
        import uuid
        doc_id = str(uuid.uuid4())
        data = {
            "id": doc_id,
            "filename": filename,
            "category": category,
            "content": content
        }
        if self.use_supabase:
            res = self.supabase_client.table("documents").upsert({
                "filename": filename,
                "category": category,
                "content": content
            }, on_conflict="filename").execute()
            return res.data[0]
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO documents (id, filename, category, content) VALUES (?, ?, ?, ?) ON CONFLICT(filename) DO UPDATE SET category=excluded.category, content=excluded.content",
                (doc_id, filename, category, content)
            )
            conn.commit()
            conn.close()
            return data

    def delete_document(self, filename: str) -> None:
        if self.use_supabase:
            self.supabase_client.table("documents").delete().eq("filename", filename).execute()
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE filename = ?", (filename,))
            conn.commit()
            conn.close()

    # --- Settings Methods ---
    def get_setting(self, key: str) -> Any:
        if self.use_supabase:
            res = self.supabase_client.table("settings").select("value").eq("key", key).execute()
            return res.data[0]["value"] if res.data else None
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            conn.close()
            return json.loads(row[0]) if row else None

    def update_setting(self, key: str, value: Any) -> None:
        if self.use_supabase:
            self.supabase_client.table("settings").upsert({
                "key": key,
                "value": value
            }).execute()
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
                (key, json.dumps(value))
            )
            conn.commit()
            conn.close()

    # --- System Logs ---
    def add_system_log(self, service_name: str, log_level: str, message: str, metadata: Optional[Dict] = None) -> None:
        import uuid
        log_id = str(uuid.uuid4())
        data = {
            "id": log_id,
            "service_name": service_name,
            "log_level": log_level,
            "message": message,
            "metadata": metadata or {}
        }
        if self.use_supabase:
            try:
                self.supabase_client.table("system_logs").insert(data).execute()
            except:
                pass # Non-blocking log insert
        else:
            try:
                conn = sqlite3.connect(self.sqlite_db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO system_logs (id, service_name, log_level, message, metadata) VALUES (?, ?, ?, ?, ?)",
                    (log_id, service_name, log_level, message, json.dumps(metadata or {}))
                )
                conn.commit()
                conn.close()
            except:
                pass

    # --- Cart Methods ---
    def get_cart_items(self, conversation_id: str) -> List[Dict[str, Any]]:
        if self.use_supabase:
            res = self.supabase_client.table("carts").select("*").eq("conversation_id", conversation_id).execute()
            return res.data
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM carts WHERE conversation_id = ?", (conversation_id,))
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows

    def add_cart_item(self, conversation_id: str, product_name: str, quantity: int, price: float) -> Dict[str, Any]:
        import uuid
        cart_item_id = str(uuid.uuid4())
        data = {
            "id": cart_item_id,
            "conversation_id": conversation_id,
            "product_name": product_name,
            "quantity": quantity,
            "price": price
        }
        if self.use_supabase:
            res = self.supabase_client.table("carts").insert(data).execute()
            return res.data[0]
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO carts (id, conversation_id, product_name, quantity, price) VALUES (?, ?, ?, ?, ?)",
                (cart_item_id, conversation_id, product_name, quantity, price)
            )
            conn.commit()
            conn.close()
            return data

    def update_cart_item_quantity(self, conversation_id: str, product_name: str, quantity: int) -> None:
        if self.use_supabase:
            self.supabase_client.table("carts").update({"quantity": quantity}).eq("conversation_id", conversation_id).eq("product_name", product_name).execute()
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE carts SET quantity = ? WHERE conversation_id = ? AND product_name = ?",
                (quantity, conversation_id, product_name)
            )
            conn.commit()
            conn.close()

    def clear_cart(self, conversation_id: str) -> None:
        if self.use_supabase:
            self.supabase_client.table("carts").delete().eq("conversation_id", conversation_id).execute()
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM carts WHERE conversation_id = ?", (conversation_id,))
            conn.commit()
            conn.close()

    def delete_cart_item(self, conversation_id: str, product_name: str) -> None:
        if self.use_supabase:
            self.supabase_client.table("carts").delete().eq("conversation_id", conversation_id).eq("product_name", product_name).execute()
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM carts WHERE conversation_id = ? AND product_name = ?", (conversation_id, product_name))
            conn.commit()
            conn.close()


db = DatabaseClient()
