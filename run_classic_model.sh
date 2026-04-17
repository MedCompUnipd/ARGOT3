#!/usr/bin/env bash

set -euo pipefail

# -----------------------------
# Error and warning handler
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
# Default values
# -----------------------------
threads=1
mongodb_host="localhost"
mongodb_db=""

diamond_bin="${diamond_bin:-diamond}"
argot_jar="${argot_jar:-/app/bin/Argot3-1.0.jar}"
src_dir="${src_dir:-/app/src/classic_model}"

# -----------------------------
# Usage
# -----------------------------
usage() {
    echo "Argot3 - CLASSIC MODEL"
    echo
    echo "Usage:"
    echo "  $0 -f <fasta> -d <db> -g <go.owl> -o <outdir> -D <db_name> [options]"
    echo
    echo "Required arguments:"
    echo "  -f <fasta>        Input protein FASTA file"
    echo "  -d <db>           DIAMOND database (prefix or .dmnd file)"
    echo "  -g <go.owl>       Gene Ontology file (OWL format)"
    echo "  -o <outdir>       Output directory"
    echo "  -D <db_name>      MongoDB database name (e.g. ARGOT_NEW)"
    echo
    echo "Optional arguments:"
    echo "  -t <threads>      Number of threads to use for DIAMOND (default: 1)"
    echo "  -m <host>         MongoDB host (default: localhost)"
    echo "  -x <diamond>      Path to DIAMOND binary (default: diamond in PATH)"
    echo "  -a <argot.jar>    Path to Argot3 JAR (default: /app/bin/Argot3-1.0.jar)"
    echo "  -s <src_dir>      Path to pipeline scripts (default: /app/src/classic_model)"
    echo
    echo "Execution flags:"
    echo "      --dry-run     Print commands without executing them"
    echo "      --verbose     Print commands as they are executed"
    echo "      --force       Overwrite existing output directory"
    echo "  -h                Show this help message and exit"
    echo
    exit 1
}

# -----------------------------
# Parse args: handle long options
# before getopts, then strip them
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
# -> replace $@ with all elements of args or with nothing if args is empty

input_fasta=""
diamond_db=""
go_owl=""
outdir=""

while getopts ":f:d:g:o:t:m:D:x:a:s:h" opt; do
    case $opt in
        f) input_fasta=$OPTARG ;;
        d) diamond_db=$OPTARG ;;
        g) go_owl=$OPTARG ;;
        o) outdir=$OPTARG ;;
        t) threads=$OPTARG ;;
        m) mongodb_host=$OPTARG ;;
        D) mongodb_db=$OPTARG ;;
        x) diamond_bin=$OPTARG ;;
        a) argot_jar=$OPTARG ;;
        s) src_dir=$OPTARG ;;
        h) usage ;;
        \?) err "invalid option -$OPTARG"; usage ;;
        :) err "option -$OPTARG requires an argument."; usage ;;
    esac
done
shift $((OPTIND - 1))

# -----------------------------
# Validate arguments
# -----------------------------
missing=0
[[ -z "$input_fasta" ]] && { err "missing -f <fasta>"; missing=1; }
[[ -z "$diamond_db" ]]  && { err "missing -d <db>"; missing=1; }
[[ -z "$go_owl" ]]      && { err "missing -g <go.owl>"; missing=1; }
[[ -z "$outdir" ]]      && { err "missing -o <outdir>"; missing=1; }
[[ -z "$mongodb_db" ]]  && { err "missing -D <db_name>"; missing=1; }

[[ $missing -eq 1 ]] && { echo; usage; }

# Validate threads is a positive integer
if ! [[ "$threads" =~ ^[1-9][0-9]*$ ]]; then
    err "-t <threads> must be a positive integer, got '$threads'"
    exit 1
fi

# DIAMOND DB flexible handling
if [[ -f "$diamond_db" ]]; then
    :
elif [[ -f "${diamond_db}.dmnd" ]]; then
    diamond_db="${diamond_db}.dmnd"
else
    err "DIAMOND DB $diamond_db not found"
    exit 1
fi

[[ -f "$input_fasta" ]] || { err "FASTA file $input_fasta not found"; exit 1; }
[[ -f "$go_owl" ]]      || { err "GO file $go_owl not found"; exit 1; }

command -v "$diamond_bin" >/dev/null 2>&1 || { err "diamond $diamond_bin not found"; exit 1; }
command -v python3       >/dev/null 2>&1  || { err "python3 not found"; exit 1; }
command -v java          >/dev/null 2>&1  || { err "java not found"; exit 1; }

[[ -f "$argot_jar" ]] || { err "Argot3 JAR $argot_jar not found"; exit 1; }

[[ -d "$src_dir" ]] || { err "src_dir $src_dir not found"; exit 1; }
for script in \
    check_fasta.py \
    clean_blastp.py \
    new_blastp_to_argot_inp.py \
    in-cafa_format.py \
    propagate.py \
    format_out.py \
    owlLibrary3.py
do
    [[ -f "$src_dir/$script" ]] || {
        err "missing script $script in $src_dir"
        exit 1
    }
done

# -----------------------------
# Directories
# -----------------------------
# Handle existing output directory
if [[ -d "$outdir" ]]; then
    if [[ "$force" -eq 1 ]]; then
        warn "output directory exists, cleaning $outdir"
        run rm -rf "$outdir"
    else
        err "output directory $outdir already exists"
        err "use --force to overwrite or choose a different -o <outdir>"
        exit 1
    fi
fi

run mkdir -p "$outdir"

# Validate writability only when not in dry-run mode
if [[ "$dry_run" -eq 0 ]] && [[ ! -w "$outdir" ]]; then
    err "output dir $outdir not writable"
    exit 1
fi

input_dir="$outdir/input"
output_dir="$outdir/output"
preds_dir="$outdir/predictions"

run mkdir -p "$input_dir" "$output_dir" "$preds_dir"

# -----------------------------
# Pipeline
# -----------------------------
# Print configuration
echo
echo "=== CONFIGURATION ==="
echo "  FASTA:            $input_fasta"
echo "  DIAMOND DB:       $diamond_db"
echo "  GO ontology:      $go_owl"
echo "  Output dir:       $outdir"
echo "  Threads:          $threads"
echo "  Mongo host:       $mongodb_host"
echo "  Mongo DB:         $mongodb_db"

# Run pipeline steps
echo
echo "=== RUNNING STEPS ==="
run python3 "$src_dir/check_fasta.py" -f "$input_fasta" -o "$input_dir/proteins_list.fasta"

run "$diamond_bin" blastp \
    -d "$diamond_db" \
    -q "$input_dir/proteins_list.fasta" \
    -o "$output_dir/diamond_raw.blastp" \
    -f 6 -b 5 -c 1 -k 1000 -p "$threads"

run python3 "$src_dir/clean_blastp.py" \
    -i "$output_dir/diamond_raw.blastp" \
    -o "$output_dir/diamond_clean.blastp"

run python3 "$src_dir/new_blastp_to_argot_inp.py" \
    -b "$output_dir/diamond_clean.blastp" \
    -m "$mongodb_host" \
    -d "$mongodb_db" \
    -c annots \
    -o "$input_dir/argot_in.txt"

run java -jar "$argot_jar" \
    -i "$input_dir/argot_in.txt" \
    -s "$mongodb_host" \
    -d "$mongodb_db" \
    -o "$output_dir/argot_out.txt" \
    -g "$go_owl" \
    -c goafreq

run python3 "$src_dir/in-cafa_format.py" \
    -i "$output_dir/argot_out.txt" \
    -v Argot3 \
    -o "$output_dir" \
    -f temporary

[[ "$dry_run" -eq 1 ]] || [[ -f "$output_dir/temporary_argot_out_in_cafa.txt" ]] || {
    err "expected CAFA output not found"
    exit 1
}
run mv "$output_dir/temporary_argot_out_in_cafa.txt" \
       "$output_dir/predictions_raw.tsv"

run python3 "$src_dir/propagate.py" \
    -i "$output_dir/predictions_raw.tsv" \
    -o "$output_dir/predictions_prop.tsv" \
    -g "$go_owl" \
    -p

run python3 "$src_dir/format_out.py" \
    -i "$output_dir/predictions_raw.tsv" \
    -o "$preds_dir/unpropagated.tsv" \
    -g "$go_owl"

run python3 "$src_dir/format_out.py" \
    -i "$output_dir/predictions_prop.tsv" \
    -o "$preds_dir/propagated.tsv" \
    -g "$go_owl"

echo "=== DONE ==="