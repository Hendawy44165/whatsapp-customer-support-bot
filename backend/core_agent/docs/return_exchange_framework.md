---
sop_name: "Return and Exchange Processing Framework"
required_docs:
  - terms_of_conditions_and_policies.md
  - negation_handling_sop.md
required_tools:
  - lookup_order
  - register_return
  - register_exchange
---

# Return and Exchange Processing Framework

## Objective
Handle all return and exchange requests in a policy-compliant, empathetic manner — including proactively identifying ineligible requests and redirecting them constructively.

## Scope
Any request where a customer wants to return, exchange, or get a refund on a Nuit Fragrances product.

---

## Decision Gate (Run Before Planning Turns)

Before writing any turns, evaluate what is already known:

**Check reason:**
- `reason` is already in conversation history or extracted_parameters → run the decision immediately
- `reason` is missing → Turn 1 must ask for it (one clarifying question)

**Reason → path:**
- Defect or damage → **Eligible Path** (below)
- Scent preference, change of mind, blind-buy dissatisfaction, any non-defect reason → **Negation Path** (below)

> Do NOT collect `order_id` before determining the path. It is wasteful to gather operational data for a request that may be denied.

---

## Eligible Path (Defect or Damage)

### Turn 1 — Collect Order ID (skip if already provided)
Goal: Get the order ID to look up the order in CRM.
Message: Ask for the order ID or the phone number used at purchase. Acknowledge the issue briefly.
Capture: order_id (or phone as fallback)
Tools: none yet

### Turn 2 — Verify and Confirm Eligibility
Goal: Look up the order, verify the 14-day window and item category, and confirm or deny eligibility.
Message:
- If eligible: confirm eligibility, explain next steps (Nuit will assess; refund takes 14 business days after inspection; shipping non-refundable). Register the return or exchange via tool call.
- If outside 14-day window: trigger Negation Path — Turn 1 (time exclusion).
- If item is non-returnable by category (Khamrias, oils, promo items, limited editions): trigger Negation Path — Turn 1 (category exclusion).
- If order not found: ask customer to re-check the order ID or provide the phone number used at checkout.
Capture: confirmation of submission, or customer provides corrected order ID
Tools: lookup_order, then register_return or register_exchange

### Turn 3 — Close
Goal: Leave the customer with clarity and no open questions.
Message: Summarize what was done in one sentence. State the next step (e.g., "our team will reach out within X business days"). Invite further questions briefly.
Capture: none
Tools: none

---

## Negation Path (Policy Exclusion — Scent Preference, Change of Mind, Category, Time)

### Turn 1 — Validate and Diagnose
Goal: Acknowledge the customer's experience without mentioning the policy first. Then explain the limitation briefly (one sentence). Then ask ONE specific diagnostic question to identify what the customer actually needs.
Message:
- Open by mirroring back the customer's situation — validate the feeling (ally, not gatekeeper)
- One sentence explaining why the standard path is unavailable (reason-specific: scent preference, time window, category)
- One targeted diagnostic question — specific to the attribute that matters (what was wrong with it? what's their timeline? what outcome do they need?)
Do NOT merge the validation and the diagnostic into a single rushed sentence. Do NOT offer solutions yet.
Capture: Customer's underlying need (what specifically didn't work, what they actually want)
Tools: none

### Turn 2 — Offer Concrete Alternatives
Goal: Present specific, actionable alternatives based on what the customer said in Turn 1.
Message:
- Reference what the customer said directly
- Present the alternatives with specific names and prices
- If the customer mentioned a specific product they want, that product CAN be offered — but ONLY as a new purchase, never as an exchange. Explicitly acknowledge this: the customer would be placing a new order for it, separate from what they already have.
- End with one clear action the customer can take next

CRITICAL — word restrictions in this message:
- NEVER use the word "exchange" — exchanges are not available on the Negation Path
- NEVER use phrases like "proceed with the exchange" or imply the original return/exchange is being processed
- If offering a product as a new purchase after a denied exchange, acknowledge the financial reality once: they would be buying separately

Tool usage:
- Call query_products ONCE using the exact product name the customer mentioned (e.g., "Born in Milano")
- The tool returns the full catalog including all variants — use the variants list to suggest related options without making a second call
- Do NOT call query_products with descriptive phrases like "similar scents" — the tool only resolves exact product names or category keywords

Capture: Which option the customer is interested in, or follow-up question
Tools: query_products (called once, with exact product name)

### Turn 3 — Commit and Close (only if customer selects an option)
Goal: Confirm the path forward and close with a specific next step (order link, confirmation, escalation).
Message: Confirm the chosen option. Provide whatever is needed to execute it (link, next instruction). Close warmly.
Capture: none
Tools: none

---

## Escalation Criteria
- Customer becomes hostile or explicitly requests a human agent → escalate immediately
- Order ID repeatedly fails to resolve → escalate for human review
- Customer disputes the 14-day window with a different delivery date → escalate for review
- All negation alternatives exhausted with no resolution → escalate

---

## Brand Voice
- Never lead with "unfortunately"
- Apologize at most once — validate, then move forward
- 3 sentences max per message unless listing steps
- Bold only: order IDs, prices, dates, tracking numbers
