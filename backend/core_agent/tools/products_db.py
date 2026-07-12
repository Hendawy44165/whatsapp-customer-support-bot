import os
import sys
import sqlite3
import re
import json
from typing import Optional
from langchain_core.tools import tool

# Ensure backend folder is in path for database import
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import db


@tool
def query_products_sql(sql_query: str) -> str:
    """Executes a read-only SQL query on the 'products' table.

    The table schema is:
    - id (TEXT PRIMARY KEY): unique product variant identifier
    - category (TEXT): product category (e.g. 'flagship_edp_50ml', 'luxury_collaboration', 'perfume_oils_shots_khamrias', 'body_splash_mists')
    - name (TEXT): product display name
    - price (REAL): standard price in EGP
    - promo_price (REAL): promo price in EGP (may be NULL)
    - variant (TEXT): variant name (may be NULL)
    - stock_quantity (INTEGER): units in stock
    - is_available (BOOLEAN): 1 if stock_quantity > 0, else 0
    - description (TEXT): detailed description

    Use this tool to find:
    - in stock products (stock_quantity > 0)
    - out of stock products (stock_quantity = 0)
    - available products (is_available = 1)
    
    Only read-only SELECT queries are allowed.
    """
    # Safety Check: only allow SELECT queries
    query_stripped = sql_query.strip().lower()
    if not query_stripped.startswith("select"):
        return "Error: Only read-only SELECT queries are permitted on the products database."

    # Prevent write operations or command chaining
    forbidden_keywords = ["insert", "update", "delete", "drop", "alter", "create", "replace", "truncate"]
    for keyword in forbidden_keywords:
        if re.search(r'\b' + re.escape(keyword) + r'\b', query_stripped):
            return f"Error: Forbidden keyword '{keyword}' detected. Only read-only SELECT queries are permitted."

    try:
        conn = sqlite3.connect(db.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "No matching products found."

        results = [dict(row) for row in rows]
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"SQL Execution Error: {str(e)}"


@tool
def get_product_details(name: str, variant: Optional[str] = None) -> str:
    """Retrieves detailed information about a specific product and/or variant from the products database.

    Args:
        name: The name of the product (e.g. 'Flagship Eau de Parfum', 'Avec Hatshepsut', 'Vanilla Shot', 'Soft Cloud Heart')
        variant: Optional variant name (e.g. 'Rum', 'Dulce de Leche') for flagship perfumes.
    """
    try:
        conn = sqlite3.connect(db.sqlite_db_path)
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

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return f"No product details found matching name '{name}'" + (f" and variant '{variant}'" if variant else "")

        results = [dict(row) for row in rows]
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error retrieving product details: {str(e)}"


@tool
def search_products_by_description(description_query: str) -> str:
    """Searches the products database semantically by product description.

    Use this when the customer asks for a fragrance based on notes, moods, ingredients, or descriptors (e.g. 'woody', 'sweet vanilla', 'warm spicy', 'refreshing fresh').

    Args:
        description_query: The text query describing fragrance notes or characteristics.
    """
    try:
        results = db.semantic_search_products(description_query)
        if not results:
            return f"No products found matching description query: '{description_query}'"
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error performing semantic search: {str(e)}"
