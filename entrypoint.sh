#!/usr/bin/env bash

set -euo pipefail

# -----------------------------
# Error / warning
# -----------------------------
err() { echo "Error: $*" >&2; }
warn() { echo "Warning: $*" >&2; }

# -----------------------------
# Execution control
# -----------------------------
dry_run=0
verbose=0
force=0

run() {
    if [[ "$dry_run" -eq 1 ]]; then
        echo -n "[DRY-RUN] "
        printf '%q ' "$@"
        echo
    else
        if [[ "$verbose" -eq 1 ]]; then
            echo -n "[RUN] "
            printf '%q ' "$@"
            echo
        fi
        "$@"
    fi
}

# -----------------------------
# Defaults
# -----------------------------
mode=""
exec_mode="sequential"

# shared
fasta=""
outdir=""
go_owl=""

# classic
diamond_db=""
threads=1
mongo_host="mongodb"
mongo_port=27017
mongo_db=""

# new
structure_dir=""
weights_dir=""

# scripts
script_classic="./src/run_classic_model.sh"
script_new="./src/run_new_model.sh"

# -----------------------------
# Usage
# -----------------------------
usage() {
    echo "Argot3"
    echo
    echo "Run the Argot3 classic model, the new structure-based model, or both pipelines."
    echo "MongoDB is expected to be running externally (e.g. via Docker Compose)."
    echo
    echo "Usage:"
    echo "  $0 --mode <classic|new|both> [options]"
    echo
    echo "Execution mode:"
    echo "  --mode <mode>          Select pipeline to run:"
    echo "                         classic   Run the DIAMOND + Argot3 pipeline"
    echo "                         new       Run the structure-based deep learning pipeline"
    echo "                         both      Run both pipelines"
    echo
    echo "  --exec <mode>          Execution strategy when --mode=both:"
    echo "                         sequential (default)   Run classic then new"
    echo "                         parallel               Run classic and new in parallel"
    echo
    echo "Shared arguments:"
    echo "  -f <fasta>             Input protein FASTA file"
    echo "  -o <outdir>            Output directory. Creates:"
    echo "                                              - <outdir>/classic"
    echo "                                              - <outdir>/new"
    echo "                                              - <outdir>/merged (when enabled)"
    echo "  -g <go.owl>            Gene Ontology file (OWL format)"
    echo
    echo "Classic model arguments:"
    echo "  -d <db>                DIAMOND database (prefix or .dmnd file)"
    echo "  -t <threads>           Number of threads for DIAMOND (default: 1)"
    echo "  --mongo-db <name>      MongoDB database name (e.g. ARGOT_DB)"
    echo "  --mongo-host <host>    MongoDB host (default: mongodb)"
    echo "  --mongo-port <port>    MongoDB port (default: 27017)"
    echo
    echo "New model arguments:"
    echo "  -s <dir>               Structure directory"
    echo "  -w <dir>               Weights directory"
    echo
    echo "Execution flags:"
    echo "      --dry-run          Print commands without executing them"
    echo "      --verbose          Print commands as they are executed"
    echo "      --force            Overwrite existing output directory"
    echo "  -h                     Show this help message and exit"
    echo
    exit 1
}

# -----------------------------
# Parse args
# -----------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode) mode=$2; shift 2 ;;
        --exec) exec_mode=$2; shift 2 ;;

        -f) fasta=$2; shift 2 ;;
        -o) outdir=$2; shift 2 ;;
        -g) go_owl=$2; shift 2 ;;

        -d) diamond_db=$2; shift 2 ;;
        -t) threads=$2; shift 2 ;;
        --mongo-db) mongo_db=$2; shift 2 ;;
        --mongo-host) mongo_host=$2; shift 2 ;;
        --mongo-port) mongo_port=$2; shift 2 ;;

        -s) structure_dir=$2; shift 2 ;;
        -w) weights_dir=$2; shift 2 ;;

        --dry-run) dry_run=1; shift ;;
        --verbose) verbose=1; shift ;;
        --force) force=1; shift ;;
        -h) usage ;;

        *) err "unknown argument '$1'"; usage ;;
    esac
done

# -----------------------------
# Validation
# -----------------------------
missing=0
[[ -z "$mode" ]]   && { err "missing required argument --mode <classic|new|both>"; missing=1; }
[[ -z "$fasta" ]]  && { err "missing required argument -f <fasta>"; missing=1; }
[[ -z "$outdir" ]] && { err "missing required argument -o <outdir>"; missing=1; }
[[ -z "$go_owl" ]] && { err "missing required argument -g <go.owl>"; missing=1; }

[[ $missing -eq 1 ]] && { echo; usage; }

case "$mode" in
    classic|new|both) ;;
    *) err "invalid value for --mode <classic|new|both>"; exit 1 ;;
esac

case "$exec_mode" in
    sequential|parallel) ;;
    *) err "invalid value for --exec <sequential|parallel>"; exit 1 ;;
esac

if [[ "$mode" != "both" && "$exec_mode" != "sequential" ]]; then
    warn "--exec is ignored unless --mode both"
fi

[[ -f "$fasta" ]]  || { err "file not found '$fasta' (-f)"; exit 1; }
[[ -f "$go_owl" ]] || { err "file not found '$go_owl' (-g)"; exit 1; }

# Classic validation
if [[ "$mode" == "classic" || "$mode" == "both" ]]; then
    [[ -z "$diamond_db" ]] && { err "missing required argument -d <db>"; exit 1; }
    [[ -z "$mongo_db" ]]   && { err "missing required argument --mongo-db <name>"; exit 1; }

    if ! [[ "$threads" =~ ^[1-9][0-9]*$ ]]; then
        err "invalid value for -t <threads>, must be a positive integer (got '$threads')"
        exit 1
    fi

    if ! [[ "$mongo_port" =~ ^[0-9]+$ ]]; then
        err "invalid value for --mongo-port <port>, must be a positive integer (got '$mongo_port')"
        exit 1
    fi

    if [[ -f "$diamond_db" ]]; then
        :
    elif [[ -f "${diamond_db}.dmnd" ]]; then
        diamond_db="${diamond_db}.dmnd"
    else
        err "file not found '$diamond_db' (-d)"
        exit 1
    fi

    [[ -f "$script_classic" ]] || { err "file not found '$script_classic' (classic script)"; exit 1; }
fi

# New validation
if [[ "$mode" == "new" || "$mode" == "both" ]]; then
    [[ -z "$structure_dir" ]] && { err "missing required argument -s <dir>"; exit 1; }
    [[ -z "$weights_dir" ]]   && { err "missing required argument -w <dir>"; exit 1; }

    [[ -d "$structure_dir" ]] || { err "directory not found '$structure_dir' (-s)"; exit 1; }
    [[ -d "$weights_dir" ]]   || { err "directory not found '$weights_dir' (-w)"; exit 1; }

    [[ -f "$script_new" ]] || { err "file not found '$script_new' (new script)"; exit 1; }
fi

# -----------------------------
# Output
# -----------------------------
classic_out="$outdir/classic"
new_out="$outdir/new"

if [[ -d "$outdir" && "$force" -ne 1 ]]; then
    err "output directory exists '$outdir' (use --force)"
    exit 1
fi

[[ -d "$outdir" ]] && run rm -rf "$outdir"
run mkdir -p "$outdir"

if [[ "$dry_run" -eq 0 ]] && [[ ! -w "$outdir" ]]; then
    err "output directory is not writable '$outdir'"
    exit 1
fi

# -----------------------------
# Commands
# -----------------------------
classic_cmd=(
    bash "$script_classic"
    -f "$fasta"
    -d "$diamond_db"
    -g "$go_owl"
    -o "$classic_out"
    -t "$threads"
    -m "$mongo_host"
    -P "$mongo_port"
    -D "$mongo_db"
)

new_cmd=(
    bash "$script_new"
    -f "$fasta"
    -g "$go_owl"
    -o "$new_out"
    -s "$structure_dir"
    -w "$weights_dir"
)

[[ "$dry_run" -eq 1 ]] && classic_cmd+=(--dry-run) && new_cmd+=(--dry-run)
[[ "$verbose" -eq 1 ]] && classic_cmd+=(--verbose) && new_cmd+=(--verbose)

# -----------------------------
# Execute
# -----------------------------
if [[ "$mode" == "classic" ]]; then
    run "${classic_cmd[@]}"

elif [[ "$mode" == "new" ]]; then
    run "${new_cmd[@]}"

else
    if [[ "$exec_mode" == "parallel" && "$dry_run" -eq 0 ]]; then
        echo "=== Running Argot3 - Classic Model ==="
        run "${classic_cmd[@]}" > "$outdir/classic.log" 2>&1 & pid1=$!
        echo "=== Running Argot3 - New Model ======="
        run "${new_cmd[@]}" > "$outdir/new.log" 2>&1 & pid2=$!

        fail=0
        wait $pid1 || fail=1
        wait $pid2 || fail=1
        [[ $fail -eq 1 ]] && exit 1

    else
        run "${classic_cmd[@]}"
        run "${new_cmd[@]}"
    fi
fi