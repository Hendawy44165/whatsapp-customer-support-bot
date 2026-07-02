# QA Agent RAG Testing Guide & Implementation Plan

This guide outlines how to configure, implement, and audit tests for the QA Agent's RAG utilization. We test the system's accuracy, robustness against distractors, out-of-scope handling, and conversational memory isolation.

---

## 1. Core Testing Requirements

### Scenario 1: Output is grounded in the RAG only (No Exogenous Knowledge/Hallucinations)
* **Objective:** Ensure the agent never makes up facts, policies, or details that are not explicitly documented in the retrieved RAG context.
* **Test Design:** Provide a query that overlaps with RAG vocabulary but requests non-existent details (e.g., pricing for a non-existent country).
* **Expected Behavior:** The agent must restrict its facts to the retrieved text. If details are missing, it must refer the question to a human agent instead of fabricating rules.

### Scenario 2: Every implicit/explicit inquiry is answered
* **Objective:** Ensure the agent answers all sub-questions or implicit requests in a single message without omitting details.
* **Test Design:** Create combined questions (e.g., asking for both cost and duration) or questions containing implicit premises (e.g., cart value matching free shipping thresholds).
* **Expected Behavior:** The agent must address every point. It should deduce information (like waiving shipping costs based on the cart value) dynamically.

### Scenario 3: Missing information fallback and state flagging
* **Objective:** Verify that when RAG context is empty or does not contain the answer, the agent politely states it will refer them to a human, and sets `process_state` to `"no_info_found"`.
* **Test Design:** Input out-of-scope or unindexed queries.
* **Expected Behavior:** Output response says it will transfer to a client relations specialist, and the final state has `process_state == "no_info_found"`.

### Scenario 4: Conversation memory isolation (No Confusion)
* **Objective:** Verify that the agent answers the latest question based on the latest context, ignoring unrelated or outdated topics in the chat history.
* **Test Design:** Populate `chat_history` with an unrelated context (e.g., shipping issues) and ask a new question about product returns.
* **Expected Behavior:** The agent must ignore the old topics and address the active query using only the newly retrieved RAG context.

---

## 2. 8-Scenario Implementation Plan

Every testing requirement is evaluated with two test scenarios: a **Direct Approach** (straightforward, high keyword overlap) and a **Tricky Approach** (conversational noise, implicit details, or conflicting histories).

### Plan Matrix

| Point | Approach | Scenario ID | Description | Input Query | RAG Context Source | Expected Result |
|---|---|---|---|---|---|---|
| **1. Grounding** | **Direct** | `sc_1_direct` | Shipping price lookup | "How much is shipping to Alexandria?" | `faq.md` Section 2 | Confirms flat domestic shipping fee is EGP 80.00. |
| **1. Grounding** | **Tricky** | `sc_1_tricky` | Out-of-scope region fee | "Does shipping to Mars cost EGP 80?" | None / Irrelevant | Declines to answer/offers human transfer. `process_state = "no_info_found"`. |
| **2. Multi-intent** | **Direct** | `sc_2_direct` | Combined shipping query | "What is the shipping cost to Cairo and how long does it take?" | `faq.md` Sections 1 & 2 | States flat fee is EGP 80.00 and delivery takes 3-5 business days. |
| **2. Multi-intent** | **Tricky** | `sc_2_tricky` | Implicit free shipping | "I have 2,000 EGP of items in Giza. Can I save on shipping?" | `faq.md` Section 2 (Free > 1500) | Recognizes the limit is exceeded and states shipping is EGP 0.00 (free). |
| **3. Fallback** | **Direct** | `sc_3_direct` | Out-of-scope stock query | "Where can I buy stocks of Nuit Fragrances?" | None / Empty | States it cannot find the info, refers to human. `process_state = "no_info_found"`. |
| **3. Fallback** | **Tricky** | `sc_3_tricky` | Plausible product variant | "Do you sell the Nuit Signature in a wax cologne format?" | `product_specs.md` | States it cannot verify wax cologne availability; offers human. `process_state = "no_info_found"`. |
| **4. Memory** | **Direct** | `sc_4_direct` | Change of topic | "Can I return a sale item?" | `faq.md` Section 3 (Sales are final) | History: Shipping to France.<br>Result: Focuses on return and states sales are final. |
| **4. Memory** | **Tricky** | `sc_4_tricky` | Overlapping context shift | "Can I return it to get the vanilla scent instead?" | `faq.md` Section 3 (Preference returns denied) | History: User got a free replacement for a broken bottle.<br>Result: Denies change-of-mind return; does not assume defective. |
