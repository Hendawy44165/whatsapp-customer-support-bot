#!/bin/bash
# run.sh - Start the local Supabase Postgres Docker containers

# Get directory where script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "[run.sh] Starting local Supabase database container..."
docker compose up -d

echo "[run.sh] Checking container status..."
docker compose ps
