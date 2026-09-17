# ---- Builder: install deps into an isolated prefix ----
FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes --prefix=/install -r requirements.txt



# ---- Runtime: clean image, copy only the installed packages ----
FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Where the gunicorn workers write their memory-mapped metric files. Without
# it, prometheus_client keeps counters in process memory and a scrape returns
# whichever of the two workers answered — a graph that appears to go backwards
# under load. Declared as an env var because that variable being set is what
# switches the library into multiprocess mode; see app/metrics.py.
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus-multiproc

# One RUN, two facts: the unprivileged user, and a directory it can write to.
# Created here rather than left to the application because the container runs
# non-root and cannot mkdir under a root-owned /tmp entry at start-up.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /tmp/prometheus-multiproc \
    && chown appuser:appuser /tmp/prometheus-multiproc
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ ./app/
COPY gunicorn.conf.py .
ARG GIT_SHA=dev
ENV APP_VERSION=${GIT_SHA}
LABEL org.opencontainers.image.revision=${GIT_SHA} \
      org.opencontainers.image.source="https://github.com/myloo23/MilanProjA-Szakdoga" \
      org.opencontainers.image.title="ProjectA backend"
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app.app:app"]