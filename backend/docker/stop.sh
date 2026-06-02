#!/bin/bash
# stop.sh - Stop the official Supabase Docker Compose stack

# Get directory where script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/supabase"

echo "[stop.sh] Stopping Supabase database and service containers..."
docker compose stop
