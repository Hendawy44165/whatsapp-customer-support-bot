# NUIT FRAGRANCES: FUNNEL CONVERSION MECHANICS, DATA ENDPOINTS & ADVERTISING COPY LEDGER
# Document Control ID: NUIT-KB-01D-2026 | Data Classification: Internal Context Asset

## 1. STRATEGIC TOP-OF-FUNNEL (TOFU) CONVERSION MECHANICS
* **The Sensory Digital Disconnect:** Because fine fragrance cannot be physically sampled through a digital screen or automated interface layer, high-end online customer acquisition requires a risk-mitigating gateway product.
* **Funnel Architecture Mandate:** The top-of-funnel conversion model uses an entry-level trial bundle. This bundle lowers the physical friction of buying a fragrance online, creates verified customer profiles, and establishes direct communication lines across Meta applications. These lines are later used to upsell clients to full-size bottles.

## 2. FUNNEL CAMPAIGN STRUCTURE: THE NUIT DISCOVERY EXPERIENCE
* **Standard Bundle Components:** Offers a curated selection of deluxe miniatures via the specialized Discovery Box lineup, enabling cross-comparison of top-tier scent adaptations.
* **Complete Offer Pricing Matrix:** Base MSRP structural value sits at EGP 525.00, with active standard introductory promotional campaigns setting the conversion cost to **EGP 368.00** flat (All taxes and processing costs inclusive).
* **Fulfillment & Shipping Terms:** Processed with completely **free domestic shipping** nationwide within the Arab Republic of Egypt when paired with active campaign push triggers. The standard domestic logistics fee of EGP 80.00 is systematically waived to optimize top-of-funnel conversion rates.

## 3. DIRECT PAYLOAD MAPPING TO CHATBOT AUTOMATION ENDPOINTS
The following data strings serve as entry codes, matching incoming client messages to automated system webhooks and inventory paths:
* **Entry Payload Code `NUIT_SHARK_DISCOVERY`:**
  * *System Action:* Triggers the automated fulfillment sequence confirming the activation of the EGP 368.00 Best Sellers Discovery Box Offering with campaign shipping incentives across Egypt.
  * *Inventory Allocation:* Reserves one (1) multi-variant sample box and creates a pending shipping label in the fulfillment queue.
* **Entry Payload Code `SIGNATURE_UPGRADE_300`:**
  * *System Action:* Triggers the checkout page generation for a full-size flagship 50ml bottle, automatically deducting the corresponding upgrade incentive or retention voucher from the base configuration.
  * *Financial Outcome:* Drops the core flagship product from its standard baseline down to its active campaign layer of exactly **EGP 599.00**.

## 4. MULTI-VARIANT CONVERSION COPY GRID (META ADS MANAGER INPUTS)
The following copy assets are mapped directly to your targeted audience segments for ad set management inside Meta Ads Manager:

### 4.1 Segment Alpha Copy Asset (Target: Corporate Nomad)
* **Creative Visual Direction Hook:** High-contrast minimalist photography focusing on the crisp frosted onyx glass bottle profile resting on a premium executive marble desk. No human figures present.
* **Primary Copy Asset:** "Command the boardroom without saying a single word. Formulated with high-concentration French oils imported from Grasse, **Nuit Fragrances** delivers an elite projection profile built to handle back-to-back corporate calls. Claim your risk-free travel sampling set today."

### 4.2 Segment Beta Copy Asset (Target: Creative Class)
* **Creative Visual Direction Hook:** Macro lens product photography emphasizing the metallic precision and industrial craftsmanship of the gold atomizer stamp. Clean geometric backgrounds.
* **Primary Copy Asset:** "True luxury isn't imported; it is built locally. Experience an uncompromising sensory statement with unique note profiles matching the world's most iconic luxury blends. Tap 'Send Message' to lock in your luxury discovery box."

### 4.3 Segment Gamma Copy Asset (Target: Digital Entrepreneur)
* **Creative Visual Direction Hook:** Clean split-screen digital rendering presenting the signature premium bottle packaging alongside the official *Shark Tank Egypt* logo accent. High visual energy.
* **Primary Copy Asset:** "As seen on Shark Tank Egypt. Stop overpaying for hyper-inflated imported designer labels and transition to the elite domestic perfume standard. Get deluxe miniatures sent directly to your door for just **EGP 368** with promotional zero shipping fees."

## 5. PROMOTIONAL GUARDRAILS & ARCHITECTURAL DISQUALIFICATIONS
* **Final Sale Designation:** Discovery configurations, sample box orders, individual 2ml/5ml miniatures, and custom sample selections are classified as final promotional sales. They are strictly non-refundable and non-exchangeable under any circumstances.
* **Anti-Stacking Architecture:** The e-commerce backend blocks voucher stacking. A checkout session can use only one (1) promotional code or discount voucher string at a time. Multiple discount vouchers cannot be applied to a single transaction.
