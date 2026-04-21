# ARGOT3

ARGOT3 is a containerized pipeline for protein function annotation using Gene Ontology (GO) terms. It supports two annotation strategies that can be run independently or together:

- **Classic model**: sequence similarity-based annotation using DIAMOND, MongoDB-backed GO annotations, and the Argot3 scoring engine
- **New model**: structure-informed deep learning annotation using ESM2 protein embeddings and trained neural network weights

---

## Repository Structure

```
ARGOT3.0/
├── Dockerfile                  # Container definition (NVIDIA TF base + dependencies)
├── entrypoint.sh               # Main pipeline entry point
├── run_mongodb.sh              # Host-side MongoDB setup script (Docker or Singularity)
├── bin/
│   ├── diamond                 # DIAMOND binary
│   └── Argot3-1.0.jar          # Argot3 Java scoring engine
└── src/
    ├── run_classic_model.sh    # Classic pipeline runner
    ├── run_new_model.sh        # New model pipeline runner
    ├── classic_model/          # Python scripts for the classic pipeline
    └── new_model/              # Python scripts for the new model pipeline
```

---

## Requirements

The following data files and directories are expected to be available on the host and mounted into the container (e.g. via `-v /data:/data`):

```
/data/                          # Host directory mounted into the container
├── proteins.fasta              # Input protein sequences (FASTA format)
├── go.owl                      # Gene Ontology file (OWL format)
│
├── uniprot.dmnd                # DIAMOND database          [classic model]
│
├── structures/                 # Protein structure files   [new model]
├── weights/                    # Pre-trained model weights [new model]
└── embeddings/                 # ESM2 model weights cache  [new model]
    └── hub/
        └── checkpoints/
            ├── esm2_t33_650M_UR50D.pt
            └── esm2_t33_650M_UR50D-contact-regression.pt
```

The `embeddings/` directory holds the pre-downloaded ESM2 model weights used by `fair-esm` at runtime. Without it, the pipeline will attempt to download ~2.5 GB at runtime. Pass it to the container via `TORCH_HOME` (see examples below).

---

## MongoDB Setup

MongoDB must be running before the pipeline is invoked. Use `run_mongodb.sh` to start a MongoDB instance and optionally restore a dump archive.

> **Note:** `run_mongodb.sh` is a host-side script and is not part of the Docker container.

### Usage

```bash
./run_mongodb.sh [options]

Options:
  -r <runtime>    Container runtime: docker | singularity (default: auto-detect)
  -n <name>       Container/instance name (default: argot-mongodb)
  -p <port>       MongoDB port (default: 27017)
  -d <data_dir>   Host directory for persistent data (default: ~/mongo_data)
  -f <dump_file>  MongoDB archive dump to restore (optional)
  -i <sif>        Singularity SIF image (optional, default: docker://mongo:7)
  --force         Remove existing data directory before starting
```

### Examples
Start MongoDB (auto-detected) and restore a dump:
```bash
./run_mongodb.sh -f /path/to/argot.dump
```

Use a custom port and container name:
```bash
./run_mongodb.sh -n my-mongo -p 27018 -f /path/to/argot.dump
```

#### Use Singularity on HPC with a pre-built SIF

For HPC environments without Docker, use `run_mongodb.sh` with `-r singularity` (the software auto-detects Singularity if Docker is missing). It is recommended to provide a pre-built SIF image to avoid pulling from Docker Hub on compute nodes:

```bash
singularity build mongo.sif docker://mongo:7
```

```bash
./run_mongodb.sh -r singularity -i /path/to/mongo.sif -f /path/to/argot.dump
```

> **Note:** The dump archive must be in MongoDB archive format (created with `mongodump --archive`).

### Connecting ARGOT3 to MongoDB

*TO DO*

---

## Building the Docker Image

```bash
docker build -t argot3 .
```

The image is based on `nvcr.io/nvidia/tensorflow:24.01-tf2-py3` and includes:
- Java 17 (for Argot3.jar)
- PyTorch with CUDA 12.1 support
- Python packages: `pymongo`, `owlready2`, `fair-esm`, `biopython`, `networkx`, and others

---

## Running the Pipeline

The main entry point is `entrypoint.sh`, which is set as the Docker `ENTRYPOINT`.

### Usage

```
docker run [docker options] argot3 --mode <classic|new|both> [options]

Execution mode:
  --mode <mode>          classic   Run the DIAMOND + Argot3 pipeline
                         new       Run the structure-based deep learning pipeline
                         both      Run both pipelines

  --exec <mode>          Execution strategy when --mode=both:
                         sequential (default)   Run classic then new
                         parallel               Run classic and new in parallel

Shared arguments:
  -f <fasta>             Input protein FASTA file
  -o <outdir>            Output directory
  -g <go.owl>            Gene Ontology file (OWL format)

Classic model arguments:
  -d <db>                DIAMOND database (prefix or .dmnd file)
  -t <threads>           Number of threads for DIAMOND (default: 1)
  --mongo-db <name>      MongoDB database name
  --mongo-host <host>    MongoDB host (default: mongodb)
  --mongo-port <port>    MongoDB port (default: 27017)

New model arguments:
  -s <dir>               Structure directory
  -w <dir>               Weights directory

Execution flags:
  --dry-run              Print commands without executing them
  --verbose              Print commands as they are executed
  --force                Overwrite existing output directory
```

### Examples

Run the classic model:
```bash
docker run --network host \
    -v /data:/data \
    argot3 \
    --mode classic \
    -f /data/proteins.fasta \
    -o /data/output \
    -g /data/go.owl \
    -d /data/uniprot.dmnd \
    -t 8 \
    --mongo-host localhost \
    --mongo-db ARGOT_DB
```

Run the new model:
```bash
docker run --gpus all --network host \
    -v /data:/data \
    -e TORCH_HOME=/data/embeddings \
    argot3 \
    --mode new \
    -f /data/proteins.fasta \
    -o /data/output \
    -g /data/go.owl \
    -s /data/structures \
    -w /data/weights
```

Run both pipelines in parallel:
```bash
docker run --gpus all --network host \
    -v /data:/data \
    -e TORCH_HOME=/data/embeddings \
    argot3 \
    --mode both \
    --exec parallel \
    -f /data/proteins.fasta \
    -o /data/output \
    -g /data/go.owl \
    -d /data/uniprot.dmnd \
    -t 8 \
    --mongo-host localhost \
    --mongo-db ARGOT_DB \
    -s /data/structures \
    -w /data/weights
```

When running with `--mode both --exec parallel`, each pipeline writes its logs to `<outdir>/classic.log` and `<outdir>/new.log`.

---

## Output Structure

### Classic model (`--mode classic`)

```
<outdir>/classic/
├── input/
│   ├── proteins_list.fasta         # Validated input sequences
│   └── argot_in.txt                # Argot3 input file
├── output/
│   ├── diamond_raw.blastp          # Raw DIAMOND output
│   ├── diamond_clean.blastp        # Filtered DIAMOND output
│   ├── argot_out.txt               # Argot3 raw scores
│   ├── predictions_raw.tsv         # Unpropagated predictions
│   └── predictions_prop.tsv        # Propagated predictions
└── predictions/
    ├── unpropagated.tsv            # Final unpropagated output
    └── propagated.tsv              # Final propagated output
```

### New model (`--mode new`)

```
<outdir>/new/
├── data/
│   ├── proteins_list.fasta         # Validated input sequences
│   ├── proteins_list.txt           # Protein IDs
│   ├── embeddings/                 # Per-protein TF embeddings (generated at runtime)
│   ├── cco_batch.txt               # Cellular Component predictions
│   ├── mfo_batch.txt               # Molecular Function predictions
│   ├── bpo_batch.txt               # Biological Process predictions
│   ├── prediction_raw.txt          # Joined unpropagated predictions
│   └── prediction_propagated.txt   # Propagated predictions
└── predictions/
    ├── unpropagated.tsv            # Final unpropagated output
    └── propagated.tsv              # Final propagated output
```

When running `--mode both`, outputs are placed in `<outdir>/classic/` and `<outdir>/new/` respectively.