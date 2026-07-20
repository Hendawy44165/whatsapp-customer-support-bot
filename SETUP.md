# 🛠️ Setup Guide — Nuit Fragrances WhatsApp Customer Support Bot

> **Who is this for?** Anyone setting up the project for the first time. You do **not** need
> deep backend experience. Follow each section in order and you will have a fully working
> local development environment by the end.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quickstart: Local Orchestrator (One-Click Docker Setup)](#2-quickstart-local-orchestrator-one-click-docker-setup)
3. [Clone and Directory Layout](#3-clone-and-directory-layout)
4. [Supabase Setup](#4-supabase-setup)
5. [Meta WhatsApp Cloud API Setup](#5-meta-whatsapp-cloud-api-setup)
6. [HubSpot Setup](#6-hubspot-setup)
7. [LangSmith Setup](#7-langsmith-setup)
8. [Environment Variables Reference](#8-environment-variables-reference)
9. [Running the Backend (Manual Option)](#9-running-the-backend-manual-option)
10. [Running the Frontend (Manual Option)](#10-running-the-frontend-manual-option)
11. [Verifying Everything Works](#11-verifying-everything-works)
12. [Common Issues and Troubleshooting](#12-common-issues-and-troubleshooting)

---

## 1. Prerequisites

| Tool | Minimum Version | Install guide |
|------|----------------|---------------|
| **Python** | 3.12+ | https://python.org/downloads |
| **uv** (recommended) | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Node.js** | 18+ | https://nodejs.org |
| **npm** | 9+ | bundled with Node.js |
| **Git** | any | https://git-scm.com |

> **Tip:** We use `uv` instead of `pip` for dependency management. If you prefer plain pip,
> every `uv` command has a direct pip equivalent shown in each section.

---

## 2. Quickstart: Local Orchestrator (One-Click Docker Setup)

We have provided a unified orchestration script `spin_up.sh` in the root of the project that completely automates your local startup:

### What the script does:
1. **Checks Prerequisites**: Validates that Docker, Docker Compose, Node, npm, and `uv` are installed.
2. **Bootstraps Supabase**: Clones the official self-hosted Supabase Docker configuration into `backend/docker/supabase/` if not present.
3. **Generates Keys & Avoids Conflicts**: Automatically creates secure JWT/database credentials and moves Kong API gateway HTTP port from `8000` to `54321` (saving `8000` for your FastAPI backend).
4. **Launches Containers**: Spins up local Supabase database, studio, auth, and gateway services in Docker.
5. **Migrates Schema**: Waits for Postgres database readiness and applies `backend/migrations/001_initial_schema.sql` SQL migrations automatically.
6. **Injects Env Keys**: Synchronizes the generated keys directly to your local `backend/.env` and `frontend/.env` configurations.
7. **Installs & Runs Services**: Installs dependencies and runs both the FastAPI server and the React Vite dev server concurrently in the background.

### Usage:
```bash
./spin_up.sh

# Or, if you need to perform a clean database reset (clears persistent Docker data):
./spin_up.sh --reset
```

To close all servers and shut down local Docker containers gracefully, simply press `Ctrl+C` in your terminal.

---

## 3. Clone and Directory Layout

```bash
git clone <your-repo-url>
cd customer-support-bot
```

```
customer-support-bot/
├── backend/                  ← FastAPI server (Python)
│   ├── app.py
│   ├── database.py           ← Supabase client
│   ├── migrations/
│   │   └── 001_initial_schema.sql
│   ├── .env.example          ← Copy this to .env and fill in values
│   └── requirements.txt
├── frontend/                 ← React dashboard (Node.js)
└── SETUP.md                  ← This file
```

---

## 3. Supabase Setup

Supabase is the cloud Postgres database that stores conversations, messages, tickets, and
all other persistent data.

### 3.1 Create a Supabase Project

1. Go to **https://app.supabase.com** and sign in (free account is sufficient).
2. Click **New project**.
3. Choose your organisation, pick a project name (e.g. `nuit-bot`), set a strong database
   password, and choose the region closest to your users.
4. Wait approximately 2 minutes for the project to spin up.

### 3.2 Get Your API Keys

1. In the left sidebar click **Settings → API**.
2. Copy the following values — you will need them in `.env`:

| `.env` variable | Where to find it |
|-----------------|-----------------|
| `SUPABASE_URL` | **Project URL** (e.g. `https://abcdefgh.supabase.co`) |
| `SUPABASE_SERVICE_KEY` | **service_role** secret (bottom of the page — keep private!) |
| `SUPABASE_ANON_KEY` | **anon** public key (safe to expose to browsers) |

> **Security warning:** The `SUPABASE_SERVICE_KEY` bypasses Row Level Security.
> Never commit it to git or expose it in frontend code. It is used **server-side only**.

### 3.3 Run the SQL Migration

1. In the Supabase dashboard, click **SQL Editor** in the left sidebar.
2. Click **New query**.
3. Open `backend/migrations/001_initial_schema.sql` from this repository.
4. Copy the entire file contents and paste into the SQL Editor.
5. Click **Run** (or press `Ctrl+Enter`).
6. You should see `Success. No rows returned.`

**What the migration creates:**

- `conversations` — every customer chat thread
- `messages` — individual messages (customer / agent / human expert)
- `tickets` — escalation records when a conversation is handed off
- `products` — Nuit Fragrances product catalogue
- `system_logs` — internal audit and debug stream
- `message_buffer` — outbound message queue with scheduling support
- `documents` — RAG knowledge-base documents uploaded by admins
- `settings` — key/value store for runtime-configurable system parameters
- `experts` — human agent profiles for the escalation console
- Performance indexes on all frequently-queried columns
- Row Level Security (RLS) policies for anon and service roles

### 3.4 Verify Tables Were Created

1. Click **Table Editor** in the left sidebar.
2. You should see all 9 tables listed.

### 3.5 Row Level Security (Already Applied by Migration)

The migration enables RLS on all tables and creates two policy layers:

- **Anon role** — SELECT only. Used by the React frontend dashboard with the public anon key.
- **Service role** — Full access. Used by the FastAPI backend with the service key.

No manual steps needed. If you add new tables in the future, remember to add RLS policies.

---

## 4. Meta WhatsApp Cloud API Setup

### 4.1 Create a Meta Developer Account

1. Go to **https://developers.facebook.com** and log in with your Facebook account.
2. Click **My Apps → Create App**.
3. Select **Business** as the app type.
4. Fill in the app name (e.g. `Nuit Bot`) and your contact email, then click **Create app**.

### 4.2 Add the WhatsApp Product

1. Inside your new app, scroll down the dashboard and click **Set up** next to **WhatsApp**.
2. Follow the WhatsApp Business API onboarding wizard.

### 4.3 Get Your Phone Number ID and Access Token

1. Navigate to **WhatsApp → API Setup** in the left sidebar.
2. Under **Step 1 – Select phone number**, note the **Phone number ID**
   (a long number like `123456789012345`).
3. Click **Generate access token** to get a temporary 24-hour token, suitable for development.

For production, create a non-expiring **System User** token:

- Go to **Business Settings → System users → Add system user → Generate new token**
- Select your app and grant `whatsapp_business_messaging` and `whatsapp_business_management` permissions.

| `.env` variable | Value |
|-----------------|-------|
| `META_PHONE_NUMBER_ID` | Phone number ID from step 2 |
| `META_WHATSAPP_TOKEN` | Your access token |

### 4.4 Configure the Webhook

The backend exposes a webhook endpoint at `POST /webhook/whatsapp`. Meta will call this
URL every time a customer sends a WhatsApp message to your number.

**For local development** you need a public HTTPS URL because Meta cannot reach `localhost`.
Use a tunnel tool:

```bash
# Option A – ngrok (recommended for development)
ngrok http 8000
# Copy the printed https://xxxx.ngrok-free.app URL

# Option B – cloudflared
cloudflared tunnel --url http://localhost:8000
```

Then in the Meta Developer Console:

1. Go to **WhatsApp → Configuration → Webhook**.
2. Set **Callback URL** to `https://your-tunnel-url/webhook/whatsapp`.
3. Set **Verify token** to any random string you choose (e.g. `nuit_bot_verify_abc123`).
4. Click **Verify and save**.
5. Click **Manage** and subscribe to the `messages` field.

| `.env` variable | Value |
|-----------------|-------|
| `META_WEBHOOK_VERIFY_TOKEN` | The verify token string you chose above |

### 4.5 Send a Test Message

In Meta Developer Console → API Setup, use the **Send and receive messages** sandbox tool
to send a test message from Meta's sandbox number to your registered WhatsApp number.

---

## 5. HubSpot Setup

HubSpot is used to create CRM contacts and notes when conversations are escalated to a
human expert (i.e. a ticket is created).

### 5.1 Create a Private App

1. Log in to **https://app.hubspot.com**.
2. Click the gear icon (Settings) → **Integrations → Private Apps**.
3. Click **Create a private app**.
4. Give it a name (e.g. `Nuit Bot Integration`).
5. Under the **Scopes** tab, enable:
   - `crm.objects.contacts.read`
   - `crm.objects.contacts.write`
   - `crm.objects.notes.read`
   - `crm.objects.notes.write`
6. Click **Create app** and then **Continue creating** on the confirmation dialog.
7. Copy the **Access token** shown on the confirmation screen.

| `.env` variable | Value |
|-----------------|-------|
| `HUBSPOT_ACCESS_TOKEN` | The access token from step 7 |

> **Note:** HubSpot private-app tokens do not expire on their own, but treat this token
> like a password. Never commit it to git.

---

## 6. LangSmith Setup

LangSmith provides real-time tracing, debugging, and observability for all LangGraph and
LangChain runs. It is optional but strongly recommended for development.

1. Create a free account at **https://smith.langchain.com**.
2. Click your avatar in the top-right → **Settings → API Keys → Create API key**.
3. Copy the key.

| `.env` variable | Value |
|-----------------|-------|
| `LANGSMITH_API_KEY` | Your LangSmith API key |
| `LANGSMITH_PROJECT` | `nuit-bot-v2` (or any project name you prefer) |
| `LANGSMITH_TRACING` | `true` |
| `LANGSMITH_ENDPOINT` | `https://api.smith.langchain.com` |

Once set, all agent runs will appear automatically in the LangSmith dashboard.

---

## 7. Environment Variables Reference

Create `backend/.env` by copying the example file:

```bash
cp backend/.env.example backend/.env
# Then open backend/.env and fill in all values
```

| Variable | Required | Description |
|----------|----------|-------------|
| `PROVIDER_API_KEY` | Required | API key for your LLM provider (OpenAI, GitHub Models, etc.) |
| `PROVIDER_BASE_URL` | Required | Base URL of the LLM API |
| `PROVIDER_MODEL_NAME` | Required | Model identifier (e.g. `openai/gpt-4.1-mini`) |
| `SUPABASE_URL` | Required | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Required | Supabase service-role key — server-side only, never expose |
| `SUPABASE_ANON_KEY` | Required | Supabase anonymous/public key — safe for frontend |
| `META_PHONE_NUMBER_ID` | Production | WhatsApp Cloud API phone number ID |
| `META_WHATSAPP_TOKEN` | Production | WhatsApp Cloud API access token |
| `META_WEBHOOK_VERIFY_TOKEN` | Production | Random string used to verify the Meta webhook |
| `HUBSPOT_ACCESS_TOKEN` | Production | HubSpot private-app access token |
| `LANGSMITH_TRACING` | Optional | Enable LangSmith tracing — `true` or `false` |
| `LANGSMITH_ENDPOINT` | Optional | LangSmith API endpoint |
| `LANGSMITH_API_KEY` | Optional | LangSmith API key |
| `LANGSMITH_PROJECT` | Optional | LangSmith project name |
| `SQLITE_SIM_DB` | Optional | Path to local SQLite product DB (default: `local_supabase_sim.db`) |

> Variables labelled **Production** are not required for local simulation via `/api/chat`
> but are necessary for a live WhatsApp integration.

---

## 9. Running the Backend (Manual Option)

### 8.1 Install Dependencies

**With uv (recommended):**

```bash
cd backend
uv sync
```

**With pip:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 8.2 Start the FastAPI Server

```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Expected startup output:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:database:DatabaseClient: Connected to Supabase at https://your-project.supabase.co
INFO:database:DatabaseClient: Initialising local products SQLite DB at: local_supabase_sim.db
```

### 8.3 Available API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Send a customer message through the AI agent |
| `GET` | `/api/conversations` | List all conversations (admin dashboard) |
| `GET` | `/api/documents` | List knowledge-base documents |
| `POST` | `/api/upload` | Upload a `.md` or `.txt` reference document |
| `DELETE` | `/api/documents/{filename}` | Remove a document |
| `GET` | `/api/settings/{key}` | Get a system setting value |
| `POST` | `/api/settings/{key}` | Update a system setting value |
| `GET` | `/api/expert/conversations` | Expert console — conversation queue |
| `POST` | `/api/expert/claim/{conversation_id}` | Claim a pending conversation |
| `POST` | `/api/expert/resolve/{conversation_id}` | Resolve a conversation |
| `GET` | `/api/expert/profiles` | List all expert profiles |

Interactive API documentation (Swagger UI) is available at **http://localhost:8000/docs**.

---

## 10. Running the Frontend (Manual Option)

```bash
cd frontend
npm install
npm run dev
```

The React dashboard will start at **http://localhost:5173** (Vite default port).

Make sure the backend is already running at `http://localhost:8000` before opening
the dashboard — the frontend makes API calls to that address.

---

## 11. Verifying Everything Works

### Database connectivity

After starting the backend, look for this line in the logs:

```
INFO:database:DatabaseClient: Connected to Supabase at https://your-project.supabase.co
```

If you see `WARNING: SUPABASE_URL is not set` instead, your `backend/.env` file is missing
or the `SUPABASE_URL` value is blank.

### Test a chat message via curl

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, what perfumes do you have?", "customer_phone": "+201234567890"}'
```

Expected response:

```json
{
  "status": "processed",
  "message": "Agent process completed successfully. Output response buffered.",
  "is_handoff": false,
  "handoff_summary": ""
}
```

### Check Supabase for new data

In the Supabase dashboard → **Table Editor**:
- Open `conversations` — you should see a new row for your test chat.
- Open `messages` — you should see the customer message and the agent's response.
- Open `message_buffer` — you should see the queued outbound response.

### LangSmith traces

Go to **https://smith.langchain.com** → your project. A new trace should appear within
a few seconds of sending the chat request.

---

## 12. Common Issues and Troubleshooting

### `RuntimeError: Supabase client is not initialised`

Your `SUPABASE_URL` or `SUPABASE_SERVICE_KEY` is missing or empty in `backend/.env`.
Confirm the file exists (not just `.env.example`) and both values are filled in.

### Import error for supabase

If you see an import error related to supabase, you have an outdated version:

```bash
uv sync
# or
pip install "supabase>=2.0.0"
```

### `401 Unauthorized` from Supabase

You are using the wrong API key. The **backend** must use the `SUPABASE_SERVICE_KEY`
(labelled **secret** / service_role in the Supabase dashboard), not the anon key.

### Webhook verification fails — Meta returns 403

The `META_WEBHOOK_VERIFY_TOKEN` in your `.env` must **exactly** match the verify token
you typed into the Meta Webhook configuration screen. Check for trailing spaces or
copy-paste errors.

### HubSpot returns 401

The HubSpot private-app token may have been deleted or regenerated. Create a new token
in HubSpot → Settings → Integrations → Private Apps.

### Frontend shows an empty conversations list

The frontend reads from `http://localhost:8000/api/conversations`. Confirm:
1. The backend is running.
2. At least one conversation exists in Supabase (send a test `/api/chat` request first).
3. The browser console has no CORS errors (the backend allows all origins by default).

### `ModuleNotFoundError: No module named 'supabase'`

The virtual environment is missing the supabase package. Inside `backend/` run:

```bash
uv sync
# or (with venv activated)
pip install -r requirements.txt
```

---

*Last updated: 2026-07-12 — Stream A initial Supabase migration*
