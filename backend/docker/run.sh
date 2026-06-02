#!/bin/bash
# run.sh - Bootstrap and launch the official Supabase Docker Compose stack

# Get directory where script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/supabase"

# 1. Initialize environmental variables
if [ ! -f .env ]; then
    echo "[run.sh] Copying .env.example to .env..."
    cp .env.example .env
    
    echo "[run.sh] Generating secure JWT secrets and API keys..."
    sh utils/generate-keys.sh --update-env
    sh utils/add-new-auth-keys.sh --update-env
    
    echo "[run.sh] Reconfiguring ports to prevent local conflicts (Gateway: 54321, DB: 54322)..."
    # Customize ports in .env
    sed -i "s|^KONG_HTTP_PORT=.*$|KONG_HTTP_PORT=54321|g" .env
    sed -i "s|^POSTGRES_PORT=.*$|POSTGRES_PORT=54322|g" .env
    sed -i "s|^SUPABASE_PUBLIC_URL=.*$|SUPABASE_PUBLIC_URL=http://localhost:54321|g" .env
    sed -i "s|^API_EXTERNAL_URL=.*$|API_EXTERNAL_URL=http://localhost:54321|g" .env
fi

echo "[run.sh] Starting official Supabase container stack..."
docker compose up -d

echo ""
echo "================================================================="
echo "  Supabase Local Docker Stack is running!"
echo "  - Database Connection: postgresql://postgres:<password>@localhost:54322/postgres"
echo "  - Supabase Studio Dashboard: http://localhost:54321"
echo "================================================================="
echo ""
