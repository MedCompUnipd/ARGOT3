FROM ubuntu:22.04

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
        python3 python3-pip \
        build-essential \
        libxml2-dev libxslt1-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Python dependencies
# -----------------------------
RUN pip3 install --no-cache-dir \
        pymongo \
        owlready2 \
        tqdm

# -----------------------------
# Application layout
# -----------------------------
WORKDIR /app

# Binaries
COPY bin/ ./bin/
RUN chmod +x ./bin/diamond

# Scripts
COPY src/ ./src/

# Main entrypoint
COPY run_step1.sh .
RUN chmod +x run_step1.sh

# Make binaries globally available
ENV PATH="/app/bin:${PATH}"

# Set other environment variables
ENV LC_ALL=C
ENV LANG=C
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PYTHONPATH=/app/src

# -----------------------------
# Entry point
# -----------------------------
ENTRYPOINT ["./run_step1.sh"]