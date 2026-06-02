import unittest
import os
import sys

# Add parent directory to path to import database and shop cart MCP
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db
from mcp_servers.shop_cart_mcp import (
    list_products,
    add_to_cart,
    edit_cart,
    get_cart,
    generate_cart_report
)

class TestShopCart(unittest.TestCase):
    def setUp(self):
        # Configure simulation database to use a test-specific SQLite file
        os.environ["SQLITE_SIM_DB"] = "test_cart_sim.db"
        self.conv_id = "test-session-123"
        db.__init__() # Re-init database client with the test DB path
        db.clear_cart(self.conv_id)

    def tearDown(self):
        # Clean up database tables
        db.clear_cart(self.conv_id)
        if os.path.exists("test_cart_sim.db"):
            try:
                os.remove("test_cart_sim.db")
            except:
                pass

    def test_list_products(self):
        catalog = list_products()
        self.assertIn("Signature EDP 50ml", catalog)
        self.assertIn("Oud Royale 50ml", catalog)

    def test_add_and_get_cart(self):
        # Add signature scent
        res = add_to_cart(self.conv_id, "signature", 2)
        self.assertIn("Successfully added 2x", res)

        # Get cart description
        cart_content = get_cart(self.conv_id)
        self.assertIn("2x **Signature EDP 50ml**", cart_content)
        self.assertIn("Total Cart Value: 2900.0 EGP", cart_content)

    def test_edit_cart_quantity(self):
        # Add item
        add_to_cart(self.conv_id, "oud_royale", 1)
        
        # Increase quantity to 3
        res = edit_cart(self.conv_id, "oud_royale", 3)
        self.assertIn("Updated **Oud Royale 50ml** quantity in your cart to 3", res)

        cart_content = get_cart(self.conv_id)
        self.assertIn("3x **Oud Royale 50ml**", cart_content)

        # Set quantity to 0 to remove
        res_remove = edit_cart(self.conv_id, "oud_royale", 0)
        self.assertIn("Removed **Oud Royale 50ml**", res_remove)
        
        cart_empty = get_cart(self.conv_id)
        self.assertEqual(cart_empty, "Your shopping cart is currently empty.")

    def test_programmatic_report_generation(self):
        add_to_cart(self.conv_id, "signature", 1)
        add_to_cart(self.conv_id, "discovery_box", 1)

        report = generate_cart_report(self.conv_id)
        
        self.assertIn("NUIT FRAGRANCES CART REPORT", report)
        self.assertIn("Signature EDP 50ml", report)
        self.assertIn("Discovery Box trial bundle", report)
        self.assertIn("FREE (Promo Bundle)", report) # Free shipping rule
        self.assertIn("Report generated programmatically via Shop Cart Engine V1", report)

if __name__ == "__main__":
    unittest.main()
