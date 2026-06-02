# Static mock order database for Nuit Fragrances customer order tracking

MOCK_ORDERS_DB = {
    "NUIT-1001": {
        "order_id": "NUIT-1001",
        "customer_name": "John Doe",
        "mobile_number": "+201234567890",
        "status": "delivered",
        "items": "Signature EDP 50ml",
        "carrier": "Aramex",
        "tracking_number": "AX-998273-EG",
        "estimated_delivery": "Completed on May 28, 2026"
    },
    "NUIT-1002": {
        "order_id": "NUIT-1002",
        "customer_name": "Sarah Ahmed",
        "mobile_number": "+201099887766",
        "status": "shipped",
        "items": "Discovery Box trial bundle",
        "carrier": "Bosta",
        "tracking_number": "BS-112233-EG",
        "estimated_delivery": "June 4, 2026 (In Transit)"
    },
    "NUIT-1003": {
        "order_id": "NUIT-1003",
        "customer_name": "Sherif Mahmoud",
        "mobile_number": "+201554433221",
        "status": "processing",
        "items": "Discovery Box trial bundle, Signature EDP 50ml",
        "carrier": "Bosta",
        "tracking_number": "BS-445566-EG",
        "estimated_delivery": "June 6, 2026 (Processing in Warehouse)"
    }
}
