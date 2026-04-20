#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# Error / warning
# -----------------------------
err() { echo "Error: $*" >&2; }
warn() { echo "Warning: $*" >&2; }

# -----------------------------
# Defaults
# -----------------------------
MONGO_NAME="argot-mongodb"
MONGO_PORT="27017"
MONGO_DATA="${HOME}/mongo_data"
DUMP_FILE=""

# -----------------------------
# Usage
# -----------------------------
usage() {
    echo "MongoDB Setup for Argot3"
    echo
    echo "Start a MongoDB container and optionally restore a dump archive."
    echo
    echo "Usage:"
    echo "  $0 [-n <name>] [-d <data_dir>] [-f <dump_file>]"
    echo
    echo "Options:"
    echo "  -n <name>       MongoDB container name (default: argot-mongodb)"
    echo "  -d <data_dir>   Host directory for persistent data (default: ~/mongo_data)"
    echo "  -f <dump_file>  MongoDB archive dump to restore (optional)"
    echo "  -h              Show this help message and exit"
    echo
    exit 1
}

# -----------------------------
# Parse args
# -----------------------------
while getopts ":n:d:f:h" opt; do
    case $opt in
        n) MONGO_NAME=$OPTARG ;;
        d) MONGO_DATA=$OPTARG ;;
        f) DUMP_FILE=$OPTARG ;;
        h) usage ;;
        \?) err "unknown argument '-$OPTARG'"; usage ;;
        :) err "missing required value for -$OPTARG"; usage ;;
    esac
done

# -----------------------------
# Validate environment
# -----------------------------
command -v docker >/dev/null 2>&1 || { err "required executable not found 'docker'"; exit 1; }

echo "=== MongoDB setup ==="

# Ensure data directory exists
mkdir -p "${MONGO_DATA}"

# -----------------------------
# Check if container exists
# -----------------------------
if docker ps -a --format '{{.Names}}' | grep -q "^${MONGO_NAME}$"; then
    echo "Container '${MONGO_NAME}' already exists"

    if docker ps --format '{{.Names}}' | grep -q "^${MONGO_NAME}$"; then
        echo "MongoDB already running"
    else
        echo "Starting existing container..."
        docker start "${MONGO_NAME}"
    fi
else
    echo "Creating MongoDB container..."

    docker run -d \
        --name "${MONGO_NAME}" \
        -p "${MONGO_PORT}:27017" \
        -v "${MONGO_DATA}:/data/db" \
        mongo:7 || { err "failed to start MongoDB container (port ${MONGO_PORT} may already be in use)"; exit 1; }
fi

# -----------------------------
# Wait for readiness
# -----------------------------
echo "Waiting for MongoDB..."

ready=0
for i in $(seq 1 30); do
    if docker exec "${MONGO_NAME}" \
        mongosh --quiet --eval "db.runCommand({ ping: 1 })" \
        >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 1
done

[[ "$ready" -eq 1 ]] || { err "MongoDB did not become ready in time"; exit 1; }

echo "MongoDB is ready (localhost:${MONGO_PORT})"

# -----------------------------
# Restore dump (optional)
# -----------------------------
if [[ -n "${DUMP_FILE}" ]]; then
    echo "Restoring database from dump '${DUMP_FILE}'..."

    [[ -f "${DUMP_FILE}" ]] || { err "dump file not found '${DUMP_FILE}'"; exit 1; }

    warn "restoring dump (existing data will be overwritten)..."

    docker exec -i "${MONGO_NAME}" \
        mongorestore --archive --drop < "${DUMP_FILE}"

    echo "Restore complete"
else
    echo "No dump provided, skipping restore"
fi

# -----------------------------
# Final info
# -----------------------------
echo
echo "MongoDB is running:"
echo "  Host: localhost"
echo "  Port: ${MONGO_PORT}"
echo "  Container: ${MONGO_NAME}"
echo "  Data dir: ${MONGO_DATA}"

echo
echo "=== DONE ==="