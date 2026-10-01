# Not yet built/tested -- no Docker available in the environment this was
# written in. Verify with `docker build .` locally before trusting this;
# flag anything that fails back so it can be fixed here.

FROM python:3.12-slim

# Keep Python from writing .pyc files / buffering stdout -- standard for
# containers, makes `docker logs` show output immediately rather than
# buffered.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements first so this layer only rebuilds when dependencies
# actually change, not on every code edit -- meaningfully faster rebuilds
# once this is part of a real dev loop.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user. Not optional for anything internet-facing.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

# Deliberately no --workers flag. data/mock_data.py holds admin-approval
# state (PENDING_CLUSTERS, APPROVAL_LOG) as plain in-process Python objects
# -- multiple workers means multiple independent copies of that state, and
# approvals silently becoming inconsistent depending on which worker
# handles a given request. Don't add --workers here until that's backed by
# a real shared datastore (SQLite/Postgres); see docker-compose.yml for the
# same constraint applied to replica count.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
