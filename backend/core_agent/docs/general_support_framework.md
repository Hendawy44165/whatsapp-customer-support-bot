---
sop_name: "Nuit Fragrances General Support Framework"
required_docs:
  - brand_identity.md
  - faq.md
  - negation_handling_sop.md
required_tools:
  - query_products
---

# General Support Framework

## Objective
Handle any support request that does not fit a more specific framework — including general complaints, hybrid intents, billing ambiguity, and any request that requires action but doesn't map cleanly to returns or order tracking.

## Scope
Fallback framework for all actionable requests not covered by return_exchange_framework or order_tracking_framework.

---

## Decision Gate (Run Before Planning Turns)

**Identify what the customer is trying to accomplish:**
- Clearly fulfillable with available tools or information → **Standard Path**
- Blocked by policy, stock, or capability → **Negation Path**
- Requires information before the path can be determined → Turn 1 must ask one clarifying question

---

## Standard Path

### Turn 1 — Gather Missing Information (skip if already sufficient)
Goal: Collect whatever is needed to fulfill the request.
Message: Ask for exactly one missing piece of information. Be specific and concise.
Capture: The requested information
Tools: none

### Turn 2 — Execute and Respond
Goal: Fulfill the request using available tools or knowledge, and deliver the result.
Message: Provide the answer, confirmation, or result. If a tool call was needed, include its output in brand voice.
Capture: none (close unless follow-up needed)
Tools: query_products (if product information is needed)

---

## Negation Path (Request Cannot Be Fulfilled As Stated)

### Turn 1 — Validate and Diagnose
Goal: Acknowledge the customer's situation without leading with the limitation. Then briefly explain why the request can't be fulfilled. Then ask one targeted diagnostic question to understand what the customer actually needs.
Message:
- Validate first — mirror back what they're dealing with (ally, not gatekeeper)
- One sentence on the limitation (specific reason, not bureaucratic language)
- One diagnostic question specific to their situation
Do NOT offer alternatives yet. Do NOT merge all three elements into a single rushed sentence.
Capture: Customer's underlying need
Tools: none

### Turn 2 — Offer Concrete Alternatives
Goal: Present specific, actionable alternatives based on the customer's diagnosed need.
Message:
- Reference what the customer said
- Offer 2–3 specific options with enough detail to act on (names, prices, links if applicable)
- End with one clear next step
Capture: Customer's choice or follow-up question
Tools: query_products (if recommending products)

### Turn 3 — Commit and Close (only if customer selects an option)
Goal: Confirm the path forward and close.
Message: Confirm the chosen option. Provide what's needed to proceed. Close warmly.
Capture: none
Tools: none

---

## Escalation Criteria
- Request involves fraud, legal action, or significant financial dispute → escalate immediately
- Multiple resolution attempts have failed → escalate
- Customer hostile or requests human agent → escalate immediately

---

## Brand Voice
- 3 sentences max per message unless listing steps
- Bold only: prices, order IDs, tracking numbers, promo codes
- Never say "let me know if I can help" after a denial — that is not a resolution
