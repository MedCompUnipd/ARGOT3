# ARGOT3 — Quick Start

ARGOT3 annotates protein sequences with Gene Ontology terms using a classic sequence-similarity pipeline, a deep learning pipeline, or both combined.

For full documentation see [HERE](DOCUMENTATION.md).

---

## 1. Download and unpack the resource bundle

Download the resource bundle from [here](#) *(link to be added)*, then unpack it:

```
tar -xzf argot3_resource_bundle.tar.gz
```

---

## 2. Get the container image

**Pre-built (recommended)** — pull directly from the GitHub Container Registry ([package page](https://github.com/MedCompUnipd/ARGOT3/pkgs/container/argot3)):

```
# Docker
docker pull ghcr.io/medcompunipd/argot3:<version>
docker tag ghcr.io/medcompunipd/argot3:<version> argot3

# Singularity
singularity build argot3.sif docker://ghcr.io/medcompunipd/argot3:<version>
```

> **Note:** building the Singularity image may require several tens of GB of temporary disk space. Set `SINGULARITY_TMPDIR` and `SINGULARITY_CACHEDIR` to change default directories if needed.

**Build locally** — from the repository source:

```
# Docker
docker build -t argot3 .

# Singularity (requires Docker image built above)
singularity build argot3.sif docker-daemon://argot3:latest
```

---

## 3. Start MongoDB

The script auto-detects Docker or Singularity. Use `-r docker` or `-r singularity` to override. The database name loaded from the dump is `ARGOT_DB` — use this value for `--mongo-db` when running the pipeline.

```
./run_mongodb.sh -f /path/to/argot3_resource_bundle/dump/
```

> **Warning:** The database dump is large. Restoring it requires ~100 GB of free disk space. Persistent data is stored in `$HOME/mongo_data` by default — make sure that filesystem has enough space, or specify a different location with `-d`.

Common options:

```
# Custom runtime, data directory and port
./run_mongodb.sh \
    -r singularity \
    -d /scratch/mongo_data \
    -p 27018 \
    -f /path/to/argot3_resource_bundle/dump/
```

MongoDB runs on port `27017` by default. If you change it with `-p`, pass the same port to the pipeline with `--mongo-port`.

---

## 4. Run the pipeline

Three volume mounts are required:

| Mount | Purpose |
|-------|---------|
| `/path/to/argot3_resource_bundle` → `/data` | Resource bundle |
| `/path/to/proteins.fasta` → `/input/proteins.fasta` | Input FASTA |
| `/path/to/output` → `/output` | Output directory |

The `-o` argument must point to a **non-existing subdirectory** inside the output mount (e.g. `/output/run1`). The pipeline creates it.

> **Singularity users:** commands below are identical — apply these substitutions:
>
> | Docker | Singularity |
> |--------|-------------|
> | `docker run` | `singularity run` |
> | `--gpus all` | `--nv` *(omit if no GPU)* |
> | `--network host` | *(omit — host network is default)* |
> | `-v src:dst` | `--bind src:dst` |
> | `-e VAR=val` | `--env VAR=val` |
> | `argot3` | `argot3.sif` |

### Run everything (both pipelines + merge)

```
docker run --gpus all --network host \
    -v /path/to/argot3_resource_bundle:/data \
    -v /path/to/proteins.fasta:/input/proteins.fasta \
    -v /path/to/output:/output \
    -e TORCH_HOME=/data/embeddings \
    argot3 \
    --mode all \
    --exec parallel \
    -f /input/proteins.fasta \
    -o /output/run1 \
    -g /data/go.owl \
    -d /data/uniprot_wGO.dmnd \
    -t 8 \
    --mongo-host localhost \
    --mongo-db ARGOT_DB \
    -s /data/structure \
    -w /data/weights
```

- `TORCH_HOME=/data/embeddings` points to the pre-downloaded ESM2 weights (avoids a ~2.5 GB download at runtime)
- `--exec parallel` runs both pipelines simultaneously; omit it (or use `--exec sequential`) to run them one after the other, which uses less memory

### Classic model only

```
docker run --network host \
    -v /path/to/argot3_resource_bundle:/data \
    -v /path/to/proteins.fasta:/input/proteins.fasta \
    -v /path/to/output:/output \
    argot3 \
    --mode classic \
    -f /input/proteins.fasta \
    -o /output/run1 \
    -g /data/go.owl \
    -d /data/uniprot_wGO.dmnd \
    -t 8 \
    --mongo-host localhost \
    --mongo-db ARGOT_DB
```

### New model only

```
docker run --gpus all \
    -v /path/to/argot3_resource_bundle:/data \
    -v /path/to/proteins.fasta:/input/proteins.fasta \
    -v /path/to/output:/output \
    -e TORCH_HOME=/data/embeddings \
    argot3 \
    --mode new \
    -f /input/proteins.fasta \
    -o /output/run1 \
    -g /data/go.owl \
    -s /data/structure \
    -w /data/weights
```

### Run both pipelines without merging

Use `--mode both` with the same arguments as `--mode all` — it runs both pipelines without the final merge. Results can be merged later with `--mode merge`.

### Merge existing outputs

Use this to merge results from a previous `--mode classic` and `--mode new` run, pointing `-o` to the same run directory. **The output directory must contain results from both models** (i.e. it must have been produced by prior `--mode classic` and `--mode new` runs with the same `-o` path).

```
docker run \
    -v /path/to/argot3_resource_bundle:/data \
    -v /path/to/output:/output \
    argot3 \
    --mode merge \
    -o /output/run1 \
    -g /data/go.owl
```

To apply taxonomic constraints, append these flags. `--species` is the NCBI taxonomy ID of the target organism (e.g. `9606` for human):

```
    --species 9606 \
    -T /data/taxonomy \
    -C /data/constraints
```