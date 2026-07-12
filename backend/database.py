import os
import sqlite3
import json
import logging
import re
import math
from typing import Dict, List, Any, Optional

logger = logging.getLogger("database")


class DatabaseClient:
    """Local SQLite database client specifically for Nuit products.

    Provides database table initialization, seeding, query, details lookup,
    and a local TF-IDF Cosine Similarity semantic search index for product descriptions.
    """

    def __init__(self):
        self.sqlite_db_path = os.getenv("SQLITE_SIM_DB", "local_supabase_sim.db")
        logger.info(f"DatabaseClient: Initializing local products SQLite DB at: {self.sqlite_db_path}")
        self._init_sqlite_tables()

    def _init_sqlite_tables(self):
        """Creates the products table and seeds it if empty."""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()

        # Products Table
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

        # Seed products if empty
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            flagship_variants = [
                ("Rum", 0),  # Out of stock
                ("Dulce de Leche", 15),
                ("Head Turner", 8),
                ("Born in Milano", 25),
                ("Born in Vegas", 12),
                ("Bounty Hunter", 3),
                ("Red Flag", 0),  # Out of stock
                ("Green Flag", 9),
                ("Espresso Martini", 14),
                ("Forbidden Fruit", 7),
                ("Casa Di Rosa", 0),  # Out of stock
                ("Lindo Día", 18),
                ("Monroe", 22),
                ("Warm Vanilla", 30),
                ("French Foulard", 5),
                ("True Hipster", 11),
                ("Leather Jacket", 6),
                ("Cappuccina", 4),
                ("Choco Frappe", 0),  # Out of stock
                ("Hazelwood", 16),
                ("Heritage", 13),
                ("I am Harvey", 20)
            ]

            for var_name, stock in flagship_variants:
                cursor.execute(
                    "INSERT INTO products (id, category, name, price, promo_price, variant, stock_quantity, is_available, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"prod-edp-{var_name.lower().replace(' ', '-')}",
                        "flagship_edp_50ml",
                        f"Flagship Eau de Parfum - {var_name}",
                        855.00,
                        599.00,
                        var_name,
                        stock,
                        1 if stock > 0 else 0,
                        f"Nuit Flagship 50ml Eau de Parfum in the exquisite {var_name} variant. Scent profile features warm, premium, elegant fragrance notes."
                    )
                )

            # Luxury Collaboration
            cursor.execute(
                "INSERT INTO products (id, category, name, price, promo_price, variant, stock_quantity, is_available, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "prod-lux-hatshepsut",
                    "luxury_collaboration",
                    "Avec Hatshepsut (Nuit X Temraza)",
                    1950.00,
                    None,
                    None,
                    5,
                    1,
                    "Exclusive art flacon collaboration with Temraza. Highly exclusive luxury collector's edition, not eligible for standard EDP discounts. Rich woody, warm spicy, and deep amber fragrance notes."
                )
            )

            # Concentrated Perfume Oils (Shots)
            shots = [
                ("Vanilla Shot", 12),
                ("Born in Milano Shot", 0),  # Out of stock
                ("Caramel Shot", 8),
                ("Head Turner Shot", 15)
            ]
            for shot_name, stock in shots:
                cursor.execute(
                    "INSERT INTO products (id, category, name, price, promo_price, variant, stock_quantity, is_available, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"prod-oil-{shot_name.lower().replace(' ', '-')}",
                        "perfume_oils_shots_khamrias",
                        shot_name,
                        475.00,
                        None,
                        None,
                        stock,
                        1 if stock > 0 else 0,
                        f"Highly concentrated premium Nuit perfume oil / khamria in {shot_name} variant. Scent profile features sweet vanilla, caramel, floral accords, and amber notes."
                    )
                )

            # Body Splash & Mists
            mists = [
                ("Soft Cloud Heart", 20),
                ("Very Delicate Vanilla", 15),
                ("The Harvey Splash", 0)  # Out of stock
            ]
            for mist_name, stock in mists:
                cursor.execute(
                    "INSERT INTO products (id, category, name, price, promo_price, variant, stock_quantity, is_available, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"prod-mist-{mist_name.lower().replace(' ', '-')}",
                        "body_splash_mists",
                        mist_name,
                        315.00,
                        None,
                        None,
                        stock,
                        1 if stock > 0 else 0,
                        f"Refreshing premium Nuit body splash / mist in {mist_name} variant. Light, clean, sweet vanilla, fresh floral scent notes."
                    )
                )

        conn.commit()
        conn.close()

    def get_products(self) -> List[Dict[str, Any]]:
        """Retrieves all products from the local SQL database."""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_product_details(self, name: str, variant: Optional[str] = None) -> List[Dict[str, Any]]:
        """Gets detailed information of specific products/variants by name match."""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if variant:
            cursor.execute(
                "SELECT * FROM products WHERE (name LIKE ? OR category = ?) AND variant LIKE ?",
                (f"%{name}%", name, f"%{variant}%")
            )
        else:
            cursor.execute(
                "SELECT * FROM products WHERE name LIKE ? OR category = ?",
                (f"%{name}%", name)
            )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def semantic_search_products(self, query: str) -> List[Dict[str, Any]]:
        """Search products by description using a TF-IDF Cosine Similarity vector space model."""
        products = self.get_products()
        if not products:
            return []

        def compute_tf(text: str) -> dict:
            words = re.findall(r'\b\w+\b', text.lower())
            tf = {}
            for word in words:
                tf[word] = tf.get(word, 0) + 1
            total = len(words) or 1
            for word in tf:
                tf[word] = tf[word] / total
            return tf

        def compute_idf(documents: list) -> dict:
            N = len(documents)
            idf = {}
            for doc in documents:
                words = set(re.findall(r'\b\w+\b', doc.lower()))
                for word in words:
                    idf[word] = idf.get(word, 0) + 1
            for word in idf:
                idf[word] = math.log((N + 1) / (idf[word] + 1)) + 1
            return idf

        def get_cosine_similarity(vec1: dict, vec2: dict) -> float:
            intersection = set(vec1.keys()) & set(vec2.keys())
            numerator = sum([vec1[x] * vec2[x] for x in intersection])
            sum1 = sum([vec1[x]**2 for x in vec1.keys()])
            sum2 = sum([vec2[x]**2 for x in vec2.keys()])
            denominator = math.sqrt(sum1) * math.sqrt(sum2)
            if not denominator:
                return 0.0
            return numerator / denominator

        descriptions = [p.get("description", "") or "" for p in products]
        documents = descriptions + [query]
        idf = compute_idf(documents)

        query_tf = compute_tf(query)
        query_vec = {word: tf_val * idf.get(word, 0.0) for word, tf_val in query_tf.items()}

        scored_products = []
        for product in products:
            p_desc = product.get("description", "") or ""
            p_tf = compute_tf(p_desc)
            p_vec = {word: tf_val * idf.get(word, 0.0) for word, tf_val in p_tf.items()}
            sim = get_cosine_similarity(query_vec, p_vec)
            if sim > 0:
                scored_products.append((sim, product))

        scored_products.sort(key=lambda x: x[0], reverse=True)
        return [p for score, p in scored_products][:10]


db = DatabaseClient()
