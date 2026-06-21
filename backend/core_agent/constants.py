"""
Constants and configurations for the Nuit Fragrances Customer Service Agent.
"""

VALID_CATEGORIES = {
    "unrelated_or_harmful",
    "greeting_or_chitchat",
    "order_tracking",
    "faq_shipping_egypt",
    "faq_shipping_intl",
    "faq_returns_refunds",
    "faq_discovery_box",
    "complex_uncategorized"
}

DIRECT_RESPONSES = {
    "unrelated_or_harmful": (
        "I want to ensure you receive completely accurate details on that matter. "
        "Let me verify our specific inventory files or connect you directly with a specialist from our care team. "
        "May I please have your phone number to look up your order profile?"
    ),
    "greeting_or_chitchat": (
        "Hello and welcome to Nuit Fragrances! I'm here to assist you with our luxury fragrances, order details, or policies. "
        "How can I help you today?"
    ),
    "order_tracking": (
        "To track your shipment, please provide your **order number** or the **mobile number** used during checkout. "
        "Once shared, I will locate your shipping status."
    ),
    "faq_shipping_egypt": (
        "Domestic shipping across Egypt is a flat fee of **EGP 80.00**, and is completely **free** for orders above **EGP 1,500.00**. "
        "Delivery typically takes **3 to 5 business days**."
    ),
    "faq_shipping_intl": (
        "We ship worldwide! International shipping has a flat fee of **EGP 650.00** with a transit timeline of **7 to 14 business days**."
    ),
    "faq_returns_refunds": (
        "Returns and exchanges are accepted for **defective or damaged items only** within **14 calendar days** of delivery. "
        "Scent preference, blind buys, and sales/promo items are strictly ineligible for refund or exchange."
    ),
    "faq_discovery_box": (
        "Our Discovery Box miniatures trial bundle is available at a promo price of **EGP 368.00** (regularly **EGP 525.00**) with **free domestic shipping** inside Egypt."
    )
}
