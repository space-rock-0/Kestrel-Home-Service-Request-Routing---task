# Kestrel service-request router — CPU only, no API key, no paid call.
#
# Build from the project root:   docker build -t kestrel-router .
# Run with your data mounted:    docker run -p 8000:8000 -v "$(pwd)/data/input:/app/data/input" kestrel-router
#
# artifacts/model.joblib and artifacts/metrics.json are baked in by .dockerignore so the image
# boots on a clean machine with a working model. Mounting a volume over /app/artifacts HIDES them
# (Docker volumes shadow the image), so mount /app/data/input and let the service write its own
# artifacts, or mount artifacts somewhere else. decisions.md D12.

FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV KESTREL_HOST=0.0.0.0 \
    KESTREL_PORT=8000 \
    KESTREL_INPUT_DIR=/app/data/input \
    KESTREL_ARTIFACT_DIR=/app/artifacts \
    PYTHONUNBUFFERED=1

# Input data is a mount point. artifacts/ is deliberately NOT a volume: declaring it would shadow
# the model baked into the image and the service would answer 503 until something retrained.
VOLUME ["/app/data/input"]
EXPOSE 8000

# Verified locally against a running server: exit 0 when /api/health answers 200, exit 1 when
# nothing is listening. stderr is dropped so a failing probe does not fill the container log.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request as u,sys; sys.exit(0 if u.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else 1)" 2>/dev/null || exit 1

CMD ["python", "-m", "kestrel", "serve"]