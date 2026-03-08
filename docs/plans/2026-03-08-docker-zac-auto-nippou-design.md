# ZAC Auto Nippou Docker化 設計書

**作成日:** 2026-03-08

**目的:** zac_auto_nippouスクリプトをDockerコンテナで実行できるようにする。既存のdocker/zac_auto_nippouディレクトリ内のDockerfileとdocker-compose.ymlを修正する。

## 要件

- 手動で`docker-compose up`を実行して、必要な時だけ起動
- 毎回`generate_auth.py && main.py`を連続実行
- ホストの`zac_auto_nippou/.env`をボリュームマウント
- ホストの`zac_auto_nippou/config.json`をボリュームマウント
- `auth.json`はコンテナ内で生成（マウント不要）

## 全体アーキテクチャ

### 構成

```
docker/zac_auto_nippou/
├── Dockerfile          # 既存を修正
├── docker-compose.yml  # 既存を修正
└── entrypoint.sh       # 新規作成
```

### 実行フロー

1. ユーザーが`docker-compose up`実行
2. コンテナ起動 → entrypoint.sh実行
3. entrypoint.sh内で：
   - `generate_auth.py`実行（認証情報生成、auth.json作成）
   - 成功したら`main.py`実行（日報自動入力）
   - どちらかが失敗したら停止
4. 完了後、コンテナ自動終了

### マウントするファイル

- `zac_auto_nippou/config.json` → `/app/config.json`（読み取り専用）
- `zac_auto_nippou/.env` → `/app/.env`（読み取り専用）

## コンポーネント設計

### 1. Dockerfile（修正）

**修正内容：**

#### 1-1. COPYパスの修正
```dockerfile
# 現在（問題あり）
COPY zac_auto_nippou/pyproject.toml zac_auto_nippou/uv.lock .

# 修正後
COPY zac_auto_nippou/pyproject.toml zac_auto_nippou/uv.lock /app/
```

**理由：** build contextが`../../`（task-automationルート）なので、正しいパスを指定する必要がある。

#### 1-2. entrypoint.shの追加
```dockerfile
COPY docker/zac_auto_nippou/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
```

#### 1-3. CMDの変更
```dockerfile
# 現在
CMD ["uv", "run", "python", "main.py"]

# 修正後
CMD ["/app/entrypoint.sh"]
```

#### 維持する内容
- Playwrightのインストール（chromiumとdeps）
- タイムゾーン設定（TZ=Asia/Tokyo）
- Python 3.12-slim-bookworm
- uvを使った依存関係管理

### 2. docker-compose.yml（修正）

**修正内容：**

#### 2-1. volumesの修正
```yaml
# 現在
volumes:
  - ../../zac_auto_nippou/config.json:/app/config.json
  - ../../zac_auto_nippou/auth.json:/app/auth.json

# 修正後
volumes:
  - ../../zac_auto_nippou/config.json:/app/config.json:ro
  - ../../zac_auto_nippou/.env:/app/.env:ro
```

**変更点：**
- `auth.json`のマウントを削除（コンテナ内で生成されるため不要）
- `.env`のマウントを追加（ZAC_ID, ZAC_PASSWORD用）
- `:ro`で読み取り専用に設定（セキュリティ向上）

#### 維持する内容
- build context: `../../`
- dockerfile: `docker/zac_auto_nippou/Dockerfile`
- container_name: `zac_auto_nippou_app`
- environment: `TZ=Asia/Tokyo`

### 3. entrypoint.sh（新規作成）

**配置場所：** `docker/zac_auto_nippou/entrypoint.sh`

**内容：**
```bash
#!/bin/bash
set -e  # エラーが発生したら即座に終了

echo "=== ZAC Auto Nippou Docker ==="
echo "Step 1: Generating authentication..."
uv run python generate_auth.py

if [ $? -eq 0 ]; then
    echo "Step 1: Authentication completed successfully"
    echo ""
    echo "Step 2: Running main automation..."
    uv run python main.py

    if [ $? -eq 0 ]; then
        echo "Step 2: Automation completed successfully"
        echo "=== All tasks completed ==="
    else
        echo "ERROR: main.py failed"
        exit 1
    fi
else
    echo "ERROR: generate_auth.py failed"
    exit 1
fi
```

**ポイント：**
- `set -e`でエラー時に自動停止
- 各ステップの実行結果を明示的に表示
- エラー時は適切なメッセージとexit code 1で終了
- 成功時は成功メッセージを表示

## データフロー

### 1. 起動時
```
docker-compose up
  ↓
Dockerコンテナ起動
  ↓
entrypoint.sh実行
```

### 2. 認証フェーズ（generate_auth.py）
```
entrypoint.sh
  ↓
generate_auth.py実行
  ↓ (環境変数読み込み)
/app/.env (ZAC_ID, ZAC_PASSWORD)
  ↓ (認証処理)
Playwrightでブラウザ起動
  ↓ (成功)
/app/auth.json生成（コンテナ内）
```

### 3. 自動化フェーズ（main.py）
```
entrypoint.sh
  ↓
main.py実行
  ↓ (設定読み込み)
/app/config.json
  ↓ (認証情報読み込み)
/app/auth.json（コンテナ内）
  ↓ (自動化処理)
Playwrightでブラウザ起動
  ↓
日報入力処理
```

### 4. 終了
```
main.py完了
  ↓
entrypoint.sh完了
  ↓
コンテナ自動終了
```

## エラーハンドリング

### generate_auth.py失敗時
- エラーメッセージ表示：`"ERROR: generate_auth.py failed"`
- exit code 1で終了
- main.pyは実行されない

### main.py失敗時
- エラーメッセージ表示：`"ERROR: main.py failed"`
- exit code 1で終了

### 想定されるエラーケース
1. `.env`ファイルが存在しない → generate_auth.pyでValidationError
2. `config.json`が存在しない → main.pyでFileNotFoundError
3. ネットワークエラー → Playwright内でエラー
4. ZAC認証失敗→ generate_auth.pyでタイムアウト

すべてのケースで適切なエラーメッセージが表示され、コンテナは終了する。

## 使用方法

### 1. 前提条件
```bash
# 必要なファイルが揃っていることを確認
ls zac_auto_nippou/.env        # ZAC_ID, ZAC_PASSWORD
ls zac_auto_nippou/config.json # target_year, target_month, etc.
```

### 2. ビルド
```bash
cd docker/zac_auto_nippou
docker-compose build
```

### 3. 実行
```bash
cd docker/zac_auto_nippou
docker-compose up
```

### 4. 実行結果の確認
```
=== ZAC Auto Nippou Docker ===
Step 1: Generating authentication...
ZACのログイン画面を開きます...
...
Step 1: Authentication completed successfully

Step 2: Running main automation...
カレンダーと配分を計算しました: 2026年3月
...
Step 2: Automation completed successfully
=== All tasks completed ===
```

## セキュリティ考慮事項

1. **読み取り専用マウント**
   - `config.json`と`.env`は`:ro`フラグで読み取り専用
   - コンテナからホストファイルを変更できない

2. **認証情報の扱い**
   - `.env`ファイルはホストに保存（Gitにコミットしない）
   - `auth.json`はコンテナ内のみに存在（永続化されない）

3. **最小権限の原則**
   - コンテナは実行完了後自動終了
   - 不要な権限は付与しない

## 制限事項

1. **auth.jsonの永続化なし**
   - 毎回generate_auth.pyで認証が必要
   - 認証セッションは保存されない
   - これは要件通りの動作

2. **ヘッドレスブラウザ**
   - GUI表示なし
   - デバッグ時はスクリーンショット機能を活用

3. **ログの永続化**
   - コンテナ終了後、標準出力ログは失われる
   - 必要であればログファイルをボリュームマウント

## テスト戦略

### 1. ビルドテスト
```bash
docker-compose build
# 期待：ビルド成功、エラーなし
```

### 2. 実行テスト
```bash
docker-compose up
# 期待：
# - generate_auth.py成功
# - main.py成功
# - コンテナ自動終了
```

### 3. エラーハンドリングテスト

**テスト1：.envが存在しない**
```bash
mv zac_auto_nippou/.env zac_auto_nippou/.env.backup
docker-compose up
# 期待：ValidationErrorでgenerate_auth.pyが失敗
```

**テスト2：config.jsonが存在しない**
```bash
mv zac_auto_nippou/config.json zac_auto_nippou/config.json.backup
docker-compose up
# 期待：FileNotFoundErrorでmain.pyが失敗
```

## 今後の拡張案

1. **ログファイルの永続化**
   - `/app/logs`ディレクトリをボリュームマウント
   - 実行履歴を保存

2. **スケジュール実行**
   - cron等と組み合わせて自動実行
   - 例：毎朝9時に自動実行

3. **通知機能**
   - Slack/Email通知を追加
   - 成功/失敗を通知

4. **マルチステージビルド**
   - ビルドステージと実行ステージを分離
   - イメージサイズを削減

## まとめ

このDocker化により、以下のメリットが得られる：

1. **環境の一貫性**：どこでも同じ環境で実行可能
2. **依存関係の分離**：ホストを汚さない
3. **再現性**：Dockerfileで環境を再現可能
4. **シンプルな実行**：`docker-compose up`だけで完結
5. **セキュリティ**：読み取り専用マウントで安全

既存のDockerfileとdocker-compose.ymlを最小限の修正で活用し、entrypoint.shを追加するだけで、シンプルかつ堅牢なDocker化を実現する。
