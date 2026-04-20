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
src_dir="${src_dir:-/app/src/new_model}"

structure_dir=""
weights_dir=""
go_owl=""

# -----------------------------
# Usage
# -----------------------------
usage() {
    echo "Argot3 - New Model"
    echo
    echo "Run the Argot3 structure-based deep learning pipeline using embeddings, structure data, and trained model weights."
    echo
    echo "Usage:"
    echo "  $0 -f <fasta> -o <outdir> -s <structure_dir> -w <weights_dir> -g <go.owl> [options]"
    echo
    echo "Required arguments:"
    echo "  -f <fasta>             Input protein FASTA file"
    echo "  -o <outdir>            Output directory"
    echo "  -s <dir>               Structure directory"
    echo "  -w <dir>               Weights directory"
    echo "  -g <go.owl>            Gene Ontology file (OWL format)"
    echo
    echo "Optional arguments:"
    echo "  -S <src_dir>           Path to pipeline scripts (default: /app/src/new_model)"
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
args=()
for arg in "$@"; do
    case $arg in
        --dry-run) dry_run=1 ;;
        --verbose) verbose=1 ;;
        --force) force=1 ;;
        --) ;;  # ignore bare --
        *) args+=("$arg") ;;
    esac
done
set -- "${args[@]+"${args[@]}"}"

fasta=""
outdir=""

while getopts ":f:o:s:w:g:S:h" opt; do
    case $opt in
        f) fasta=$OPTARG ;;
        o) outdir=$OPTARG ;;
        s) structure_dir=$OPTARG ;;
        w) weights_dir=$OPTARG ;;
        g) go_owl=$OPTARG ;;
        S) src_dir=$OPTARG ;;
        h) usage ;;
        \?) err "unknown argument '-$OPTARG'"; usage ;;
        :) err "missing required value for -$OPTARG"; usage ;;
    esac
done
shift $((OPTIND - 1))

# -----------------------------
# Validate
# -----------------------------
missing=0
[[ -z "$fasta" ]]         && { err "missing required argument -f <fasta>"; missing=1; }
[[ -z "$go_owl" ]]        && { err "missing required argument -g <go.owl>"; missing=1; }
[[ -z "$outdir" ]]        && { err "missing required argument -o <outdir>"; missing=1; }
[[ -z "$structure_dir" ]] && { err "missing required argument -s <dir>"; missing=1; }
[[ -z "$weights_dir" ]]   && { err "missing required argument -w <dir>"; missing=1; }

[[ $missing -eq 1 ]] && { echo; usage; }

[[ -f "$fasta" ]]         || { err "file not found '$fasta' (-f)"; exit 1; }
[[ -d "$structure_dir" ]] || { err "directory not found '$structure_dir' (-s)"; exit 1; }
[[ -d "$weights_dir" ]]   || { err "directory not found '$weights_dir' (-w)"; exit 1; }
[[ -f "$go_owl" ]]        || { err "file not found '$go_owl' (-g)"; exit 1; }

[[ -d "$src_dir" ]]       || { err "directory not found '$src_dir' (-S)"; exit 1; }
for script in \
    check_fasta.py \
    extract.py \
    get_fastas_uniprot.py \
    convert_to_tf.py \
    predict_batch.py \
    join.py \
    propagate.py \
    format_out.py \
    models.py \
    owlLibrary3.py
do
    [[ -f "$src_dir/$script" ]] || {
        err "file not found '$src_dir/$script' (required pipeline script)"
        exit 1
    }
done

command -v python3 >/dev/null 2>&1 || { err "required executable not found 'python3'"; exit 1; }

# -----------------------------
# Output dir
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

data="$outdir/data"
preds="$outdir/predictions"

run mkdir -p "$outdir" 

if [[ "$dry_run" -eq 0 ]] && [[ ! -w "$outdir" ]]; then
    err "output directory is not writable '$outdir'"
    exit 1
fi

run mkdir -p "$data" "$preds"

# -----------------------------
# Pipeline
# -----------------------------
echo
echo "=== CONFIGURATION ==="
echo "  FASTA:            $fasta"
echo "  Output dir:       $outdir"
echo "  Structure dir:    $structure_dir"
echo "  Weights dir:      $weights_dir"
echo "  GO ontology:      $go_owl"
echo "  Source dir:       $src_dir"

echo
echo "=== RUNNING STEPS ==="

run python3 "$src_dir/check_fasta.py" \
    -f "$fasta" \
    -o "$data/proteins_list.fasta"

run bash -c "set -o pipefail; grep '>' '$data/proteins_list.fasta' | cut -d' ' -f1 | sort -u | sed 's/>//' > '$data/proteins_list.txt'"

run python3 "$src_dir/extract.py" \
    esm2_t33_650M_UR50D \
    "$data/proteins_list.fasta" \
    "$data/torch_embeddings" \
    --repr_layers 33 --include per_tok

run bash -c "set -o pipefail; ls -1 '$data/torch_embeddings' | cut -d'.' -f1 | sort -u > '$data/embedded_prots.txt'"

if [[ "$dry_run" -eq 0 ]]; then

    n_total=$(wc -l < "$data/proteins_list.txt")
    n_embedded=$(wc -l < "$data/embedded_prots.txt")

    if [[ "$n_total" -ne "$n_embedded" ]]; then
        warn "re-embedding missing proteins"

        run bash -c "set -o pipefail; comm -13 \"$data/embedded_prots.txt\" \"$data/proteins_list.txt\" > \"$data/without_embeddings.txt\""

        run python3 "$src_dir/get_fastas_uniprot.py" \
            -i "$data/without_embeddings.txt" \
            -u "$data/proteins_list.fasta" \
            -o "$data/without_embeddings.fasta"

        run python3 "$src_dir/check_fasta.py" \
            -f "$data/without_embeddings.fasta" \
            -o "$data/without_embeddings_clean.fasta"

        run python3 "$src_dir/extract.py" \
            esm2_t33_650M_UR50D \
            "$data/without_embeddings_clean.fasta" \
            "$data/torch_embeddings" \
            --repr_layers 33 --include per_tok --nogpu
    fi

fi

run python3 "$src_dir/convert_to_tf.py" \
    -e "$data/torch_embeddings" \
    -o "$data/embeddings"

run rm -rf "$data/torch_embeddings"

run python3 "$src_dir/predict_batch.py" \
    -l "$data/proteins_list.txt" \
    -e "$data/embeddings" \
    -o "$data" \
    -b 16 \
    -s "$structure_dir" \
    -w "$weights_dir"

run python3 "$src_dir/join.py" \
    -c "$data/cco_batch.txt" \
    -m "$data/mfo_batch.txt" \
    -b "$data/bpo_batch.txt" \
    -o "$data/prediction_raw.txt"

run python3 "$src_dir/propagate.py" \
    -i "$data/prediction_raw.txt" \
    -o "$data/prediction_propagated.txt" \
    -g "$go_owl"

run python3 "$src_dir/format_out.py" \
    -i "$data/prediction_raw.txt" \
    -g "$go_owl" \
    -o "$preds/unpropagated.tsv"

run python3 "$src_dir/format_out.py" \
    -i "$data/prediction_propagated.txt" \
    -g "$go_owl" \
    -o "$preds/propagated.tsv"

echo
echo "=== DONE ==="