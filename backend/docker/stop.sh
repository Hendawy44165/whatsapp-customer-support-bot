#!/bin/bash
# stop.sh - Stop the local Supabase Postgres Docker containers

# Get directory where script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "[stop.sh] Stopping local Supabase database container..."
docker compose stop
