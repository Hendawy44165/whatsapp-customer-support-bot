import unittest
import os
import sys
import time
import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db

class TestMessageBuffer(unittest.TestCase):
    def setUp(self):
        os.environ["SQLITE_SIM_DB"] = "test_buffer_sim.db"
        self.conv_id = "test-conv-buffer"
        db.__init__()
        
        # Clean and create dummy conversation
        import sqlite3
        conn = sqlite3.connect("test_buffer_sim.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations")
        cursor.execute("DELETE FROM message_buffer")
        cursor.execute(
            "INSERT INTO conversations (id, customer_phone, platform, status) VALUES (?, ?, ?, ?)",
            (self.conv_id, "+201010101010", "whatsapp", "active")
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists("test_buffer_sim.db"):
            try:
                os.remove("test_buffer_sim.db")
            except:
                pass

    def test_immediate_message_buffering(self):
        # Queue immediate message
        msg_id = db.queue_outbound_message(self.conv_id, "Hello Customer immediately!")
        
        # Check that it appears in pending messages
        pending = db.get_pending_buffered_messages()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], msg_id)
        self.assertEqual(pending[0]["content"], "Hello Customer immediately!")
        self.assertEqual(pending[0]["status"], "pending")

        # Mark sent
        db.mark_buffered_message_sent(msg_id)
        
        # Should no longer be pending
        pending_after = db.get_pending_buffered_messages()
        self.assertEqual(len(pending_after), 0)

    def test_scheduled_message_buffering(self):
        # Queue message scheduled for 10 seconds in the future
        future_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=10)
        msg_id_future = db.queue_outbound_message(
            self.conv_id, 
            "Hello scheduled customer!", 
            scheduled_for=future_time.isoformat()
        )
        
        # Queue message scheduled for 5 seconds in the past (should be sent immediately)
        past_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=5)
        msg_id_past = db.queue_outbound_message(
            self.conv_id, 
            "Hello overdue customer!", 
            scheduled_for=past_time.isoformat()
        )

        # Get pending messages: should ONLY return the overdue one
        pending = db.get_pending_buffered_messages()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], msg_id_past)
        self.assertEqual(pending[0]["content"], "Hello overdue customer!")

if __name__ == "__main__":
    unittest.main()
