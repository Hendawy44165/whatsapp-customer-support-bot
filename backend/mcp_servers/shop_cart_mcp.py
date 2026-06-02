import os
import sys
from mcp.server.fastmcp import FastMCP

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db

# Create FastMCP server
mcp = FastMCP("Nuit Shop Cart Handling")

# Product Catalog
PRODUCTS = {
    "signature": {"name": "Signature EDP 50ml", "price": 1450.0, "description": "Fresh citrus with warm amberwood, Extrait concentration."},
    "oud_royale": {"name": "Oud Royale 50ml", "price": 1850.0, "description": "Cambodian oud with Damascus rose, luxurious and deep."},
    "noir_intense": {"name": "Noir Intense 50ml", "price": 1650.0, "description": "Spicy cardamom, coffee, and dark vetiver."},
    "discovery_box": {"name": "Discovery Box trial bundle", "price": 450.0, "description": "3ml travel atomizers of our top 3 signature scents. Free shipping."}
}

@mcp.tool()
def list_products() -> str:
    """
    Lists all available fragrances in the catalog with prices and sizes.
    """
    lines = ["Available Fragrance Catalog:"]
    for code, info in PRODUCTS.items():
        lines.append(f"- **{info['name']}**: {info['price']} EGP - {info['description']} (Code: '{code}')")
    return "\n".join(lines)

@mcp.tool()
def add_to_cart(conversation_id: str, product_code: str, quantity: int = 1) -> str:
    """
    Adds a fragrance to the client's shopping cart.
    Accepts 'product_code' (e.g. 'signature', 'oud_royale', 'noir_intense', 'discovery_box').
    """
    code = product_code.strip().lower()
    if code not in PRODUCTS:
        return f"Error: Product code '{product_code}' not found in catalog. Available codes: {list(PRODUCTS.keys())}"

    product = PRODUCTS[code]
    try:
        # Check if conversation exists
        conv = db.get_conversation(conversation_id)
        if not conv:
            # Create a mock one if missing
            db.create_conversation(conversation_id, "+201000000000", "whatsapp")

        # Check if item is already in cart
        items = db.get_cart_items(conversation_id)
        existing_item = next((item for item in items if item["product_name"] == product["name"]), None)

        if existing_item:
            new_qty = existing_item["quantity"] + quantity
            db.update_cart_item_quantity(conversation_id, product["name"], new_qty)
        else:
            db.add_cart_item(conversation_id, product["name"], quantity, product["price"])

        db.add_system_log("shop_cart_mcp", "INFO", f"Added {quantity}x {product['name']} to cart {conversation_id}")
        return f"Successfully added {quantity}x **{product['name']}** to your cart."
    except Exception as e:
        return f"Error adding to cart: {str(e)}"

@mcp.tool()
def edit_cart(conversation_id: str, product_code: str, quantity: int) -> str:
    """
    Modifies the quantity of a product in the cart.
    Set quantity to 0 to remove the item.
    """
    code = product_code.strip().lower()
    if code not in PRODUCTS:
        return f"Error: Product code '{product_code}' not found in catalog. Available codes: {list(PRODUCTS.keys())}"

    product = PRODUCTS[code]
    try:
        items = db.get_cart_items(conversation_id)
        existing_item = next((item for item in items if item["product_name"] == product["name"]), None)

        if not existing_item:
            return f"Error: '{product['name']}' is not in your cart."

        if quantity <= 0:
            # Remove item
            conn = os.getenv("SQLITE_SIM_DB", "local_supabase_sim.db")
            import sqlite3
            db_conn = sqlite3.connect(conn)
            cursor = db_conn.cursor()
            cursor.execute("DELETE FROM carts WHERE conversation_id = ? AND product_name = ?", (conversation_id, product["name"]))
            db_conn.commit()
            db_conn.close()
            return f"Removed **{product['name']}** from your cart."
        else:
            db.update_cart_item_quantity(conversation_id, product["name"], quantity)
            return f"Updated **{product['name']}** quantity in your cart to {quantity}."
    except Exception as e:
        return f"Error editing cart: {str(e)}"

@mcp.tool()
def get_cart(conversation_id: str) -> str:
    """
    Retrieves the active cart contents and calculates total price.
    """
    try:
        items = db.get_cart_items(conversation_id)
        if not items:
            return "Your shopping cart is currently empty."

        lines = ["Your Shopping Cart:"]
        total = 0.0
        for item in items:
            subtotal = item["quantity"] * item["price"]
            total += subtotal
            lines.append(f"- {item['quantity']}x **{item['product_name']}** @ {item['price']} EGP each (Subtotal: {subtotal} EGP)")
        lines.append(f"**Total Cart Value**: {total} EGP")
        return "\n".join(lines)

@mcp.tool()
def generate_cart_report(conversation_id: str) -> str:
    """
    Programmatically generates a clean structured textual cart report (Without using AI generation).
    Useful to summarize items and pricing before handoff or checkout confirmation.
    """
    try:
        items = db.get_cart_items(conversation_id)
        if not items:
            return "--- SHOPPING CART REPORT ---\nStatus: Empty\nTotal: 0 EGP\n----------------------------"

        total = 0.0
        report_lines = [
            "=========================================",
            "        NUIT FRAGRANCES CART REPORT      ",
            "=========================================",
            f"Conversation ID: {conversation_id}",
            "-----------------------------------------",
            "Items in Cart:"
        ]
        
        for idx, item in enumerate(items, start=1):
            subtotal = item["quantity"] * item["price"]
            total += subtotal
            report_lines.append(
                f"{idx}. {item['product_name']}\n"
                f"   Qty: {item['quantity']} | Unit Price: {item['price']} EGP\n"
                f"   Subtotal: {subtotal} EGP"
            )
            
        report_lines.extend([
            "-----------------------------------------",
            f"Gross Total: {total} EGP",
            f"Shipping Fee: {'FREE (Promo Bundle)' if any('Discovery Box' in it['product_name'] for it in items) or total >= 1000 else '50 EGP'}",
            f"Grand Total: {total if (any('Discovery Box' in it['product_name'] for it in items) or total >= 1000) else (total + 50)} EGP",
            "=========================================",
            "Report generated programmatically via Shop Cart Engine V1."
        ])
        
        return "\n".join(report_lines)
    except Exception as e:
        return f"Error generating cart report: {str(e)}"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp.asgi_app, host="0.0.0.0", port=8012)
