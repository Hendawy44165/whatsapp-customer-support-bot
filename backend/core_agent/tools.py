import os
import sys
import random
import datetime
from langchain_core.tools import tool

# Ensure backend package parent is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.database import db

# Product Catalog
PRODUCTS = {
    "signature": {"name": "Signature EDP 50ml", "price": 1450.0, "description": "Fresh citrus with warm amberwood, Extrait concentration."},
    "oud_royale": {"name": "Oud Royale 50ml", "price": 1850.0, "description": "Cambodian oud with Damascus rose, luxurious and deep."},
    "noir_intense": {"name": "Noir Intense 50ml", "price": 1650.0, "description": "Spicy cardamom, coffee, and dark vetiver."},
    "discovery_box": {"name": "Discovery Box trial bundle", "price": 450.0, "description": "3ml travel atomizers of our top 3 signature scents. Free shipping."}
}

# --- HubSpot CRM Tools ---
@tool
def get_contact_profile(email: str) -> str:
    """Retrieves the HubSpot CRM customer profile by email. Returns contact details, lifecycle stage, and custom notes."""
    try:
        db.add_system_log("hubspot_tool", "INFO", f"Looking up CRM profile for: {email}")
        
        # Simple mock profiles based on common email addresses
        if "mariam" in email.lower():
            return (
                f"HubSpot Contact Found:\n"
                f"- Name: Mariam Hegazi\n"
                f"- Email: {email}\n"
                f"- Lifecycle Stage: Customer\n"
                f"- Notes: Purchased Discovery Box trial on 2026-06-01. Prefers WhatsApp notifications. Flagged as highly receptive to premium citrus notes."
            )
        elif "youssef" in email.lower():
            return (
                f"HubSpot Contact Found:\n"
                f"- Name: Youssef Aly\n"
                f"- Email: {email}\n"
                f"- Lifecycle Stage: Lead\n"
                f"- Notes: Initiated checkout but abandoned. Active ticket #8732 regarding order status. Emotion history: Frustrated."
            )
        else:
            return (
                f"HubSpot Contact Found:\n"
                f"- Name: Guest Client ({email})\n"
                f"- Email: {email}\n"
                f"- Lifecycle Stage: Lead\n"
                f"- Notes: No previous purchases or support tickets recorded."
            )
    except Exception as e:
        db.add_system_log("hubspot_tool", "ERROR", f"Error in get_contact_profile for {email}: {str(e)}")
        return f"Error retrieving CRM profile: {str(e)}"

@tool
def create_support_ticket(email: str, subject: str, description: str) -> str:
    """Creates a new support ticket in HubSpot CRM. Returns the ticket number and confirmation message."""
    try:
        db.add_system_log("hubspot_tool", "INFO", f"Creating HubSpot ticket for {email}: {subject}")
        ticket_id = random.randint(10000, 99999)
        return (
            f"Successfully created HubSpot Support Ticket!\n"
            f"- Ticket ID: #HS-{ticket_id}\n"
            f"- Customer Email: {email}\n"
            f"- Subject: {subject}\n"
            f"- Description: {description}\n"
            f"- Status: OPEN (Assigned to General Support Queue)"
        )
    except Exception as e:
        db.add_system_log("hubspot_tool", "ERROR", f"Error creating ticket: {str(e)}")
        return f"Error creating support ticket: {str(e)}"

# --- Shop Cart Tools ---
@tool
def list_products() -> str:
    """Lists all available fragrances in the catalog with prices and sizes."""
    lines = ["Available Fragrance Catalog:"]
    for code, info in PRODUCTS.items():
        lines.append(f"- **{info['name']}**: {info['price']} EGP - {info['description']} (Code: '{code}')")
    return "\n".join(lines)

@tool
def add_to_cart(conversation_id: str, product_code: str, quantity: int = 1) -> str:
    """Adds a fragrance to the client's shopping cart. Accepts 'product_code' (e.g. 'signature')."""
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

        db.add_system_log("shop_cart_tool", "INFO", f"Added {quantity}x {product['name']} to cart {conversation_id}")
        return f"Successfully added {quantity}x **{product['name']}** to your cart."
    except Exception as e:
        return f"Error adding to cart: {str(e)}"

@tool
def edit_cart(conversation_id: str, product_code: str, quantity: int) -> str:
    """Modifies the quantity of a product in the cart. Set quantity to 0 to remove the item."""
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
            db.delete_cart_item(conversation_id, product["name"])
            return f"Removed **{product['name']}** from your cart."
        else:
            db.update_cart_item_quantity(conversation_id, product["name"], quantity)
            return f"Updated **{product['name']}** quantity in your cart to {quantity}."
    except Exception as e:
        return f"Error editing cart: {str(e)}"

@tool
def get_cart(conversation_id: str) -> str:
    """Retrieves the active cart contents and calculates total price."""
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
    except Exception as e:
        return f"Error retrieving cart: {str(e)}"

@tool
def generate_cart_report(conversation_id: str) -> str:
    """Programmatically generates a clean structured textual cart report (Without using AI generation)."""
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

# --- Conversations/Messaging Tools ---
@tool
def get_chat_history(conversation_id: str) -> str:
    """Retrieves the chronological text history of messages for context analysis."""
    try:
        messages = db.get_messages(conversation_id)
        if not messages:
            return "No previous message logs recorded for this conversation."

        history = []
        for m in messages:
            sender = "Customer" if m["sender_type"] == "customer" else "Nuit Concierge" if m["sender_type"] == "agent" else f"Human Expert"
            history.append(f"[{m['created_at']}] {sender}: {m['content']}")
        return "\n".join(history)
    except Exception as e:
        return f"Error retrieving history: {str(e)}"

@tool
def queue_immediate_message(conversation_id: str, content: str) -> str:
    """Queues a reply message in the outbound buffer to be sent immediately to the user."""
    try:
        msg_id = db.queue_outbound_message(conversation_id, content)
        db.add_system_log("conversations_tool", "INFO", f"Queued immediate message ID: {msg_id}")
        return f"Message queued successfully (ID: {msg_id}). Worker will dispatch it shortly."
    except Exception as e:
        return f"Error queueing message: {str(e)}"

@tool
def queue_scheduled_followup(conversation_id: str, content: str, delay_seconds: int) -> str:
    """Schedules an outbound follow-up message to the customer after a specific delay in seconds."""
    try:
        future_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=delay_seconds)
        future_iso = future_time.isoformat()

        msg_id = db.queue_outbound_message(conversation_id, content, scheduled_for=future_iso)
        db.add_system_log("conversations_tool", "INFO", f"Scheduled follow-up message ID {msg_id} in {delay_seconds}s")
        return f"Follow-up scheduled successfully (ID: {msg_id}, Dispatch at: {future_iso})."
    except Exception as e:
        return f"Error scheduling message: {str(e)}"

# --- Human Expert Routing Tool ---
@tool
def request_human_handoff(conversation_id: str, handoff_summary: str) -> str:
    """Triggers the human escalation pipeline, assigning the chat to the least loaded expert and providing a redirection deep-link."""
    try:
        db.add_system_log("human_expert_tool", "INFO", f"Handoff requested for conversation {conversation_id}")
        
        # 1. Update conversation status to pending_handoff and save summary
        db.update_conversation(conversation_id, {
            "status": "pending_handoff",
            "handoff_summary": handoff_summary
        })

        # 2. Attempt automatic load-based assignment
        experts = db.get_experts()
        online_experts = [e for e in experts if e["status"] == "online"]

        if online_experts:
            # Sort by current_load ascending (least loaded first)
            online_experts.sort(key=lambda x: x["current_load"])
            assigned_expert = online_experts[0]
            
            # Update conversation to handed_off and assign to the expert
            db.update_conversation(conversation_id, {
                "status": "handed_off",
                "assigned_expert_id": assigned_expert["id"]
            })
            
            db.add_system_log(
                "human_expert_tool", 
                "INFO", 
                f"Conversation {conversation_id} automatically assigned to expert {assigned_expert['name']} (Load: {assigned_expert['current_load']})"
            )
            
            return (
                f"Handoff success!\n"
                f"- Assigned Expert: {assigned_expert['name']}\n"
                f"- Deep Link Redirect: {assigned_expert['chat_redirect_url']}\n"
                f"Customer chat has been locked for the expert."
            )
        else:
            db.add_system_log("human_expert_tool", "WARNING", f"No online experts available. Conversation {conversation_id} added to the pending queue.")
            return "No online support experts are currently active. Conversation has been placed in the Shared Pending Queue."
            
    except Exception as e:
        db.add_system_log("human_expert_tool", "ERROR", f"Error in handoff execution for {conversation_id}: {str(e)}")
        return f"Error executing handoff routing: {str(e)}"
