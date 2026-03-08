# Jobcan勤怠打刻自動化 実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Jobcanの勤怠打刻を自動化し、土日・祝日・有給日を判定して平日のみ打刻するシステムを構築する

**Architecture:** Playwrightでブラウザ自動化、初回ログイン時にセッション情報を保存、実行時にセッションを復元して打刻。Dockerコンテナで実行し、ホスト側のcronから起動。

**Tech Stack:** Python 3.12, Playwright, jpholiday, pydantic, Docker, uv

---

## Task 1: プロジェクト構造とベースファイルの作成

**Files:**
- Create: `jobcan_kintai/pyproject.toml`
- Create: `jobcan_kintai/.python-version`
- Create: `jobcan_kintai/.env.sample`
- Create: `jobcan_kintai/config.sample.json`
- Create: `jobcan_kintai/.gitignore`

**Step 1: プロジェクトディレクトリを作成**

```bash
mkdir -p /workspaces/task-automation/jobcan_kintai
cd /workspaces/task-automation/jobcan_kintai
```

**Step 2: pyproject.tomlを作成**

```toml
[project]
name = "jobcan-kintai"
version = "0.1.0"
description = "Jobcan attendance automation"
requires-python = ">=3.12"
dependencies = [
    "jpholiday>=1.0.3",
    "playwright>=1.58.0",
    "pydantic>=2.12.5",
    "pydantic-settings>=2.13.1",
]
```

**Step 3: .python-versionを作成**

```
3.12
```

**Step 4: .env.sampleを作成**

```
JOBCAN_EMAIL=your_email@example.com
JOBCAN_PASSWORD=your_password
```

**Step 5: config.sample.jsonを作成**

```json
{
  "paid_leave_days": [
    "3/6",
    "3/15"
  ]
}
```

**Step 6: .gitignoreを作成**

```
.env
auth.json
__pycache__/
*.pyc
.pytest_cache/
tmp/
```

**Step 7: コミット**

```bash
git add jobcan_kintai/
git commit -m "feat: jobcan_kintai プロジェクト構造を作成"
```

---

## Task 2: generate_auth.py の実装

**Files:**
- Create: `jobcan_kintai/generate_auth.py`

**Step 1: 依存ライブラリをインストール**

```bash
cd /workspaces/task-automation/jobcan_kintai
uv sync
uv run playwright install chromium
```

**Step 2: generate_auth.pyの基本構造を作成**

```python
#!/usr/bin/env python3
"""
Jobcanにログインしてセッション情報を保存するスクリプト
"""
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """環境変数の設定"""
    jobcan_email: str
    jobcan_password: str

    class Config:
        env_file = ".env"
        case_sensitive = False


async def generate_auth():
    """Jobcanにログインしてauth.jsonを生成"""
    print("=== Jobcan 認証情報生成 ===")

    # 設定を読み込み
    try:
        settings = Settings()
        print(f"ログインID: {settings.jobcan_email}")
    except Exception as e:
        print(f"エラー: 環境変数の読み込みに失敗しました - {e}")
        print(".envファイルを確認してください")
        return False

    # ブラウザを起動
    async with async_playwright() as p:
        print("ブラウザを起動中...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # ログインページにアクセス
            print("ログインページにアクセス中...")
            await page.goto("https://id.jobcan.jp/users/sign_in", timeout=30000)
            await page.wait_for_load_state("networkidle")

            # メールアドレスを入力
            print("認証情報を入力中...")
            await page.fill('input[name="user[email]"]', settings.jobcan_email)
            await page.fill('input[name="user[password]"]', settings.jobcan_password)

            # ログインボタンをクリック
            print("ログイン中...")
            await page.click('input[type="submit"]')
            await page.wait_for_load_state("networkidle")

            # ログイン成功を確認（URLが変わることを確認）
            current_url = page.url
            if "sign_in" in current_url:
                print("エラー: ログインに失敗しました。認証情報を確認してください")
                return False

            print(f"ログイン成功: {current_url}")

            # セッション情報を保存
            print("セッション情報を保存中...")
            storage = await context.storage_state(path="auth.json")
            print("✓ auth.json を生成しました")

            return True

        except Exception as e:
            print(f"エラー: {e}")
            return False
        finally:
            await browser.close()


if __name__ == "__main__":
    print("標準出力バッファリングを無効化")
    import sys
    sys.stdout.reconfigure(line_buffering=True)

    success = asyncio.run(generate_auth())
    if success:
        print("=== 認証情報生成完了 ===")
        sys.exit(0)
    else:
        print("=== 認証情報生成失敗 ===")
        sys.exit(1)
```

**Step 3: 動作確認（.envファイルを作成してから実行）**

```bash
# .envファイルを作成（実際の認証情報を設定）
cp .env.sample .env
# .envを編集

# スクリプトを実行
uv run python generate_auth.py
```

Expected: "✓ auth.json を生成しました" と表示され、auth.jsonが作成される

**Step 4: コミット**

```bash
git add jobcan_kintai/generate_auth.py
git commit -m "feat: generate_auth.py を実装"
```

---

## Task 3: 日付判定ロジックの実装

**Files:**
- Create: `jobcan_kintai/date_checker.py`

**Step 1: date_checker.pyを作成**

```python
#!/usr/bin/env python3
"""
土日・祝日・有給日を判定するモジュール
"""
import json
from datetime import datetime
from pathlib import Path
import jpholiday


def load_paid_leave_days(config_path: str = "config.json") -> list[str]:
    """config.jsonから有給日リストを読み込む

    Args:
        config_path: config.jsonのパス

    Returns:
        有給日のリスト（"月/日"形式）
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("paid_leave_days", [])
    except FileNotFoundError:
        print(f"警告: {config_path} が見つかりません。有給日なしとして処理します")
        return []
    except json.JSONDecodeError as e:
        print(f"エラー: {config_path} のJSONパースに失敗しました - {e}")
        raise


def is_weekend(target_date: datetime) -> bool:
    """土日かどうかを判定

    Args:
        target_date: 判定する日付

    Returns:
        土曜(5)または日曜(6)の場合True
    """
    return target_date.weekday() in (5, 6)


def is_holiday(target_date: datetime) -> bool:
    """祝日かどうかを判定

    Args:
        target_date: 判定する日付

    Returns:
        祝日の場合True
    """
    return jpholiday.is_holiday(target_date)


def is_paid_leave(target_date: datetime, paid_leave_days: list[str]) -> bool:
    """有給日かどうかを判定

    Args:
        target_date: 判定する日付
        paid_leave_days: 有給日リスト（"月/日"形式）

    Returns:
        有給日の場合True
    """
    # "月/日"形式の文字列に変換して比較
    target_str = f"{target_date.month}/{target_date.day}"
    return target_str in paid_leave_days


def should_skip_punch(target_date: datetime, config_path: str = "config.json") -> tuple[bool, str]:
    """打刻をスキップすべきかどうかを判定

    Args:
        target_date: 判定する日付
        config_path: config.jsonのパス

    Returns:
        (スキップすべきか, 理由)のタプル
    """
    # 土日チェック
    if is_weekend(target_date):
        weekday_name = "土曜日" if target_date.weekday() == 5 else "日曜日"
        return True, f"{weekday_name}のため"

    # 祝日チェック
    if is_holiday(target_date):
        holiday_name = jpholiday.is_holiday_name(target_date)
        return True, f"祝日（{holiday_name}）のため"

    # 有給日チェック
    paid_leave_days = load_paid_leave_days(config_path)
    if is_paid_leave(target_date, paid_leave_days):
        return True, "有給休暇のため"

    return False, ""


if __name__ == "__main__":
    # 動作確認
    today = datetime.now()
    should_skip, reason = should_skip_punch(today)

    print(f"日付: {today.strftime('%Y年%m月%d日')}")
    if should_skip:
        print(f"判定: スキップ（{reason}）")
    else:
        print("判定: 打刻実行")
```

**Step 2: 動作確認**

```bash
# config.jsonを作成
cp config.sample.json config.json

# スクリプトを実行
uv run python date_checker.py
```

Expected: 今日の日付と判定結果が表示される

**Step 3: コミット**

```bash
git add jobcan_kintai/date_checker.py
git commit -m "feat: 日付判定ロジックを実装"
```

---

## Task 4: main.py の実装

**Files:**
- Create: `jobcan_kintai/main.py`

**Step 1: main.pyを作成**

```python
#!/usr/bin/env python3
"""
Jobcanの打刻を実行するメインスクリプト
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

from date_checker import should_skip_punch


async def punch_jobcan():
    """Jobcanで打刻を実行"""
    print("=== Jobcan 打刻処理 ===")

    # 日付チェック
    today = datetime.now()
    print(f"実行日時: {today.strftime('%Y年%m月%d日 %H:%M:%S')}")

    should_skip, reason = should_skip_punch(today)
    if should_skip:
        print(f"打刻スキップ: {reason}")
        return True

    print("打刻を実行します")

    # auth.jsonの存在確認
    auth_file = Path("auth.json")
    if not auth_file.exists():
        print("エラー: auth.json が見つかりません")
        print("generate_auth.py を実行してセッションファイルを生成してください")
        return False

    # ブラウザを起動
    async with async_playwright() as p:
        print("ブラウザを起動中...")
        browser = await p.chromium.launch(headless=True)

        try:
            # セッションを復元
            print("セッション情報を読み込み中...")
            context = await browser.new_context(storage_state="auth.json")
            page = await context.new_page()

            # 打刻ページにアクセス
            print("打刻ページにアクセス中...")
            await page.goto("https://ssl.jobcan.jp/employee", timeout=30000)
            await page.wait_for_load_state("networkidle")

            # ログイン状態を確認
            current_url = page.url
            if "sign_in" in current_url:
                print("エラー: セッションが期限切れです")
                print("generate_auth.py を再実行してセッションを更新してください")
                return False

            print("ログイン状態確認: OK")

            # PUSHボタンを探してクリック
            print("PUSHボタンを探しています...")

            # 複数の可能性のあるセレクタを試す
            selectors = [
                'button:has-text("PUSH")',
                'input[type="submit"][value="PUSH"]',
                'button:text-is("PUSH")',
                'input[value="PUSH"]',
            ]

            button_found = False
            for selector in selectors:
                try:
                    button = page.locator(selector).first
                    if await button.count() > 0:
                        print(f"PUSHボタンを発見: {selector}")
                        await button.click()
                        button_found = True
                        break
                except Exception:
                    continue

            if not button_found:
                print("エラー: PUSHボタンが見つかりませんでした")
                print("ページの構造が変更されている可能性があります")
                # スクリーンショットを保存
                await page.screenshot(path="tmp/error_screenshot.png")
                print("スクリーンショットを tmp/error_screenshot.png に保存しました")
                return False

            # ボタンクリック後の処理を待つ
            print("打刻処理中...")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # 処理完了を待つ

            print("✓ 打刻完了")
            return True

        except Exception as e:
            print(f"エラー: {e}")
            try:
                await page.screenshot(path="tmp/error_screenshot.png")
                print("スクリーンショットを tmp/error_screenshot.png に保存しました")
            except:
                pass
            return False
        finally:
            await browser.close()


if __name__ == "__main__":
    print("標準出力バッファリングを無効化")
    sys.stdout.reconfigure(line_buffering=True)

    # tmpディレクトリを作成
    Path("tmp").mkdir(exist_ok=True)

    success = asyncio.run(punch_jobcan())
    if success:
        print("=== 処理完了 ===")
        sys.exit(0)
    else:
        print("=== 処理失敗 ===")
        sys.exit(1)
```

**Step 2: 動作確認（auth.jsonが存在することを確認）**

```bash
# main.pyを実行
uv run python main.py
```

Expected: 日付判定が実行され、平日の場合は打刻処理が実行される

**Step 3: コミット**

```bash
git add jobcan_kintai/main.py
git commit -m "feat: main.py 打刻処理を実装"
```

---

## Task 5: Docker構成の作成

**Files:**
- Create: `jobcan_kintai/docker/Dockerfile`
- Create: `jobcan_kintai/docker/docker-compose.yml`
- Create: `jobcan_kintai/docker/entrypoint.sh`

**Step 1: dockerディレクトリを作成**

```bash
mkdir -p /workspaces/task-automation/jobcan_kintai/docker
```

**Step 2: Dockerfileを作成**

```dockerfile
FROM python:3.12-slim-bookworm

# 必要なシステムパッケージのインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

# タイムゾーンを日本に設定
ENV TZ=Asia/Tokyo

# 作業ディレクトリの設定
WORKDIR /app

# 依存ライブラリのコピーとインストール
COPY jobcan_kintai/pyproject.toml /app/
RUN pip install uv
RUN uv sync

# Playwrightが使用するブラウザ(Chromium)と依存OSライブラリ群のインストール
RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium

# アプリケーションファイルのコピー
COPY jobcan_kintai/generate_auth.py /app/
COPY jobcan_kintai/main.py /app/
COPY jobcan_kintai/date_checker.py /app/
COPY jobcan_kintai/docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 実行コマンド
CMD ["/app/entrypoint.sh"]
```

**Step 3: docker-compose.ymlを作成**

```yaml
version: '3.8'

services:
  jobcan-automation:
    build:
      context: ../../
      dockerfile: jobcan_kintai/docker/Dockerfile
    container_name: jobcan_kintai_app
    volumes:
      - type: bind
        source: ${HOST_DIR:-../../}/jobcan_kintai/config.json
        target: /app/config.json
        read_only: true
      - type: bind
        source: ${HOST_DIR:-../../}/jobcan_kintai/.env
        target: /app/.env
        read_only: true
      - type: bind
        source: ${HOST_DIR:-../../}/jobcan_kintai/auth.json
        target: /app/auth.json
        read_only: true
    environment:
      - TZ=Asia/Tokyo
      - PYTHONUNBUFFERED=1
```

**Step 4: entrypoint.shを作成**

```bash
#!/bin/bash
set -e

echo "=== Jobcan 打刻自動化 ==="
echo "Step 1: 打刻処理を実行..."
uv run python main.py
echo "=== 処理完了 ==="
```

**Step 5: 実行権限を付与**

```bash
chmod +x /workspaces/task-automation/jobcan_kintai/docker/entrypoint.sh
```

**Step 6: コミット**

```bash
git add jobcan_kintai/docker/
git commit -m "feat: Docker構成を追加"
```

---

## Task 6: 実行用シェルスクリプトの作成

**Files:**
- Create: `jobcan_kintai/scripts/run_jobcan.sh`

**Step 1: scriptsディレクトリを作成**

```bash
mkdir -p /workspaces/task-automation/jobcan_kintai/scripts
```

**Step 2: run_jobcan.shを作成**

```bash
#!/bin/bash
set -e

# このスクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== Jobcan打刻自動化スクリプト ==="
echo "プロジェクトルート: ${PROJECT_ROOT}"
echo "実行時刻: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# dockerディレクトリに移動
cd "${PROJECT_ROOT}/docker"

# 環境変数を設定
export HOST_DIR="${PROJECT_ROOT}"

# Dockerコンテナを実行
echo "Dockerコンテナを起動中..."
docker compose up --build --force-recreate --remove-orphans

echo ""
echo "=== 実行完了 ==="
```

**Step 3: 実行権限を付与**

```bash
chmod +x /workspaces/task-automation/jobcan_kintai/scripts/run_jobcan.sh
```

**Step 4: 動作確認**

```bash
# スクリプトを実行
/workspaces/task-automation/jobcan_kintai/scripts/run_jobcan.sh
```

Expected: Dockerコンテナがビルド・起動され、打刻処理が実行される

**Step 5: コミット**

```bash
git add jobcan_kintai/scripts/
git commit -m "feat: 実行用シェルスクリプトを追加"
```

---

## Task 7: READMEドキュメントの作成

**Files:**
- Create: `jobcan_kintai/README.md`

**Step 1: README.mdを作成**

```markdown
# Jobcan 勤怠打刻自動化

Jobcanの勤怠打刻を自動化するスクリプトです。

## 機能

- 土日・祝日・有給休暇を自動判定
- 平日のみ自動打刻を実行
- セッション保存により毎回のログインを回避
- Dockerコンテナで実行

## セットアップ

### 1. 依存ライブラリをインストール

```bash
cd /workspaces/task-automation/jobcan_kintai
uv sync
uv run playwright install chromium
```

### 2. 環境変数ファイルを作成

```bash
cp .env.sample .env
```

`.env`ファイルを開き、Jobcanのログイン情報を設定してください。

```
JOBCAN_EMAIL=your_email@example.com
JOBCAN_PASSWORD=your_password
```

### 3. 設定ファイルの作成

```bash
cp config.sample.json config.json
```

`config.json`を開き、有給休暇日を設定してください。

```json
{
  "paid_leave_days": [
    "3/6",
    "3/15",
    "4/27"
  ]
}
```

### 4. 認証情報生成スクリプトを実行

```bash
uv run python generate_auth.py
```

成功すると`auth.json`が生成されます。

## 実行方法

### ローカルで実行

```bash
uv run python main.py
```

### Dockerで実行

```bash
cd docker
docker compose up --build --force-recreate
```

### シェルスクリプトで実行

```bash
./scripts/run_jobcan.sh
```

## crontabへの登録

以下のようにcrontabに登録すると、9:00と18:00に自動実行されます。

```bash
0 9 * * * /workspaces/task-automation/jobcan_kintai/scripts/run_jobcan.sh >> /tmp/jobcan_kintai.log 2>&1
0 18 * * * /workspaces/task-automation/jobcan_kintai/scripts/run_jobcan.sh >> /tmp/jobcan_kintai.log 2>&1
```

## トラブルシューティング

### セッションが期限切れの場合

```bash
uv run python generate_auth.py
```

を再実行してセッションを更新してください。

### PUSHボタンが見つからない場合

ページの構造が変更されている可能性があります。`tmp/error_screenshot.png`を確認してください。

## ファイル構成

```
jobcan_kintai/
├── generate_auth.py      # 認証情報生成スクリプト
├── main.py               # 打刻実行スクリプト
├── date_checker.py       # 日付判定モジュール
├── config.json           # 有給日設定
├── .env                  # 認証情報（gitignore対象）
├── auth.json             # セッション情報（gitignore対象）
├── docker/               # Docker関連ファイル
├── scripts/              # 実行用シェルスクリプト
└── README.md             # このファイル
```
```

**Step 2: コミット**

```bash
git add jobcan_kintai/README.md
git commit -m "docs: READMEを追加"
```

---

## Task 8: 最終テストとバリデーション

**Step 1: ローカル環境でのテスト**

```bash
cd /workspaces/task-automation/jobcan_kintai

# 1. 依存関係のインストール
uv sync
uv run playwright install chromium

# 2. .envファイルの作成
cp .env.sample .env
# .envを編集して実際の認証情報を設定

# 3. config.jsonの作成
cp config.sample.json config.json
# config.jsonを編集

# 4. 認証情報の生成
uv run python generate_auth.py

# 5. 打刻処理のテスト
uv run python main.py
```

Expected: 全ての処理が正常に実行される

**Step 2: Docker環境でのテスト**

```bash
cd /workspaces/task-automation/jobcan_kintai/docker
docker compose up --build --force-recreate
```

Expected: Dockerコンテナが正常に起動し、打刻処理が実行される

**Step 3: シェルスクリプトのテスト**

```bash
/workspaces/task-automation/jobcan_kintai/scripts/run_jobcan.sh
```

Expected: スクリプトが正常に実行される

**Step 4: 日付判定のテスト**

```bash
# 土日・祝日・有給日のconfig.jsonを作成してテスト
uv run python date_checker.py
```

Expected: 正しく判定結果が表示される

**Step 5: エラーケースのテスト**

- auth.jsonを削除して実行 → エラーメッセージが表示される
- 不正な.envで実行 → ログインエラーが表示される
- 不正なconfig.jsonで実行 → JSONパースエラーが表示される

**Step 6: 最終コミット**

```bash
git add .
git commit -m "test: 動作確認完了"
```

---

## 完了条件

- [ ] すべてのファイルが作成され、gitにコミットされている
- [ ] ローカル環境で正常に動作する
- [ ] Docker環境で正常に動作する
- [ ] シェルスクリプトから正常に実行できる
- [ ] 土日・祝日・有給日の判定が正しく動作する
- [ ] エラーハンドリングが適切に動作する
- [ ] READMEが完成している

## 注意事項

- 実際の認証情報は`.env`ファイルに記載し、gitにコミットしないこと
- `auth.json`もgitにコミットしないこと
- セッションは定期的に期限切れになるため、その際は`generate_auth.py`を再実行すること
- Playwright MCPやChrome DevTools MCPを使って、適宜画面を確認しながら開発を進めること
