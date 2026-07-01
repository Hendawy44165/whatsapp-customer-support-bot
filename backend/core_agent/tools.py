import json
from langchain_core.tools import tool

# Simple mock database matching the customer scenarios
MOCK_ORDERS = {
    "3021": {
        "phone": "01023456789",
        "status": "delivered",
        "delivery_date": "2026-06-25",
        "items": ["Nuit Signature 50ml"],
        "price": 1450.0,
        "eligible_for_return": True
    },
    "4022": {
        "phone": "01234567890",
        "status": "shipped",
        "eta": "2 days",
        "items": ["Temraza Edition 50ml"],
        "price": 1850.0,
        "eligible_for_return": False
    },
    "5023": {
        "phone": "01098765432",
        "status": "cancelled",
        "reason": "payment_failed",
        "items": ["Discovery Box"],
        "price": 368.0,
        "eligible_for_return": False
    }
}

@tool
def mock_crm_tool(action: str, phone: str = "", order_id: str = "", payload: dict = None) -> str:
    """
    Simulates HubSpot CRM database transactions. Updates are atomic.
    
    Args:
        action: The operation to run: 'lookup_order' | 'register_return' | 'register_exchange'.
        phone: The customer's mobile number.
        order_id: The order ID reference.
        payload: Optional configuration data for return/exchange reasons or items.
        
    Returns:
        JSON string containing the execution status and details.
    """
    clean_order_id = str(order_id).strip()
    clean_phone = str(phone).strip()
    
    if action == "lookup_order":
        # Match by order_id or phone
        if clean_order_id in MOCK_ORDERS:
            order = MOCK_ORDERS[clean_order_id]
            if clean_phone and order["phone"] != clean_phone:
                return json.dumps({"status": "not_found", "message": "Phone number does not match order ID."})
            return json.dumps({"status": "success", "order_id": clean_order_id, "data": order})
        
        # Fallback to search by phone
        for oid, order in MOCK_ORDERS.items():
            if clean_phone and order["phone"] == clean_phone:
                return json.dumps({"status": "success", "order_id": oid, "data": order})
                
        return json.dumps({"status": "not_found", "message": "No order matching order ID or phone found."})
        
    elif action in ("register_return", "register_exchange"):
        if not clean_order_id or clean_order_id not in MOCK_ORDERS:
            return json.dumps({"status": "error", "message": f"Order {clean_order_id} not found."})
            
        order = MOCK_ORDERS[clean_order_id]
        
        # Verify eligibility
        if not order["eligible_for_return"]:
            return json.dumps({
                "status": "failed", 
                "message": "Item is not eligible for return/exchange (out of 14-day window or promo item)."
            })
            
        # Simulating atomic transaction write
        # In a real app this wraps a SQL Transaction / db.commit()
        try:
            # Stage exchange/return payload processing
            item_requested = (payload or {}).get("item")
            reason = (payload or {}).get("reason", "not_specified")
            
            # Atomic commit success simulation
            return json.dumps({
                "status": "success",
                "transaction_type": action,
                "order_id": clean_order_id,
                "committed_update": {
                    "item": item_requested or order["items"][0],
                    "reason": reason,
                    "timestamp": "2026-07-01T19:28:00Z"
                }
            })
        except Exception as e:
            # Atomic rollback simulation
            return json.dumps({
                "status": "rollback_failed",
                "message": f"Database transaction crashed and rolled back. Error: {str(e)}"
            })
            
    return json.dumps({"status": "invalid_action", "message": f"Action '{action}' is not supported."})
