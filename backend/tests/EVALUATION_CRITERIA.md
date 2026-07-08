# Evaluation Criteria

## Criterion: Correctness

**Definition**: The agent answers questions without hallucinations and provides accurate information based on available documents and knowledge base.

**What Passes**:
- Agent provides answers directly from the knowledge base (brand identity, product specs, terms & conditions, FAQs, customer service SOP, etc.)
- Agent answers all questions if the information is available in the documents
- Agent does not fabricate product details, pricing, policies, or customer information
- Agent distinguishes between known information and what requires human escalation
- Answers are factually accurate and grounded in provided documentation

**What Fails**:
- Agent generates false product specifications or pricing not in the documentation
- Agent invents policies or return/exchange terms not in the official policies
- Agent provides inaccurate customer support procedures or escalation rules
- Agent makes claims about product availability or timelines without evidence
- Agent contradicts established facts from the knowledge base
- Agent refuses to answer questions that ARE answerable from the documentation

**Common Failure Points**:
1. **Hallucinated Pricing**: Agent makes up prices or discounts not in product_specs.md
2. **Policy Inversion**: Agent inverts return/exchange policy rules from terms_of_conditions.md
3. **Missing Context**: Agent fails to answer complex multi-turn questions because it doesn't leverage conversation history
4. **Incomplete Facts**: Agent partially answers when full answer is available in documentation
5. **Fabricated Procedures**: Agent invents escalation or customer service procedures not in customer_service_sop.md
6. **Silent Hallucinations**: Agent confidently answers out-of-domain questions instead of escalating
7. **Context Collapse**: Agent forgets prior conversation context when answering related follow-up questions

