-- Create Experts Table
CREATE TABLE IF NOT EXISTS experts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'offline',
    current_load INTEGER DEFAULT 0,
    chat_redirect_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create Conversations Table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_phone TEXT NOT NULL,
    platform TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    assigned_expert_id UUID REFERENCES experts(id) ON DELETE SET NULL,
    cost_usd NUMERIC(10, 5) DEFAULT 0.00000,
    handoff_summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create Messages Table (Read-only historical view of social chat)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type TEXT NOT NULL, -- 'customer', 'agent', 'human'
    content TEXT NOT NULL,
    sentiment_data JSONB,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create Message Buffer / Queue Table
CREATE TABLE IF NOT EXISTS message_buffer (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- 'pending', 'sent', 'failed'
    scheduled_for TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create System Logs Table (for non-AI system events)
CREATE TABLE IF NOT EXISTS system_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name TEXT NOT NULL,
    log_level TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create Documents Table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL, -- 'faq', 'products', 'sop'
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create Settings Table
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create Carts Table (New)
CREATE TABLE IF NOT EXISTS carts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    product_name TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    price REAL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Seed a default expert for testing
INSERT INTO experts (id, name, email, status, current_load, chat_redirect_url) VALUES (
    'e791b8d2-28e4-4d8e-908d-e6b7c07b667e',
    'Mervat Support Expert',
    'mervat@nfragrances.com',
    'online',
    0,
    'https://wa.me/201234567890?text=Assigned+Chat+Redirection'
) ON CONFLICT DO NOTHING;

-- Seed initial settings
INSERT INTO settings (key, value) VALUES (
    'llm_config',
    '{"provider_model_name": "deepseek-chat", "temperature": 0.3, "max_tokens": 1000}'
) ON CONFLICT DO NOTHING;

-- Function to update current_load in experts when conversation status/assignment changes
CREATE OR REPLACE FUNCTION update_expert_load()
RETURNS TRIGGER AS $$
BEGIN
    -- Decrement load for the old expert if they were unassigned or chat resolved
    IF (TG_OP = 'UPDATE' OR TG_OP = 'DELETE') THEN
        IF OLD.assigned_expert_id IS NOT NULL THEN
            UPDATE experts
            SET current_load = GREATEST(0, (
                SELECT COUNT(*) FROM conversations
                WHERE assigned_expert_id = OLD.assigned_expert_id
                  AND status = 'handed_off'
            ))
            WHERE id = OLD.assigned_expert_id;
        END IF;
    END IF;

    -- Increment load for the new expert if assigned
    IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') THEN
        IF NEW.assigned_expert_id IS NOT NULL THEN
            UPDATE experts
            SET current_load = (
                SELECT COUNT(*) FROM conversations
                WHERE assigned_expert_id = NEW.assigned_expert_id
                  AND status = 'handed_off'
            )
            WHERE id = NEW.assigned_expert_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for conversation assignment load calculation
CREATE OR REPLACE TRIGGER trg_update_expert_load
AFTER INSERT OR UPDATE OR DELETE ON conversations
FOR EACH ROW
EXECUTE FUNCTION update_expert_load();
