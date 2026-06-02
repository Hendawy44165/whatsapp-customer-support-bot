#!/bin/bash
# delete.sh - Stop and remove containers, volumes, networks, and image of the database

# Get directory where script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "[delete.sh] Stopping and removing containers and volumes..."
docker compose down -v

# Remove the postgres image if requested (optional)
echo "[delete.sh] Deleting database Docker image..."
docker rmi supabase/postgres:15.1.1.78 || true

echo "[delete.sh] Cleanup complete."
