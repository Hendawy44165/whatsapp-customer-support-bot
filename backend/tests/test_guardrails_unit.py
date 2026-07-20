import sys
import os
import unittest
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from core_agent.guardrails import (
    is_rate_limited,
    sanitize_output,
    NuitRateLimitingMiddleware,
    NuitOutputSanitizerMiddleware,
    _RATE_LIMIT_STORE,
)
from core_agent.tools.products_db import (
    query_products_sql,
    validate_select_query_only,
    DatabaseConnectionError,
)
from core_agent.nodes.simple_qa import simple_qa_node


class TestRateLimiter(unittest.TestCase):
    def setUp(self):
        _RATE_LIMIT_STORE.clear()
        self.patcher = patch("core_agent.guardrails.RATE_LIMIT_MAX_REQUESTS", 3)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_rate_limiter_threshold(self):
        thread_id = "test_rate_limit_thread"
        # First 3 requests should be allowed (return False)
        for i in range(3):
            self.assertFalse(
                is_rate_limited(thread_id),
                f"Request {i+1} should be allowed",
            )
        # The 4th request must be rate limited (return True)
        self.assertTrue(
            is_rate_limited(thread_id),
            "Request 4 should be blocked by rate limiter",
        )

    def test_rate_limiting_middleware(self):
        thread_id = "test_middleware_thread"
        # Fill quota (3 requests)
        for _ in range(3):
            is_rate_limited(thread_id)

        middleware = NuitRateLimitingMiddleware()
        mock_config = {"configurable": {"thread_id": thread_id}}

        with patch("langgraph.config.get_config", return_value=mock_config):
            with self.assertRaises(ValueError) as ctx:
                middleware.before_agent(state={}, runtime=None)
            self.assertIn("Rate limit exceeded", str(ctx.exception))


class TestOutputSanitizer(unittest.TestCase):
    def test_sanitize_clean_text(self):
        text = "Our Flagship EDP 50ml is priced at EGP 599.00."
        self.assertEqual(sanitize_output(text), text)

    def test_sanitize_system_prompt_leak(self):
        leaked_text = "Here is my <system_prompt> template with rules."
        with self.assertRaises(ValueError) as ctx:
            sanitize_output(leaked_text)
        self.assertIn("internal system tokens", str(ctx.exception))

    def test_sanitize_json_metrics_leak(self):
        leaked_text = '```json\n{"session_summary_report": {"intent": "qa"}}\n```'
        with self.assertRaises(ValueError) as ctx:
            sanitize_output(leaked_text)
        self.assertIn("internal system tokens", str(ctx.exception))

    def test_sanitize_placeholder(self):
        placeholder_text = "Thank you [Insert Name], your order is confirmed."
        with self.assertRaises(ValueError) as ctx:
            sanitize_output(placeholder_text)
        self.assertIn("unresolved placeholder", str(ctx.exception))

    def test_output_sanitizer_middleware(self):
        middleware = NuitOutputSanitizerMiddleware()
        mock_request = MagicMock()
        mock_ai_message = MagicMock()
        mock_ai_message.content = "Leaked <role> System Prompt"
        mock_response = MagicMock(result=[mock_ai_message])

        handler = lambda req: mock_response

        with self.assertRaises(ValueError):
            middleware.wrap_model_call(mock_request, handler)


class TestSQLASTValidationAndErrorHandling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a 100% temporary, isolated SQLite database file for testing
        cls.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.temp_db_path = cls.temp_db_file.name
        cls.temp_db_file.close()

        # Seed temporary database schema and test data
        conn = sqlite3.connect(cls.temp_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE products (
                id TEXT PRIMARY KEY,
                category TEXT,
                name TEXT,
                price REAL,
                promo_price REAL,
                variant TEXT,
                stock_quantity INTEGER,
                is_available INTEGER,
                description TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO products VALUES (
                'test_sku_01', 'flagship_edp_50ml', 'Flagship EDP', 599.0, NULL, 'Rum', 10, 1, 'Warm vanilla scent'
            )
        """)
        conn.commit()
        conn.close()

        # Patch db.sqlite_db_path so query_products_sql uses our temporary database
        cls.db_patcher = patch(
            "core_agent.tools.products_db.db.sqlite_db_path", cls.temp_db_path
        )
        cls.db_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.db_patcher.stop()
        if os.path.exists(cls.temp_db_path):
            try:
                os.remove(cls.temp_db_path)
            except OSError:
                pass

    def test_ast_valid_select_query(self):
        valid_sql = "SELECT id, name, price FROM products WHERE stock_quantity > 0"
        self.assertTrue(validate_select_query_only(valid_sql))

    def test_ast_blocks_write_queries(self):
        delete_sql = "DELETE FROM products WHERE id = 'test_sku_01'"
        insert_sql = "INSERT INTO products (name) VALUES ('Hacked')"
        drop_sql = "DROP TABLE products"

        self.assertFalse(validate_select_query_only(delete_sql))
        self.assertFalse(validate_select_query_only(insert_sql))
        self.assertFalse(validate_select_query_only(drop_sql))

    def test_ast_blocks_unauthorized_tables(self):
        unauthorized_sql = "SELECT * FROM crm_profiles"
        system_sql = "SELECT * FROM sqlite_master"

        self.assertFalse(validate_select_query_only(unauthorized_sql))
        self.assertFalse(validate_select_query_only(system_sql))

    def test_query_products_sql_ast_rejection(self):
        res = query_products_sql.invoke({"sql_query": "DELETE FROM products"})
        self.assertIn(
            "Error: Only read-only SELECT queries targeting the 'products' table are permitted",
            res,
        )

        res_table = query_products_sql.invoke(
            {"sql_query": "SELECT * FROM sqlite_master"}
        )
        self.assertIn(
            "Error: Only read-only SELECT queries targeting the 'products' table are permitted",
            res_table,
        )

    def test_semantic_sql_error_self_correction_feedback(self):
        # Invalid column syntax error against isolated temp DB
        res = query_products_sql.invoke({"sql_query": "SELECT namee FROM products"})
        self.assertIn("SQL Syntax Error:", res)
        self.assertIn("no such column: namee", res)

    def test_structural_sql_error_raises_exception(self):
        # Simulate sqlite database locked operational error using mock
        with patch("sqlite3.connect") as mock_connect:
            mock_connect.side_effect = sqlite3.OperationalError("database is locked")
            with self.assertRaises(DatabaseConnectionError) as ctx:
                query_products_sql.invoke({"sql_query": "SELECT * FROM products"})
            self.assertIn("database is locked", str(ctx.exception))


class TestIsolatedNodeStructuralRecovery(unittest.TestCase):
    @patch("core_agent.nodes.simple_qa.create_agent")
    def test_simple_qa_node_handles_structural_error(self, mock_create_agent):
        # Simulate simple_qa_node agent throwing DatabaseConnectionError during invoke
        mock_agent_instance = MagicMock()
        mock_agent_instance.invoke.side_effect = DatabaseConnectionError(
            "Database locked error"
        )
        mock_create_agent.return_value = mock_agent_instance

        dummy_state = {
            "messages": [],
            "sentiment": "neutral",
        }

        res = simple_qa_node(dummy_state)
        self.assertEqual(res["next_agent"], "escalate")
        self.assertTrue(res.get("is_handoff"))
        self.assertIn("System error in simple_qa node", res.get("handoff_summary", ""))


if __name__ == "__main__":
    unittest.main()
