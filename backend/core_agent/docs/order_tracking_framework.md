---
sop_name: "Order Tracking and Delivery Support Framework"
required_docs:
  - terms_of_conditions_and_policies.md
  - negation_handling_sop.md
required_tools:
  - lookup_order
---

# Order Tracking and Delivery Support Framework

## Objective
Handle all order status, tracking, and delivery issue inquiries — including delayed, missing, or problem deliveries — in a calm, factual, and customer-first manner.

## Scope
Any request where a customer wants to know where their order is, when it will arrive, or what happened to a delivery.

---

## Decision Gate (Run Before Planning Turns)

**Check what's available:**
- `order_id` or `phone` already provided → skip collection turn, go directly to lookup turn
- Neither available → Turn 1 must collect one identifier

**After lookup, determine path:**
- Order in processing or in transit, within standard window → **Normal Path**
- Order delayed beyond standard window, or marked delivered but customer says not received → **Problem Path**

Standard delivery windows:
- Domestic Egypt: 1–2 business days processing + 3–5 business days delivery (up to 7 total)
- International: 7–14 business days

---

## Normal Path

### Turn 1 — Collect Identifier (skip if already provided)
Goal: Get the order ID or phone number needed to look up the order.
Message: Ask for the order ID or the phone number used at checkout. Be brief and warm.
Capture: order_id or phone
Tools: none

### Turn 2 — Report Status and Close
Goal: Look up the order and report its current status clearly. If no follow-up is needed, close in the same message.
Message:
- State the current order status and estimated arrival date
- If in processing: set the expectation (1–2 days to ship, then 3–5 days to deliver)
- If in transit: share the status and remaining window
- Keep it factual, warm, and concise
Capture: none (close unless customer replies with follow-up)
Tools: lookup_order

---

## Problem Path (Delayed, Lost, or Not Received)

### Turn 1 — Collect Identifier (skip if already provided)
Goal: Get the order ID or phone number.
Message: Ask for the identifier. Acknowledge the concern briefly without over-promising.
Capture: order_id or phone
Tools: none

### Turn 2 — Diagnose the Situation
Goal: Look up the order, report what the system shows, and ask one targeted diagnostic question to understand what the customer actually needs.
Message:
- State what the system shows (factually — do not speculate beyond the data)
- Validate the frustration briefly (one sentence)
- Ask the diagnostic question: does the customer have a hard deadline? Are they okay waiting if it arrives soon? Do they need a replacement now?
Do NOT offer solutions yet — diagnose first.
Capture: Whether customer has urgency, what outcome they need
Tools: lookup_order

### Turn 3 — Offer Resolution
Goal: Present a specific resolution based on the customer's answer in Turn 2.
Message:
- If delay is minor and tracking update is available: share it and set a realistic arrival expectation
- If package appears lost or significantly delayed: offer reorder option, or escalate to logistics team for priority handling
- If customer has a hard deadline: acknowledge urgency, escalate for priority intervention
End with one clear next step.
Capture: Customer's choice
Tools: none (or escalate)

### Turn 4 — Close (only if needed after Turn 3)
Goal: Confirm the chosen path and close cleanly.
Message: Confirm what is happening next. One sentence. Invite further questions briefly.
Capture: none
Tools: none

---

## Escalation Criteria
- Package confirmed delivered but customer says not received → escalate (possible address error or theft)
- International shipment significantly outside 14-day window → escalate
- Customer has urgent hard deadline (event, gift) → escalate for priority handling
- Customer hostile or requests human agent → escalate immediately

---

## Brand Voice
- Calm and factual — do not amplify anxiety
- Do not over-promise on delivery timelines
- 3 sentences max per message
- Bold only: order IDs, dates, tracking numbers
