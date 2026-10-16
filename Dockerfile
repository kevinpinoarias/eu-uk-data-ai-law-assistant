# The demo service on a plain CPU (no graphics card needed): BGE-M3 embeds a question in about 0.12 s on a
# CPU, the chunk vectors are precomputed, and the answer model is called over the network.
#
# Built and run on 15 October 2026 (1.74 GB; the build downloads the 2.3 GB BGE-M3 weights). The chunks and the
# saved vectors are git-ignored: build with them present locally, or let the deploy workflow unpack the data
# bundle (scripts/make_data_bundle.py) first.
#   docker build -t law-assistant .
#   docker run -p 8000:8000 -e GEMINI_API_KEY=... law-assistant
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HUB_DISABLE_TELEMETRY=1
WORKDIR /app

# Dependencies first so they are cached between code changes. The CPU build of PyTorch is far smaller than the
# default one. The project is installed in editable mode so that its data paths resolve under /app.
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
# The last command imports the libraries so that a version mismatch fails the build now, not at start-up.
RUN pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install -e ".[open-embeddings]" \
 && python -c "from transformers import AutoModel, AutoTokenizer; import numpy"

# The model weights (BAAI/bge-m3, MIT licence, 2.27 GB) are downloaded once at build time.
RUN python -m law_assistant.retrieval.get_bge

# What the service reads: the page, the facts table, the chunks and the saved chunk vectors.
COPY web ./web
COPY facts ./facts
COPY data/chunks ./data/chunks
COPY data/indexes/bge-m3.f32 data/indexes/bge-m3.keys.json ./data/indexes/

# Behind a hosting platform's proxy the client address comes from X-Forwarded-For (used by the rate limit).
ENV TRUST_PROXY=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["python", "-m", "law_assistant.serve", "--host", "0.0.0.0", "--port", "8000"]
