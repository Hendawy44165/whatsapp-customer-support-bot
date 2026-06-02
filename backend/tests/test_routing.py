import unittest
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db
from mcp_servers.human_expert_mcp import request_human_handoff

class TestExpertRouting(unittest.TestCase):
    def setUp(self):
        os.environ["SQLITE_SIM_DB"] = "test_routing_sim.db"
        self.conv_id = "test-session-escalation"
        db.__init__()
        
        # Reset and mock expert profiles
        # We will directly insert into SQLite DB
        import sqlite3
        conn = sqlite3.connect("test_routing_sim.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM experts")
        cursor.execute("DELETE FROM conversations")
        
        # Insert 3 mock experts:
        # Expert A: Online, load = 3
        # Expert B: Online, load = 1
        # Expert C: Offline, load = 0
        cursor.execute(
            "INSERT INTO experts (id, name, email, status, current_load, chat_redirect_url) VALUES (?, ?, ?, ?, ?, ?)",
            ("exp-a", "Expert A", "a@nuit.com", "online", 3, "http://wa.me/a")
        )
        cursor.execute(
            "INSERT INTO experts (id, name, email, status, current_load, chat_redirect_url) VALUES (?, ?, ?, ?, ?, ?)",
            ("exp-b", "Expert B", "b@nuit.com", "online", 1, "http://wa.me/b")
        )
        cursor.execute(
            "INSERT INTO experts (id, name, email, status, current_load, chat_redirect_url) VALUES (?, ?, ?, ?, ?, ?)",
            ("exp-c", "Expert C", "c@nuit.com", "offline", 0, "http://wa.me/c")
        )
        
        # Insert conversation
        cursor.execute(
            "INSERT INTO conversations (id, customer_phone, platform, status) VALUES (?, ?, ?, ?)",
            (self.conv_id, "+201010101010", "whatsapp", "active")
        )
        
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists("test_routing_sim.db"):
            try:
                os.remove("test_routing_sim.db")
            except:
                pass

    def test_automatic_routing_least_load(self):
        # Call handoff tool. Should automatically route to Expert B (online, load=1)
        # instead of A (load=3) or C (offline)
        res = request_human_handoff(self.conv_id, "Customer claims nozzle leaks.")
        
        self.assertIn("Assigned Expert: Expert B", res)
        self.assertIn("http://wa.me/b", res)

        # Check conversation record in DB
        conv = db.get_conversation(self.conv_id)
        self.assertEqual(conv["status"], "handed_off")
        self.assertEqual(conv["assigned_expert_id"], "exp-b")
        self.assertEqual(conv["handoff_summary"], "Customer claims nozzle leaks.")

    def test_routing_no_online_experts(self):
        # Set all experts offline
        db.update_expert_status("exp-a", "offline")
        db.update_expert_status("exp-b", "offline")

        res = request_human_handoff(self.conv_id, "Customer claims nozzle leaks.")
        self.assertIn("No online support experts are currently active", res)

        # Conversation status should be pending_handoff
        conv = db.get_conversation(self.conv_id)
        self.assertEqual(conv["status"], "pending_handoff")
        self.assertIsNone(conv["assigned_expert_id"])

if __name__ == "__main__":
    unittest.main()
