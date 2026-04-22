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
src_dir="${src_dir:-/app/src/merging}"

a25=""
a30=""
outdir=""
species=0

go_owl=""
taxonomy_dir=""
constraints_dir=""

# -----------------------------
# Usage
# -----------------------------
usage() {
    echo "Argot3 - Merge Predictions"
    echo
    echo "Merge predictions from the classic model and the new model, with optional taxonomic constraints."
    echo
    echo "Usage:"
    echo "  $0 -d <res_classic> -t <res_new> -o <outdir> -g <go.owl> [options]"
    echo
    echo "Required arguments:"
    echo "  -d <dir>              Classic model results directory"
    echo "  -t <dir>              New model results directory"
    echo "  -o <dir>              Output directory"
    echo "  -g <go.owl>           Gene Ontology file (OWL format)"
    echo
    echo "Optional arguments:"
    echo "  -s <taxid>            NCBI taxon ID (enable constraints)"
    echo "  -T <dir>              Taxonomy directory (required if -s is set)"
    echo "  -C <dir>              Constraints directory (required if -s is set)"
    echo "  -S <src_dir>          Path to pipeline scripts (default: /app/src/merging)"
    echo
    echo "Execution flags:"
    echo "      --dry-run         Print commands without executing them"
    echo "      --verbose         Print commands as they are executed"
    echo "      --force           Overwrite existing output directory"
    echo "  -h                    Show this help message and exit"
    echo
    exit 1
}

# -----------------------------
# Parse long options
# -----------------------------
args=()
for arg in "$@"; do
    case $arg in
        --dry-run) dry_run=1 ;;
        --verbose) verbose=1 ;;
        --force) force=1 ;;
        --) ;;
        *) args+=("$arg") ;;
    esac
done
set -- "${args[@]+"${args[@]}"}"

# -----------------------------
# Parse short options
# -----------------------------
while getopts ":d:t:o:s:g:T:C:S:h" opt; do
    case $opt in
        d) a25=$OPTARG ;;
        t) a30=$OPTARG ;;
        o) outdir=$OPTARG ;;
        s) species=$OPTARG ;;
        g) go_owl=$OPTARG ;;
        T) taxonomy_dir=$OPTARG ;;
        C) constraints_dir=$OPTARG ;;
        S) src_dir=$OPTARG ;;
        h) usage ;;
        \?) err "unknown argument -$OPTARG"; usage ;;
        :) err "missing value for -$OPTARG"; usage ;;
    esac
done
shift $((OPTIND - 1))

# -----------------------------
# Validate
# -----------------------------
missing=0
[[ -z "$a25" ]]    && { err "missing required argument -d <res_classic>"; missing=1; }
[[ -z "$a30" ]]    && { err "missing required argument -t <res_new>"; missing=1; }
[[ -z "$outdir" ]] && { err "missing required argument -o <outdir>"; missing=1; }
[[ -z "$go_owl" ]] && { err "missing required argument -g <go.owl>"; missing=1; }

[[ $missing -eq 1 ]] && { echo; usage; }

[[ -d "$a25" ]] || { err "directory not found '$a25' (-d)"; exit 1; }
[[ -d "$a30" ]] || { err "directory not found '$a30' (-t)"; exit 1; }
[[ -f "$go_owl" ]] || { err "file not found '$go_owl' (-g)"; exit 1; }

[[ -d "$src_dir" ]] || { err "directory not found '$src_dir' (-S)"; exit 1; }

command -v python3 >/dev/null 2>&1 || { err "required executable not found 'python3'"; exit 1; }

if ! [[ "$species" =~ ^[0-9]+$ ]]; then
    err "invalid value for -s <taxid>, must be a positive integer (got '$species')"
    exit 1
fi

# Only require taxonomy/constraints if species is specified
if [[ "$species" -ne 0 ]]; then
    [[ -z "$taxonomy_dir" ]]    && { err "missing required argument -T <taxonomy_dir> (required when using -s)"; exit 1; }
    [[ -z "$constraints_dir" ]] && { err "missing required argument -C <constraints_dir> (required when using -s)"; exit 1; }

    [[ -d "$taxonomy_dir" ]]    || { err "directory not found '$taxonomy_dir' (-T)"; exit 1; }
    [[ -d "$constraints_dir" ]] || { err "directory not found '$constraints_dir' (-C)"; exit 1; }
fi

for script in merge.py slim.py apply_constr_web.py; do
    [[ -f "$src_dir/$script" ]] || {
        err "file not found '$src_dir/$script' (required pipeline script)"
        exit 1
    }
done

[[ -f "$a25/predictions/unpropagated.tsv" ]] || { err "file not found '$a25/predictions/unpropagated.tsv' (-d)"; exit 1; }
[[ -f "$a30/predictions/unpropagated.tsv" ]] || { err "file not found '$a30/predictions/unpropagated.tsv' (-t)"; exit 1; }
[[ -f "$a25/predictions/propagated.tsv" ]] || { err "file not found '$a25/predictions/propagated.tsv' (-d)"; exit 1; }
[[ -f "$a30/predictions/propagated.tsv" ]] || { err "file not found '$a30/predictions/propagated.tsv' (-t)"; exit 1; }

# -----------------------------
# Output directory
# -----------------------------
if [[ -d "$outdir" ]]; then
    if [[ "$force" -eq 1 ]]; then
        warn "output directory exists, cleaning '$outdir'"
        run rm -rf "$outdir"
    else
        err "output directory exists '$outdir' (use --force)"
        exit 1
    fi
fi

run mkdir -p "$outdir"

if [[ "$dry_run" -eq 0 ]] && [[ ! -w "$outdir" ]]; then
    err "output directory is not writable '$outdir'"
    exit 1
fi

run mkdir -p "$outdir/final"

# -----------------------------
# Config print
# -----------------------------
echo
echo "=== Running Argot3 Merge =========="
echo "=== CONFIGURATION ================="
echo "  Classic model:   $a25"
echo "  New model:       $a30"
echo "  Output dir:      $outdir"
echo "  GO ontology:     $go_owl"
if [[ "$species" -ne 0 ]]; then
    echo "  Species:         $species"
    echo "  Taxonomy dir:    $taxonomy_dir"
    echo "  Constraints dir: $constraints_dir"
fi
echo "  Source dir:      $src_dir"

# -----------------------------
# Pipeline
# -----------------------------
echo
echo "=== STEPS ========================="

if [[ "$species" -eq 0 ]]; then

    echo "Merging unpropagated..."
    run python3 "$src_dir/merge.py" \
        -d "$a25/predictions/unpropagated.tsv" \
        -t "$a30/predictions/unpropagated.tsv" \
        -o "$outdir/unpropagated.tsv"

    echo "Merging propagated..."
    run python3 "$src_dir/merge.py" \
        -d "$a25/predictions/propagated.tsv" \
        -t "$a30/predictions/propagated.tsv" \
        -o "$outdir/propagated.tsv"

    run python3 "$src_dir/slim.py" \
        -i "$outdir/propagated.tsv" \
        -g "$go_owl" \
        -s "$outdir/final/predictions_slim.tsv" \
        -f "$outdir/final/predictions_full.tsv"

else

    echo "Applying taxonomic constraints..."
    # Classic model
    run python3 "$src_dir/apply_constr_web.py" \
        -p "$a25/predictions/unpropagated.tsv" \
        -t "$taxonomy_dir" \
        -c "$constraints_dir" \
        -s "$species" \
        -o "$a25/predictions/unprop_filt.tsv"

    run python3 "$src_dir/apply_constr_web.py" \
        -p "$a25/predictions/propagated.tsv" \
        -t "$taxonomy_dir" \
        -c "$constraints_dir" \
        -s "$species" \
        -o "$a25/predictions/prop_filt.tsv"

    # New model
    run python3 "$src_dir/apply_constr_web.py" \
        -p "$a30/predictions/unpropagated.tsv" \
        -t "$taxonomy_dir" \
        -c "$constraints_dir" \
        -s "$species" \
        -o "$a30/predictions/unprop_filt.tsv"

    run python3 "$src_dir/apply_constr_web.py" \
        -p "$a30/predictions/propagated.tsv" \
        -t "$taxonomy_dir" \
        -c "$constraints_dir" \
        -s "$species" \
        -o "$a30/predictions/prop_filt.tsv"

    echo "Merging unfiltered..."
    run python3 "$src_dir/merge.py" \
        -d "$a25/predictions/unpropagated.tsv" \
        -t "$a30/predictions/unpropagated.tsv" \
        -o "$outdir/unpropagated.tsv"

    run python3 "$src_dir/merge.py" \
        -d "$a25/predictions/propagated.tsv" \
        -t "$a30/predictions/propagated.tsv" \
        -o "$outdir/propagated.tsv"

    run python3 "$src_dir/slim.py" \
        -i "$outdir/propagated.tsv" \
        -g "$go_owl" \
        -s "$outdir/final/predictions_unfiltered_slim.tsv" \
        -f "$outdir/final/predictions_unfiltered_full.tsv"

    echo "Merging filtered..."
    run python3 "$src_dir/merge.py" \
        -d "$a25/predictions/unprop_filt.tsv" \
        -t "$a30/predictions/unprop_filt.tsv" \
        -o "$outdir/unpropagated_filtered.tsv"

    run python3 "$src_dir/merge.py" \
        -d "$a25/predictions/prop_filt.tsv" \
        -t "$a30/predictions/prop_filt.tsv" \
        -o "$outdir/propagated_filtered.tsv"

    run python3 "$src_dir/slim.py" \
        -i "$outdir/propagated_filtered.tsv" \
        -g "$go_owl" \
        -s "$outdir/final/predictions_filtered_slim.tsv" \
        -f "$outdir/final/predictions_filtered_full.tsv"
fi

echo
echo "=== DONE ==========================="