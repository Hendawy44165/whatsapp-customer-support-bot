#!/bin/bash
# delete.sh - Teardown and delete the local database containers, networks, and persistent data volumes

# Get directory where script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/supabase"

echo "[delete.sh] Tearing down the local Supabase container stack..."
docker compose down -v

echo "[delete.sh] Cleaning up environment config files..."
rm -f .env .env.old

echo "[delete.sh] Cleanup complete. Persistent volumes and networks removed."
