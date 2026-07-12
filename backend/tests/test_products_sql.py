import os
import sys
import unittest
import json
import sqlite3

# Ensure backend folder is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import db
from core_agent.tools.products_db import query_products_sql, get_product_details, search_products_by_description


class TestProductsSQL(unittest.TestCase):
    def setUp(self):
        # Force database initialization to ensure table exists and is seeded
        db._init_sqlite_tables()

    def test_database_seeding(self):
        """Test that products table exists and contains seeded values."""
        conn = sqlite3.connect(db.sqlite_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertGreater(count, 0, "Products table should be seeded with items.")

    def test_query_products_sql_in_stock(self):
        """Test SQL query tool for finding in-stock items."""
        # We query the tools directly
        res = query_products_sql.invoke({"sql_query": "SELECT name, stock_quantity FROM products WHERE stock_quantity > 0 AND category = 'flagship_edp_50ml' LIMIT 2"})
        data = json.loads(res)
        self.assertEqual(len(data), 2)
        for item in data:
            self.assertGreater(item["stock_quantity"], 0)

    def test_query_products_sql_out_of_stock(self):
        """Test SQL query tool for finding out-of-stock items (like Rum)."""
        res = query_products_sql.invoke({"sql_query": "SELECT name, stock_quantity FROM products WHERE stock_quantity = 0 AND variant = 'Rum'"})
        data = json.loads(res)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["stock_quantity"], 0)

    def test_query_products_sql_security_block(self):
        """Test that write/unsafe operations are rejected."""
        res = query_products_sql.invoke({"sql_query": "INSERT INTO products (id, name, price) VALUES ('test', 'Test Perfume', 50.0)"})
        self.assertIn("Error", res)
        self.assertIn("Only read-only SELECT queries are permitted", res)

        res2 = query_products_sql.invoke({"sql_query": "DELETE FROM products WHERE id = 'prod-lux-hatshepsut'"})
        self.assertIn("Error", res2)
        self.assertIn("Only read-only SELECT queries are permitted", res2)

    def test_get_product_details(self):
        """Test product details retriever tool."""
        res = get_product_details.invoke({"name": "Avec Hatshepsut"})
        data = json.loads(res)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Avec Hatshepsut (Nuit X Temraza)")

        res_variant = get_product_details.invoke({"name": "Flagship Eau de Parfum", "variant": "Rum"})
        data_variant = json.loads(res_variant)
        self.assertEqual(len(data_variant), 1)
        self.assertEqual(data_variant[0]["variant"], "Rum")

    def test_semantic_search(self):
        """Test the semantic search functionality for scent descriptions."""
        # Query that should highly match the Hatshepsut collaboration description (woody, amber, temraza)
        res = search_products_by_description.invoke({"description_query": "woody amber Temraza collaboration"})
        data = json.loads(res)
        self.assertGreater(len(data), 0)
        # First match should be Hatshepsut
        self.assertEqual(data[0]["name"], "Avec Hatshepsut (Nuit X Temraza)")


if __name__ == "__main__":
    unittest.main()
