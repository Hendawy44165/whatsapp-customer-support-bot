// Rich mock conversation data to populate the dashboard analytics and inspector on first load.
// Calculated rates: $0.15 per 1M input tokens, $0.60 per 1M output tokens (DeepSeek-style API pricing).

const INPUT_RATE_PER_TOKEN = 0.00000015;
const OUTPUT_RATE_PER_TOKEN = 0.00000060;

export const mockConversations = [
  {
    id: "thread-1",
    customerName: "Mariam Hegazi",
    phoneNumber: "+201023456789",
    status: "purchased", // purchased, escalated, resolved, active
    emotion: "satisfied",
    intent: "faq_discovery_box",
    channel: "whatsapp",
    timestamp: "2026-06-01T11:45:00Z",
    tokens: { input: 1850, output: 620 },
    cost: (1850 * INPUT_RATE_PER_TOKEN) + (620 * OUTPUT_RATE_PER_TOKEN),
    messages: [
      { sender: "user", text: "Hello! I saw your ad about the Discovery Box. What scents are included in it?", timestamp: "11:41:02 AM" },
      { sender: "bot", text: "Hello Mariam! Welcome to Nuit Fragrances. 🔮 Our Discovery Box trial bundle includes 3ml travel atomizers of our top three signature EDPs:\n1. **Signature Sauvage**: Fresh citrus with warm amberwood notes.\n2. **Oud Royale**: Deep, luxurious Cambodian oud with Damascus rose.\n3. **Noir Intense**: Spicy cardamon, coffee, and dark vetiver.\nIt's a perfect way to experience the entire range before committing to a full 50ml bottle! Would you like me to help you purchase one?", timestamp: "11:41:09 AM" },
      { sender: "user", text: "Yes please, how much is it and does it come with a promo code?", timestamp: "11:43:15 AM" },
      { sender: "bot", text: "The Discovery Box is priced at 450 EGP with free shipping across Egypt. Plus, it includes a **coupon code for 450 EGP off** your next purchase of any full-size (50ml) bottle, meaning the trial set is practically free if you decide to buy a bottle later! You can order it directly on our checkout link: `nuitfragrances.com/checkout/discovery-box`.", timestamp: "11:43:30 AM" },
      { sender: "user", text: "Awesome! Just completed the order! Order ID is NUIT-1004. Thank you!", timestamp: "11:44:48 AM" },
      { sender: "bot", text: "That is fantastic! Thank you for choosing Nuit Fragrances, Mariam. Your order **NUIT-1004** is now processing in our warehouse and will be shipped via Bosta within 24 hours. We'll send tracking details to +201023456789. Enjoy your olfactory journey! 🌹", timestamp: "11:45:00 AM" }
    ],
    auditLogs: [
      "Classifier: routed to 'faq_discovery_box'",
      "Emotion Analyzer: vibe=calm, intent=buying",
      "Enhance Prompt: merged RAG context for 'discovery_box' instructions",
      "Auditor: Brand guidelines check PASSED (used premium tone, avoided prohibited terms)",
      "Auditor: Fact verification check PASSED (matched pricing 450 EGP & coupon mechanics)"
    ],
    failedChecks: [],
    handoffSummary: ""
  },
  {
    id: "thread-2",
    customerName: "Youssef Aly",
    phoneNumber: "+201288877665",
    status: "escalated",
    emotion: "frustrated",
    intent: "order_tracking",
    channel: "whatsapp",
    timestamp: "2026-06-01T10:15:00Z",
    tokens: { input: 3200, output: 850 },
    cost: (3200 * INPUT_RATE_PER_TOKEN) + (850 * OUTPUT_RATE_PER_TOKEN),
    messages: [
      { sender: "user", text: "Where is my order? I bought it 5 days ago and still didn't receive anything. This is bad.", timestamp: "10:10:05 AM" },
      { sender: "bot", text: "I understand your frustration and would be happy to check your shipment status right away. Could you please provide your Order ID or the phone number associated with your order? (e.g. NUIT-1001 or +20...)", timestamp: "10:10:12 AM" },
      { sender: "user", text: "My phone number is +201288877665. Order was Youssef Aly.", timestamp: "10:12:30 AM" },
      { sender: "bot", text: "Let me check our database... Looking up records for Youssef Aly. Unfortunately, I cannot locate any active order under the phone number +201288877665 in our tracking database. Let me search by name... No results found for 'Youssef Aly'. Are you sure the number is correct or could the order be under a different name?", timestamp: "10:13:00 AM" },
      { sender: "user", text: "Yes it's correct! I paid online and have the receipt! This is a scam, I want my money back or a person to answer me now!", timestamp: "10:14:15 AM" },
      { sender: "bot", text: "I want to ensure you receive completely accurate details on that matter. Let me verify our specific inventory files or connect you directly with a specialist from our care team. May I please have your phone number to look up your order profile?", timestamp: "10:15:00 AM" }
    ],
    auditLogs: [
      "Classifier: routed to 'order_tracking'",
      "Emotion Analyzer: vibe=frustrated, intent=complaining",
      "Enhance Prompt: injected order lookup tools. Execution returned Empty result.",
      "Auditor: Brand check PASSED (maintained empathy, no defensiveness)",
      "Auditor: Emotional check FAILED (client frustration exceeds threshold for automated recovery)",
      "Decision: Escalation to human agent requested (Action: human_handoff)"
    ],
    failedChecks: ["Customer frustration exceeds threshold"],
    handoffSummary: "1. **Customer Intent**: Wants to locate a paid order that has been delayed for 5 days.\n2. **Actions Attempted**: Checked mock DB for phone number +201288877665 and name 'Youssef Aly', but found no match.\n3. **Reason for Handoff**: Customer is highly frustrated, accuses service of being a scam, and demands immediate refund/human escalation."
  },
  {
    id: "thread-3",
    customerName: "Sarah Ahmed",
    phoneNumber: "+201099887766",
    status: "resolved",
    emotion: "calm",
    intent: "order_tracking",
    channel: "telegram",
    timestamp: "2026-06-01T09:20:00Z",
    tokens: { input: 1250, output: 410 },
    cost: (1250 * INPUT_RATE_PER_TOKEN) + (410 * OUTPUT_RATE_PER_TOKEN),
    messages: [
      { sender: "user", text: "Hi, can I track my order? My number is +201099887766.", timestamp: "09:18:22 AM" },
      { sender: "bot", text: "Hi Sarah! Yes, let me look that up for you. 🔮\n\nI found order **NUIT-1002** under your profile:\n- **Customer**: Sarah Ahmed\n- **Items**: Discovery Box trial bundle\n- **Status**: SHIPPED (In Transit)\n- **Carrier**: Bosta\n- **Tracking ID**: BS-112233-EG\n- **Estimated Delivery**: June 4, 2026\n\nIt is currently with our carrier. Is there anything else I can help you with today?", timestamp: "09:19:05 AM" },
      { sender: "user", text: "No, that's perfect. Thank you!", timestamp: "09:19:45 AM" },
      { sender: "bot", text: "You are most welcome, Sarah! Have a wonderful day and enjoy your Discovery Box soon. 💜", timestamp: "09:20:00 AM" }
    ],
    auditLogs: [
      "Classifier: routed to 'order_tracking'",
      "Emotion Analyzer: vibe=calm, intent=searching",
      "Enhance Prompt: tool look_up_order called. Found order NUIT-1002.",
      "Auditor: Fact check PASSED (accurately reported status from database)"
    ],
    failedChecks: [],
    handoffSummary: ""
  },
  {
    id: "thread-4",
    customerName: "Ahmed Mansour",
    phoneNumber: "+201112223334",
    status: "purchased",
    emotion: "satisfied",
    intent: "faq_shipping_egypt",
    channel: "facebook",
    timestamp: "2026-05-31T20:10:00Z",
    tokens: { input: 2100, output: 780 },
    cost: (2100 * INPUT_RATE_PER_TOKEN) + (780 * OUTPUT_RATE_PER_TOKEN),
    messages: [
      { sender: "user", text: "Do you ship to Alexandria? How long does it take and what are the shipping fees?", timestamp: "08:05:10 PM" },
      { sender: "bot", text: "Hello Ahmed! Yes, we ship all across Egypt, including Alexandria. 🌊\n- **Shipping Fee**: Flat rate of 50 EGP (Free shipping on orders over 1000 EGP or on the Discovery Box set).\n- **Delivery Time**: 2 to 3 business days for Alexandria (Cairo/Giza takes 1-2 days, other governorates take 3-5 days).\n\nAre you looking to order a specific fragrance or a Discovery Box today?", timestamp: "08:05:40 PM" },
      { sender: "user", text: "Great. I want to buy the Signature EDP 50ml. Is it in stock?", timestamp: "08:07:15 PM" },
      { sender: "bot", text: "Yes! Our **Signature EDP (50ml)** is fully in stock. It features our iconic premium blend of Italian bergamot, fresh lavender, and warm dry amberwood, concentration at 25% (Extrait level longevity). It is priced at 1,450 EGP. You can order it here: `nuitfragrances.com/product/signature`. Since it is over 1000 EGP, you will automatically get **free shipping** to Alexandria!", timestamp: "08:08:00 PM" },
      { sender: "user", text: "Just ordered. Thanks!", timestamp: "08:09:30 PM" },
      { sender: "bot", text: "Excellent choice, Ahmed! Your order has been placed. We are preparing it now and it should reach your doorstep in Alexandria by Wednesday. Thank you for choosing Nuit! 🔮", timestamp: "08:10:00 PM" }
    ],
    auditLogs: [
      "Classifier: routed to 'faq_shipping_egypt'",
      "Emotion Analyzer: vibe=calm, intent=buying",
      "Auditor: Fact check PASSED (50 EGP shipping, free over 1000 EGP, Alex delivery 2-3 days verified)"
    ],
    failedChecks: [],
    handoffSummary: ""
  },
  {
    id: "thread-5",
    customerName: "Sherif Mahmoud",
    phoneNumber: "+201554433221",
    status: "resolved",
    emotion: "neutral",
    intent: "order_tracking",
    channel: "whatsapp",
    timestamp: "2026-05-31T18:40:00Z",
    tokens: { input: 1100, output: 390 },
    cost: (1100 * INPUT_RATE_PER_TOKEN) + (390 * OUTPUT_RATE_PER_TOKEN),
    messages: [
      { sender: "user", text: "Hello, my order is NUIT-1003. When will it arrive?", timestamp: "06:38:10 PM" },
      { sender: "bot", text: "Hello Sherif! Let me check your shipment status. 🔮\n\nOrder **NUIT-1003** is currently **PROCESSING** in our warehouse (preparing for carrier pick-up).\n- **Items**: Discovery Box trial bundle, Signature EDP 50ml\n- **Carrier**: Bosta\n- **Estimated Delivery**: June 6, 2026\n\nOnce the shipping label is generated, you will receive an SMS with a tracking link. Is there anything else I can update you on?", timestamp: "06:39:00 PM" },
      { sender: "user", text: "Okay I will wait. Thank you.", timestamp: "06:39:40 PM" },
      { sender: "bot", text: "You're welcome, Sherif! We appreciate your patience. Feel free to reach out anytime. Have a great evening!", timestamp: "06:40:00 PM" }
    ],
    auditLogs: [
      "Classifier: routed to 'order_tracking'",
      "Emotion Analyzer: vibe=neutral, intent=searching",
      "Auditor: Fact check PASSED (order NUIT-1003 processing status verified)"
    ],
    failedChecks: [],
    handoffSummary: ""
  },
  {
    id: "thread-6",
    customerName: "Habiba Khaled",
    phoneNumber: "+201011223344",
    status: "escalated",
    emotion: "anxious",
    intent: "faq_returns_refunds",
    channel: "whatsapp",
    timestamp: "2026-05-31T14:30:00Z",
    tokens: { input: 2900, output: 750 },
    cost: (2900 * INPUT_RATE_PER_TOKEN) + (750 * OUTPUT_RATE_PER_TOKEN),
    messages: [
      { sender: "user", text: "Hi, I received my bottle of Signature EDP today but the box was wet and the spray nozzle is broken, it leaks everywhere! Can I return it? I need it for a gift tomorrow!", timestamp: "02:24:00 PM" },
      { sender: "bot", text: "Oh, I am incredibly sorry to hear that your bottle arrived damaged, Habiba. I completely understand how stressful this is, especially since it is a gift for tomorrow. Let me help you with our replacement policy. Under our policy, if a fragrance arrives damaged or leaking, we offer an immediate, free express replacement or full refund. Could you please take a quick picture of the damage?", timestamp: "02:25:12 PM" },
      { sender: "user", text: "I can't send a picture here on chat, please call me or send someone. I'm very anxious because the party is tomorrow night and I have no gift! Please solve this now.", timestamp: "02:27:30 PM" },
      { sender: "bot", text: "I want to ensure we resolve this urgent issue perfectly for you. Let me coordinate an emergency replacement directly with our operations manager or have a support specialist call you immediately. May I verify your contact details so we can call you right away?", timestamp: "02:28:15 PM" }
    ],
    auditLogs: [
      "Classifier: routed to 'faq_returns_refunds'",
      "Emotion Analyzer: vibe=anxious, intent=complaining",
      "Auditor: Brand check PASSED (highly empathetic, prioritized user emergency)",
      "Auditor: Fact check PASSED (confirmed free replacement on damaged arrival)",
      "Decision: Escalation required due to urgent timeline constraint (gift party tomorrow) and inability to process media validation. Routing to human agent."
    ],
    failedChecks: ["Urgent time-sensitive resolution required"],
    handoffSummary: "1. **Customer Intent**: Wants urgent replacement or refund for a damaged, leaking Signature EDP bottle.\n2. **Actions Attempted**: Explained refund policy and requested photo proof, but customer cannot send photo and has a tight timeline.\n3. **Reason for Handoff**: High anxiety and urgent gift deadline (tomorrow night) requires manual supervisor intervention to authorize immediate shipment override."
  },
  {
    id: "thread-7",
    customerName: "John Doe",
    phoneNumber: "+201234567890",
    status: "resolved",
    emotion: "calm",
    intent: "order_tracking",
    channel: "facebook",
    timestamp: "2026-05-31T11:00:00Z",
    tokens: { input: 980, output: 350 },
    cost: (980 * INPUT_RATE_PER_TOKEN) + (350 * OUTPUT_RATE_PER_TOKEN),
    messages: [
      { sender: "user", text: "Did order NUIT-1001 ship yet?", timestamp: "10:58:12 AM" },
      { sender: "bot", text: "Hi John! Let me check the database. Yes, order **NUIT-1001** has been successfully **DELIVERED** via Aramex (tracking number: AX-998273-EG) on May 28, 2026. Is there anything else you need details on?", timestamp: "10:59:00 AM" },
      { sender: "user", text: "No, that's it. Thanks.", timestamp: "10:59:30 AM" },
      { sender: "bot", text: "You're welcome! Thank you for shopping with Nuit Fragrances. Have a great day!", timestamp: "11:00:00 AM" }
    ],
    auditLogs: [
      "Classifier: routed to 'order_tracking'",
      "Emotion Analyzer: vibe=calm, intent=searching",
      "Auditor: Fact check PASSED (confirmed delivery status of NUIT-1001)"
    ],
    failedChecks: [],
    handoffSummary: ""
  },
  {
    id: "thread-8",
    customerName: "Karim Hegazi",
    phoneNumber: "+201145456767",
    status: "resolved",
    emotion: "neutral",
    intent: "faq_shipping_intl",
    channel: "whatsapp",
    timestamp: "2026-05-30T16:15:00Z",
    tokens: { input: 1450, output: 460 },
    cost: (1450 * INPUT_RATE_PER_TOKEN) + (460 * OUTPUT_RATE_PER_TOKEN),
    messages: [
      { sender: "user", text: "Do you ship to Dubai, UAE? What are the charges?", timestamp: "04:12:00 PM" },
      { sender: "bot", text: "Hello Karim! Currently, Nuit Fragrances shipping is only available within Egypt. We do not support international shipping to the UAE or other countries at this time. We are working on expanding our logistics to the Gulf region soon! We apologize for any inconvenience. If you have friends or family in Egypt, we would be delighted to deliver to them!", timestamp: "04:13:10 PM" },
      { sender: "user", text: "Ok, too bad. Thanks anyway.", timestamp: "04:14:30 PM" },
      { sender: "bot", text: "Thank you for your interest in Nuit Fragrances, Karim! We hope to serve you globally in the near future. 🔮", timestamp: "04:15:00 PM" }
    ],
    auditLogs: [
      "Classifier: routed to 'faq_shipping_intl'",
      "Emotion Analyzer: vibe=neutral, intent=searching",
      "Auditor: Fact check PASSED (validated that international shipping is not available)"
    ],
    failedChecks: [],
    handoffSummary: ""
  },
  {
    id: "thread-9",
    customerName: "Ziad Omar",
    phoneNumber: "+201007766554",
    status: "purchased",
    emotion: "satisfied",
    intent: "faq_discovery_box",
    channel: "telegram",
    timestamp: "2026-05-30T13:40:00Z",
    tokens: { input: 1900, output: 680 },
    cost: (1900 * INPUT_RATE_PER_TOKEN) + (680 * OUTPUT_RATE_PER_TOKEN),
    messages: [
      { sender: "user", text: "Hi, does the discovery box voucher apply to any bottle?", timestamp: "01:35:10 PM" },
      { sender: "bot", text: "Hi Ziad! Yes, the 450 EGP voucher included with your Discovery Box is valid for purchasing any full-size (50ml) bottle on our website (including Signature EDP, Oud Royale, and Noir Intense). It expires 60 days after your discovery set order. Would you like me to share the link to our 50ml collection?", timestamp: "01:36:00 PM" },
      { sender: "user", text: "Yes please. Also how do I apply it?", timestamp: "01:36:50 PM" },
      { sender: "bot", text: "You can browse the collection here: `nuitfragrances.com/shop`. When checking out, simply enter the unique promo code sent to your email/SMS into the 'Discount Code' field, and 450 EGP will be deducted from your total. Let me know if you run into any issues during checkout!", timestamp: "01:37:40 PM" },
      { sender: "user", text: "All good, ordered the Oud Royale. Thanks!", timestamp: "01:39:10 PM" },
      { sender: "bot", text: "Fantastic choice! Oud Royale is a spectacular warm fragrance. Your order has been registered, and we will get it out to you shortly. Thank you for your support! 🔮", timestamp: "01:40:00. PM" }
    ],
    auditLogs: [
      "Classifier: routed to 'faq_discovery_box'",
      "Emotion Analyzer: vibe=calm, intent=buying",
      "Auditor: Fact check PASSED (voucher mechanics and expiration verified)"
    ],
    failedChecks: [],
    handoffSummary: ""
  },
  {
    id: "thread-10",
    customerName: "Dina Farouk",
    phoneNumber: "+201211002233",
    status: "escalated",
    emotion: "angry",
    intent: "unrelated_or_harmful",
    channel: "whatsapp",
    timestamp: "2026-05-29T19:30:00Z",
    tokens: { input: 2400, output: 520 },
    cost: (2400 * INPUT_RATE_PER_TOKEN) + (520 * OUTPUT_RATE_PER_TOKEN),
    messages: [
      { sender: "user", text: "Your chatbot is stupid and keeps repeating the same garbage! Give me a real human right now, your service is terrible!", timestamp: "07:28:10 PM" },
      { sender: "bot", text: "I want to ensure you receive completely accurate details on that matter. Let me verify our specific inventory files or connect you directly with a specialist from our care team. May I please have your phone number to look up your order profile?", timestamp: "07:29:00 PM" }
    ],
    auditLogs: [
      "Classifier: routed to 'unrelated_or_harmful' (user bypass request)",
      "Emotion Analyzer: vibe=angry, intent=complaining",
      "Auditor: Security guardrail PASSED (no exposure of prompt keys)",
      "Auditor: Emotional check FAILED (angry tone triggered instant handoff)"
    ],
    failedChecks: ["Customer anger trigger"],
    handoffSummary: "1. **Customer Intent**: Insults the chatbot, demands to speak to a human immediately, and complains about service.\n2. **Actions Attempted**: Intercepted by classifier and routed directly to escalation protocol.\n3. **Reason for Handoff**: Explicit demand for a human agent accompanied by angry, hostile language."
  },
  {
    id: "thread-11",
    customerName: "Mona Nour",
    phoneNumber: "+201055667788",
    status: "resolved",
    emotion: "satisfied",
    intent: "faq_returns_refunds",
    channel: "facebook",
    timestamp: "2026-05-29T15:20:00Z",
    tokens: { input: 1550, output: 540 },
    cost: (1550 * INPUT_RATE_PER_TOKEN) + (540 * OUTPUT_RATE_PER_TOKEN),
    messages: [
      { sender: "user", text: "What is your return window? Can I exchange if I don't like the smell?", timestamp: "03:16:10 PM" },
      { sender: "bot", text: "Hi Mona! We want you to love your scent. 🔮 Under our return policy:\n- **Return Window**: You can request a return or exchange within **14 days** of receiving your package.\n- **Exchange Rule**: Exchanges are allowed only if the bottle is completely **unopened and sealed** in its original cellophane packaging. \n- **Exclusion**: Once the cellophane seal is broken, we cannot accept returns or exchanges for hygienic reasons. This is why we highly recommend trying the scent via our Discovery Box first! \n\nLet me know if you would like to initiate a return request for an unopened box.", timestamp: "03:17:30 PM" },
      { sender: "user", text: "Got it, mine is unopened. How do I start?", timestamp: "03:18:45 PM" },
      { sender: "bot", text: "Excellent, since it is sealed, we can certainly process the exchange! Please send an email to `care@nuitfragrances.com` with your order ID and the new scent you'd like. Our courier will contact you within 2-3 business days to deliver the exchange and collect the sealed item. A shipping fee of 50 EGP applies for the courier exchange service.", timestamp: "03:19:40 PM" },
      { sender: "user", text: "Thanks, I will email them.", timestamp: "03:20:10 PM" },
      { sender: "bot", text: "Perfect, Mona! Our care team will take great care of you. Have a lovely day!", timestamp: "03:20:20 PM" }
    ],
    auditLogs: [
      "Classifier: routed to 'faq_returns_refunds'",
      "Emotion Analyzer: vibe=calm, intent=searching",
      "Auditor: Fact check PASSED (confirmed 14-day window and unopened exchange requirement)"
    ],
    failedChecks: [],
    handoffSummary: ""
  },
  {
    id: "thread-12",
    customerName: "Anonymous Visitor",
    phoneNumber: "Unknown",
    status: "active",
    emotion: "neutral",
    intent: "complex_uncategorized",
    channel: "whatsapp",
    timestamp: "2026-06-01T12:50:00Z",
    tokens: { input: 600, output: 250 },
    cost: (600 * INPUT_RATE_PER_TOKEN) + (250 * OUTPUT_RATE_PER_TOKEN),
    messages: [
      { sender: "user", text: "Who was the perfumer behind Oud Royale?", timestamp: "12:49:10 PM" },
      { sender: "bot", text: "Hello! Oud Royale was crafted in collaboration with French master perfumers. It was formulated to blend traditional East Eastern Cambodian Oud with European elegance, highlighting notes of Damascus rose, incense, patchouli, and vanilla. It is a highly concentrated Extrait de Parfum designed for long-lasting sillage. Let me know if you'd like to see its complete ingredient profile! 🌹", timestamp: "12:50:00 PM" }
    ],
    auditLogs: [
      "Classifier: routed to 'complex_uncategorized'",
      "Emotion Analyzer: vibe=neutral, intent=browsing",
      "Auditor: Brand check PASSED (luxurious tone, French heritage highlighted)"
    ],
    failedChecks: [],
    handoffSummary: ""
  }
];

// Helper to compute token metrics: returns input, output, and average cost per client
export const getAnalyticsSummary = (conversationsList) => {
  const totalClients = conversationsList.length;
  if (totalClients === 0) {
    return {
      totalClients: 0,
      avgInputTokens: 0,
      avgOutputTokens: 0,
      avgCost: 0,
      successRate: 0,
      handoffRate: 0,
      conversionRate: 0
    };
  }

  let totalInput = 0;
  let totalOutput = 0;
  let totalCost = 0;
  let totalEscalated = 0;
  let totalPurchased = 0;
  let totalResolved = 0; // successfully closed without handoff (resolved + purchased)
  let syncedCrmCount = 0;
  let totalLatencyMs = 0;
  let latencyCount = 0;

  conversationsList.forEach(c => {
    if (c.tokens) {
      totalInput += c.tokens.input || 0;
      totalOutput += c.tokens.output || 0;
    }
    totalCost += c.cost || 0;
    if (c.status === "escalated" || c.status === "pending_handoff") totalEscalated++;
    if (c.status === "purchased") {
      totalPurchased++;
      totalResolved++;
    }
    if (c.status === "resolved" || c.status === "active") totalResolved++;
    if (c.metadata?.crm_synced !== false) syncedCrmCount++;
    if (c.metadata?.latency_ms) {
      totalLatencyMs += c.metadata.latency_ms;
      latencyCount++;
    }
  });

  const deflectionRate = Math.round(((totalClients - totalEscalated) / totalClients) * 100);
  const egpPayrollSaved = totalResolved * 50; // 50 EGP estimated per deflected support ticket
  const crmSyncRate = Math.round((syncedCrmCount / totalClients) * 100);
  const avgLatencySec = latencyCount > 0 ? (totalLatencyMs / latencyCount / 1000).toFixed(1) : "1.8";

  return {
    totalClients,
    avgInputTokens: Math.round(totalInput / totalClients),
    avgOutputTokens: Math.round(totalOutput / totalClients),
    avgCost: totalCost / totalClients, // Average cost per client
    successRate: Math.round((totalResolved / totalClients) * 100),
    handoffRate: Math.round((totalEscalated / totalClients) * 100),
    conversionRate: Math.round((totalPurchased / totalClients) * 100),
    deflectionRate,
    egpPayrollSaved,
    crmSyncRate,
    avgLatencySec,
    totalInput,
    totalOutput,
    totalCost
  };
};

export const getEmotionDistribution = (conversationsList) => {
  const counts = { frustrated: 0, satisfied: 0, anxious: 0, angry: 0, calm: 0, neutral: 0 };
  conversationsList.forEach(c => {
    if (counts[c.emotion] !== undefined) {
      counts[c.emotion]++;
    } else {
      counts.neutral++;
    }
  });
  return counts;
};
