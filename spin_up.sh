#!/usr/bin/env bash
# ==============================================================================
# spin_up.sh - Local Development Orchestrator for Nuit Customer Support Bot
#
# Launches the FastAPI backend (with local SQLite DB) and the React frontend 
# concurrently in the background. Absolutely no Docker or Supabase required.
# ==============================================================================

# Exit immediately if a command exits with a non-zero status
set -e

# Ensure common local bin directories are in PATH
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=== 🔮 Nuit Fragrances Local Startup Orchestrator ==="

# ------------------------------------------------------------------------------
# 1. Prerequisite Verification
# ------------------------------------------------------------------------------
echo "Checking prerequisites..."

# Check Node.js
if ! command -v node &>/dev/null; then
  echo "❌ Error: Node.js is not installed. Please install Node.js."
  echo "   Refer to: https://nodejs.org/"
  exit 1
fi

# Check npm
if ! command -v npm &>/dev/null; then
  echo "❌ Error: npm is not installed. Please install npm."
  exit 1
fi

# Check uv (user-specified Python runner)
if ! command -v uv &>/dev/null; then
  echo "❌ Error: 'uv' is not installed."
  echo "   Install using: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

# Check Tailscale
HAS_TAILSCALE=true
if ! command -v tailscale &>/dev/null; then
  echo "⚠️  Warning: 'tailscale' is not installed or not in PATH."
  echo "   Tailscale funnel will not be started automatically."
  HAS_TAILSCALE=false
fi

echo "✅ Prerequisites OK."

# ------------------------------------------------------------------------------
# 2. Local Configuration Settings
# ------------------------------------------------------------------------------
# Setup backend env
cd "$ROOT_DIR/backend"
if [ ! -f ".env" ]; then
  echo "⚙️  Creating backend/.env from .env.example..."
  cp .env.example .env
fi

# Setup frontend env (clear VITE_SUPABASE keys so it defaults to FastAPI REST API)
cd "$ROOT_DIR/frontend"
echo "# Local configuration" > .env
echo "# Supabase keys omitted; dashboard will route directly to FastAPI server" >> .env
echo "✅ Configuration env files check completed."

# ------------------------------------------------------------------------------
# 3. Install & Start Application
# ------------------------------------------------------------------------------
echo "📦 Installing application dependencies..."
cd "$ROOT_DIR/frontend"
npm install --no-audit --no-fund

cd "$ROOT_DIR/backend"
uv sync

# Define cleanup function to terminate background tasks
cleanup() {
  echo ""
  echo "🧹 Cleaning up background tasks..."
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "$FRONTEND_PID" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [ -n "$TAILSCALE_PID" ]; then
    echo "Stopping Tailscale funnel..."
    kill "$TAILSCALE_PID" 2>/dev/null || true
  fi
  echo "✅ Cleaned up. Exiting."
  exit 0
}

# Attach clean up process to signals
trap cleanup INT TERM

echo "🔥 Starting FastAPI backend server (SQLite)..."
cd "$ROOT_DIR/backend"
uv run uvicorn app:app --host 0.0.0.0 --port 8000 > "$ROOT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

echo "🔥 Starting React frontend dashboard..."
cd "$ROOT_DIR/frontend"
npm run dev > "$ROOT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

TAILSCALE_PID=""
if [ "$HAS_TAILSCALE" = true ]; then
  echo "🔥 Starting Tailscale Funnel on port 8000 in the background..."
  tailscale funnel 8000 > "$ROOT_DIR/tailscale.log" 2>&1 &
  TAILSCALE_PID=$!
fi

echo "------------------------------------------------------------------------------"
echo "🎉 Nuit Support Bot local stack is running!"
echo "------------------------------------------------------------------------------"
echo "🔌 Backend API Swagger UI: http://localhost:8000/docs"
echo "💻 Frontend Dashboard:     http://localhost:5173"
if [ "$HAS_TAILSCALE" = true ]; then
  echo "📡 Tailscale Funnel:       Exposing port 8000 publicly"
fi
echo "------------------------------------------------------------------------------"
echo "📝 Log files:"
echo "   - Backend:   $ROOT_DIR/backend.log"
echo "   - Frontend:  $ROOT_DIR/frontend.log"
if [ "$HAS_TAILSCALE" = true ]; then
  echo "   - Tailscale: $ROOT_DIR/tailscale.log"
fi
echo "------------------------------------------------------------------------------"
echo "🛑 Press Ctrl+C to terminate all services."
echo "------------------------------------------------------------------------------"

# Keep script running to maintain logs and trap signals
while true; do
  sleep 1
done
