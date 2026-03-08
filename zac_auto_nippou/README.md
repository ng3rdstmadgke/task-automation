# ZAC Auto Nippou

ZACの日報入力を自動化するスクリプトです。

## 準備（初回のみ）

Docker環境（ヘッドレス）で実行するため、事前にログインセッションファイル（`auth.json`）を生成する必要があります。

1. Pythonパッケージ管理ツール `uv` をインストールします。
2. 依存ライブラリをインストールし、ブラウザをセットアップします。
   ```bash
   uv sync
   uv run playwright install chromium
   ```
3. 環境変数ファイルを作成します。
   ```bash
   cp .env.sample .env
   ```
   `.env` ファイルを開き、ZACのログインIDとパスワードを設定してください。
   ```
   ZAC_ID=your_actual_zac_id
   ZAC_PASSWORD=your_actual_password
   ```
4. 認証情報生成スクリプトを実行します。
   ```bash
   uv run python generate_auth.py
   ```
   自動的にZACにログインし、日報画面まで進んで `auth.json` がディレクトリ内に作成されます。

## 実行方法 (Docker)

1. `config.json` を開き、対象年月や案件時間などを編集します。
2. Docker Composeを利用してコンテナを起動・実行します。
   ```bash
   # docker-compose.ymlがある beex-tools/docker/zac_auto_nippou ディレクトリに移動
   cd ../docker/zac_auto_nippou
   
   # ビルド＆実行
   docker compose up --build
   ```
3. ターミナルに実行ログが表示され、完了するとコンテナが終了します。
