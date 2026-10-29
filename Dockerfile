FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# The requirements export includes hashes from uv.lock.
COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt \
    && groupadd --gid 10001 botkit \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent botkit

# Allowlist: runtime secrets and backups never enter image layers.
COPY app ./app
COPY migrations ./migrations
COPY main.py alembic.ini ./
COPY scripts/run.sh scripts/check_runtime.py ./scripts/
RUN chmod 0555 /app/scripts/run.sh

USER 10001:10001
CMD ["/app/scripts/run.sh"]
