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
RUNTIME=""
MONGO_NAME="argot-mongodb"
MONGO_PORT="27017"
MONGO_DATA="${HOME}/mongo_data"
DUMP_FILE=""
SIF_IMAGE=""
FORCE=0

# -----------------------------
# Usage
# -----------------------------
usage() {
    echo "Argot3 - MongoDB Setup"
    echo
    echo "Start a MongoDB instance (Docker or Singularity) and optionally restore a dump archive."
    echo
    echo "Usage:"
    echo "  $0 [-r <runtime>] [-n <name>] [-p <port>] [-d <data_dir>] [-f <dump_file>] [-i <sif>] [--force]"
    echo
    echo "Options:"
    echo "  -r <runtime>    Container runtime: docker | singularity (default: auto-detect)"
    echo "  -n <name>       Container/instance name (default: argot-mongodb)"
    echo "  -p <port>       MongoDB port (default: 27017)"
    echo "  -d <data_dir>   Host directory for persistent data (default: ~/mongo_data)"
    echo "  -f <dump_file>  MongoDB archive dump to restore (optional)"
    echo "  -i <sif>        Singularity SIF image (optional, default: docker://mongo:7)"
    echo "  --force         Remove existing data directory before starting"
    echo "  -h              Show this help message and exit"
    echo
    exit 1
}

# -----------------------------
# Parse args
# -----------------------------
args=()
for arg in "$@"; do
    case $arg in
        --force) FORCE=1 ;;
        --) ;;
        *) args+=("$arg") ;;
    esac
done
set -- "${args[@]+"${args[@]}"}"

while getopts ":r:n:p:d:f:i:h" opt; do
    case $opt in
        r) RUNTIME=$OPTARG ;;
        n) MONGO_NAME=$OPTARG ;;
        p) MONGO_PORT=$OPTARG ;;
        d) MONGO_DATA=$OPTARG ;;
        f) DUMP_FILE=$OPTARG ;;
        i) SIF_IMAGE=$OPTARG ;;
        h) usage ;;
        \?) err "unknown argument '-$OPTARG'"; usage ;;
        :) err "missing required value for -$OPTARG"; usage ;;
    esac
done

# -----------------------------
# Validate arguments
# -----------------------------
[[ "$MONGO_PORT" =~ ^[0-9]+$ ]] || {
    err "invalid value for -p <port> (got '$MONGO_PORT')"
    exit 1
}

[[ -n "$SIF_IMAGE" && ! -f "$SIF_IMAGE" ]] && {
    err "file not found '$SIF_IMAGE' (-i)"
    exit 1
}

echo "=== MongoDB setup ==="

# Resolve absolute path (realpath -m is GNU coreutils; fall back to Python on macOS)
if realpath -m / >/dev/null 2>&1; then
    MONGO_DATA="$(realpath -m "${MONGO_DATA}")"
else
    MONGO_DATA="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "${MONGO_DATA}")"
fi

# Safety checks
if [[ -z "${MONGO_DATA}" || "${MONGO_DATA}" == "/" ]]; then
    err "refusing to use unsafe path '${MONGO_DATA}'"
    exit 1
fi

# Disallow critical system paths
case "${MONGO_DATA}" in
    /bin|/boot|/dev|/etc|/lib|/lib64|/proc|/root|/run|/sbin|/sys|/usr|/var)
        err "refusing to use system path '${MONGO_DATA}'"
        exit 1
        ;;
esac

# Handle existing data directory
if [[ -d "${MONGO_DATA}" ]]; then
    if [[ "${FORCE}" -eq 1 ]]; then
        warn "removing existing data directory '${MONGO_DATA}'"
        rm -rf "${MONGO_DATA}"
    else
        warn "using existing data directory '${MONGO_DATA}' (use --force to remove it)"
    fi
fi
mkdir -p "${MONGO_DATA}"

# -----------------------------
# Auto-detect runtime
# -----------------------------
if [[ -z "$RUNTIME" ]]; then
    if command -v docker >/dev/null 2>&1; then
        RUNTIME="docker"
    elif command -v singularity >/dev/null 2>&1; then
        RUNTIME="singularity"
    else
        err "no supported container runtime found (docker or singularity)"
        exit 1
    fi
    echo "Auto-detected runtime: $RUNTIME"
fi

case "$RUNTIME" in
    docker|singularity) ;;
    *) err "invalid value for -r <runtime> (got '$RUNTIME')"; exit 1 ;;
esac

# -----------------------------
# Docker implementation
# -----------------------------
run_docker() {
    command -v docker >/dev/null 2>&1 || {
        err "required executable not found 'docker'"
        exit 1
    }

    if docker ps -a --format '{{.Names}}' | grep -q "^${MONGO_NAME}$"; then
        echo "Container '${MONGO_NAME}' already exists"
        warn "reusing existing container '${MONGO_NAME}' (configuration may differ)"

        if docker ps --format '{{.Names}}' | grep -q "^${MONGO_NAME}$"; then
            echo "MongoDB already running"
        else
            echo "Starting container..."
            docker start "${MONGO_NAME}"
        fi
    else
        echo "Creating MongoDB container..."

        docker run -d \
            --name "${MONGO_NAME}" \
            -p "${MONGO_PORT}:27017" \
            -v "${MONGO_DATA}:/data/db" \
            mongo:7 || {
                err "failed to start container (port ${MONGO_PORT} in use?)"
                exit 1
            }

    fi
}

# -----------------------------
# Singularity implementation
# -----------------------------
run_singularity() {
    command -v singularity >/dev/null 2>&1 || {
        err "required executable not found 'singularity'"
        exit 1
    }

    local image="${SIF_IMAGE:-docker://mongo:7}"

    if singularity instance list 2>/dev/null | awk 'NR>1 {print $1}' | grep -q "^${MONGO_NAME}$"; then
        echo "Instance '${MONGO_NAME}' already running"
        warn "reusing existing instance '${MONGO_NAME}' (configuration may differ)"
    else
        echo "Starting Singularity instance..."

        singularity instance start \
            --bind "${MONGO_DATA}:/data/db" \
            "${image}" \
            "${MONGO_NAME}"

        echo "Launching mongod..."

        local mongod_log="${MONGO_DATA}/mongod.log.$(date +%s)"

        nohup singularity exec instance://"${MONGO_NAME}" \
            /bin/bash -c "mongod --dbpath /data/db --bind_ip 127.0.0.1 --port ${MONGO_PORT}" \
            > "${mongod_log}" 2>&1 &

        echo "mongod launched (log: ${mongod_log})"
    fi
}

# -----------------------------
# Wait for MongoDB
# -----------------------------
wait_mongo() {
    echo "Waiting for MongoDB..."

    ready=0
    for i in $(seq 1 30); do
        if [[ "$RUNTIME" == "docker" ]]; then
            if docker exec -i "${MONGO_NAME}" \
                     mongosh --quiet --eval "db.runCommand({ ping: 1 })" >/dev/null 2>&1; then
                ready=1
                break
            fi
        else
            if singularity exec instance://"${MONGO_NAME}" \
                     mongosh --port "${MONGO_PORT}" --quiet --eval "db.runCommand({ ping: 1 })" >/dev/null 2>&1; then
                ready=1
                break
            fi
        fi
        sleep 1
    done

    [[ "$ready" -eq 1 ]] || {
        err "MongoDB did not become ready in time"
        exit 1
    }

    echo "MongoDB is ready (localhost:${MONGO_PORT})"
}

# -----------------------------
# Restore dump
# -----------------------------
restore_dump() {
    if [[ -z "$DUMP_FILE" ]]; then
        echo "No dump provided, skipping restore"
        return
    fi

    echo "Restoring database from dump '${DUMP_FILE}'..."

    [[ -f "$DUMP_FILE" ]] || {
        err "file not found '$DUMP_FILE'"
        exit 1
    }

    warn "restoring dump (existing data will be overwritten)"

    if [[ "$RUNTIME" == "docker" ]]; then
        docker exec -i "${MONGO_NAME}" \
            mongorestore --archive --drop < "${DUMP_FILE}"
    else
        singularity exec instance://"${MONGO_NAME}" \
            mongorestore --port "${MONGO_PORT}" --archive --drop < "${DUMP_FILE}"
    fi

    echo "Restore complete"
}

# -----------------------------
# Main
# -----------------------------
case "$RUNTIME" in
    docker) run_docker ;;
    singularity) run_singularity ;;
esac

wait_mongo
restore_dump

# -----------------------------
# Final info
# -----------------------------
echo
echo "MongoDB is running:"
echo "  Runtime:  ${RUNTIME}"
echo "  Host:     localhost"
echo "  Port:     ${MONGO_PORT}"
echo "  Name:     ${MONGO_NAME}"
echo "  Data dir: ${MONGO_DATA}"

echo
echo "=== DONE ==="