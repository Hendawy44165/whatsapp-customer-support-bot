-- ============================================================
-- 001_initial_schema.sql
-- Run this in the Supabase SQL Editor to initialize all tables.
-- Project: Nuit Fragrances WhatsApp Customer Support Bot
-- ============================================================

-- ----------------------------------------------------------------
-- Conversations
-- Tracks every chat thread (customer ↔ agent / expert).
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
  id                  TEXT        PRIMARY KEY,
  customer_phone      TEXT        NOT NULL,
  platform            TEXT        DEFAULT 'whatsapp',
  status              TEXT        DEFAULT 'active',          -- active | pending_handoff | handed_off | resolved
  handoff_summary     TEXT,
  hubspot_contact_id  TEXT,
  assigned_expert_id  TEXT,
  cost_usd            REAL        DEFAULT 0,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- Messages
-- Every individual message (customer / agent / human expert).
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
  id               BIGSERIAL   PRIMARY KEY,
  conversation_id  TEXT        REFERENCES conversations(id) ON DELETE CASCADE,
  sender_type      TEXT        NOT NULL,                     -- customer | agent | human
  content          TEXT        NOT NULL,
  sentiment        TEXT,
  intent           TEXT,
  sentiment_data   JSONB,
  tokens_used      INTEGER     DEFAULT 0,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- Tickets  (escalations / support tickets)
-- Created whenever a conversation is escalated to a human expert.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tickets (
  id               BIGSERIAL   PRIMARY KEY,
  conversation_id  TEXT        REFERENCES conversations(id) ON DELETE CASCADE,
  customer_phone   TEXT        NOT NULL,
  summary          TEXT,
  status           TEXT        DEFAULT 'open',              -- open | in_progress | resolved | closed
  assigned_to      TEXT,
  hubspot_note_id  TEXT,
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  resolved_at      TIMESTAMPTZ
);

-- ----------------------------------------------------------------
-- Products  (seeded from the original SQLite database)
-- Nuit Fragrances product catalogue.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
  id              TEXT    PRIMARY KEY,
  category        TEXT    NOT NULL,
  name            TEXT    NOT NULL,
  price           REAL    NOT NULL,
  promo_price     REAL,
  variant         TEXT,
  stock_quantity  INTEGER DEFAULT 0,
  is_available    BOOLEAN DEFAULT TRUE,
  description     TEXT
);

-- ----------------------------------------------------------------
-- System Logs
-- Internal audit / debug log stream.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_logs (
  id         BIGSERIAL   PRIMARY KEY,
  source     TEXT,
  level      TEXT,        -- INFO | WARNING | ERROR | DEBUG
  message    TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- Message Buffer  (outbound queue)
-- Stores agent responses to be dispatched after a delay.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS message_buffer (
  id               BIGSERIAL   PRIMARY KEY,
  conversation_id  TEXT        REFERENCES conversations(id) ON DELETE CASCADE,
  content          TEXT        NOT NULL,
  status           TEXT        DEFAULT 'pending',            -- pending | sent | failed
  scheduled_for    TIMESTAMPTZ DEFAULT NOW(),
  sent_at          TIMESTAMPTZ,
  error            TEXT,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- Documents
-- RAG knowledge-base documents uploaded by admins.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
  id         BIGSERIAL   PRIMARY KEY,
  filename   TEXT        UNIQUE NOT NULL,
  category   TEXT,        -- faq | products | sop | general
  content    TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- Settings
-- Key/value store for runtime-configurable system parameters.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settings (
  key        TEXT   PRIMARY KEY,
  value      JSONB,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- Experts
-- Human agent profiles for the escalation console.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experts (
  id                TEXT    PRIMARY KEY,
  name              TEXT    NOT NULL,
  email             TEXT,
  chat_redirect_url TEXT,
  is_active         BOOLEAN DEFAULT TRUE
);

-- ================================================================
-- Row Level Security
-- Dashboard uses the anon key → allow SELECT; writes go through
-- the service-role key (server-side only).
-- ================================================================
ALTER TABLE conversations  ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages       ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets        ENABLE ROW LEVEL SECURITY;
ALTER TABLE products       ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_logs    ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_buffer ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents      ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings       ENABLE ROW LEVEL SECURITY;
ALTER TABLE experts        ENABLE ROW LEVEL SECURITY;

-- Allow read-only access for the anonymous (dashboard) role
CREATE POLICY "Allow anon select on conversations"  ON conversations  FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon select on messages"       ON messages       FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon select on tickets"        ON tickets        FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon select on products"       ON products       FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon select on system_logs"    ON system_logs    FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon select on documents"      ON documents      FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon select on settings"       ON settings       FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon select on experts"        ON experts        FOR SELECT TO anon USING (true);

-- Full access for the service role (used by the backend server)
CREATE POLICY "Allow service role full access on conversations"  ON conversations  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Allow service role full access on messages"       ON messages       FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Allow service role full access on tickets"        ON tickets        FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Allow service role full access on products"       ON products       FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Allow service role full access on system_logs"    ON system_logs    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Allow service role full access on message_buffer" ON message_buffer FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Allow service role full access on documents"      ON documents      FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Allow service role full access on settings"       ON settings       FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Allow service role full access on experts"        ON experts        FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ================================================================
-- Performance Indexes
-- ================================================================
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id    ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at         ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_message_buffer_status       ON message_buffer(status, scheduled_for);
CREATE INDEX IF NOT EXISTS idx_conversations_status        ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at      ON system_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_conversation_id     ON tickets(conversation_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status              ON tickets(status);
