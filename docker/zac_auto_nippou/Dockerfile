FROM python:3.12-slim-bookworm

# 必要なシステムパッケージのインストール（タイムゾーン等）
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

# タイムゾーンを日本に設定
ENV TZ=Asia/Tokyo

# 作業ディレクトリの設定
WORKDIR /app

# 依存ライブラリのコピーとインストール (uvを利用)
COPY zac_auto_nippou/pyproject.toml zac_auto_nippou/uv.lock /app/
RUN pip install uv
RUN uv sync

COPY zac_auto_nippou/ /app/

# Playwrightが使用するブラウザ(Chromium)と依存OSライブラリ群のインストール
# uv環境内のplaywrightコマンドを呼び出す
RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium

# Copy and set permissions for entrypoint script
COPY docker/zac_auto_nippou/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 実行コマンド (docker-compose側で上書き可能)
CMD ["/app/entrypoint.sh"]
