FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Tokyo

WORKDIR /app

COPY jobcan_kintai/pyproject.toml /app/
RUN pip install uv
RUN uv sync

RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium

COPY jobcan_kintai/generate_auth.py /app/
COPY jobcan_kintai/main.py /app/
COPY jobcan_kintai/date_checker.py /app/
COPY jobcan_kintai/docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
