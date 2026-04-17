FROM nvcr.io/nvidia/tensorflow:24.01-tf2-py3

# -----------------------------
# Metadata
# -----------------------------
LABEL org.opencontainers.image.authors="Michele Berselli <michele.berselli@unipd.it>, Emilio Ispano" \
      org.opencontainers.image.description="Argot3 pipeline container (DIAMOND + Argot + Python scripts)" \
      org.opencontainers.image.version="1.0"

# -----------------------------
# System dependencies
# -----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        openjdk-17-jre-headless \
        build-essential \
        libxml2-dev libxslt1-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Python dependencies
# -----------------------------
RUN pip3 install --no-cache-dir \
        pymongo \
        owlready2 \
        tqdm \
        fair-esm \
        requests \
        networkx \
        biopython \
        matplotlib \
        numpy \
        torch \
        torchvision \
        torchaudio

# -----------------------------
# Application layout
# -----------------------------
WORKDIR /app

# Binaries
COPY bin/ ./bin/
RUN chmod +x ./bin/diamond

# Scripts
COPY src/ ./src/

# Runners
COPY run_classic_model.sh run_new_model.sh ./
RUN chmod +x run_classic_model.sh run_new_model.sh

# Make binaries globally available
ENV PATH="/app/bin:${PATH}"

# Set other environment variables
ENV LC_ALL=C
ENV LANG=C
ENV PYTHONPATH=/app/src

# CMD
CMD ["bash"]