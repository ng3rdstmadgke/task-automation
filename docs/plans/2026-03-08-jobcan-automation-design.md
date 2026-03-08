# Jobcan勤怠打刻自動化 - デザインドキュメント

## 概要

Jobcanの勤怠打刻を自動化するシステム。土日・祝日・有給休暇を判定し、該当しない場合のみ打刻処理を実行する。

## 要件

- ログインURL: https://id.jobcan.jp/users/sign_in
- 打刻ページ: https://ssl.jobcan.jp/employee
- 土日、祝日、有給休暇の場合は打刻をスキップ
- 9:00と18:00に定期実行（crontabで設定）
- 出勤・退勤ともに同じPUSHボタンをクリック
- 打刻場所は初期値のまま（操作不要）
- 備考欄は空欄
- エラーログは標準出力に出力

## アーキテクチャ

### 選択したアプローチ: セッション保存型

既存のzac_auto_nippouと同じ構造を採用。セッション情報を保存することで、毎回のログインを回避し、Jobcanのセキュリティ制限に引っかかりにくくする。

### プロジェクト構造

```
jobcan_kintai/
├── generate_auth.py      # 初回セッション生成スクリプト
├── main.py               # 打刻実行スクリプト
├── config.json           # 有給日設定
├── .env                  # 認証情報（JOBCAN_EMAIL, JOBCAN_PASSWORD）
├── auth.json             # 生成されたセッション情報（gitignore対象）
├── pyproject.toml        # 依存関係（uv管理）
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── entrypoint.sh
├── scripts/
│   └── run_jobcan.sh     # ホスト側から実行するスクリプト
└── README.md
```

### 実行フロー

1. **初回セットアップ**: `generate_auth.py`を実行してauth.jsonを生成
2. **定期実行**: ホスト側のcrontabが`scripts/run_jobcan.sh`を9:00と18:00に実行
3. **コンテナ起動**: run_jobcan.shがDockerコンテナを起動
4. **打刻処理**: コンテナ内で`main.py`が実行され、土日・祝日・有給をチェック後、打刻を実行
5. **ログ出力**: 結果を標準出力に出力してコンテナ終了

## コンポーネント詳細

### 1. generate_auth.py

- Playwrightでブラウザを起動（headless mode）
- https://id.jobcan.jp/users/sign_in にアクセス
- .envから読み込んだ認証情報でログイン
- ログイン後のブラウザコンテキストをauth.jsonに保存
- セッション有効期限切れ時は手動で再実行

### 2. main.py

**日付チェック**:
- 実行日が土日かチェック（datetimeで判定）
- jpholidayライブラリで祝日チェック
- config.jsonから有給日リストを読み込み、該当日かチェック
- いずれかに該当する場合は打刻せずに終了

**打刻処理**:
- auth.jsonからセッションを復元してブラウザコンテキスト作成
- https://ssl.jobcan.jp/employee にアクセス
- PUSHボタンをクリック
- 成功/失敗をログ出力

### 3. config.json

```json
{
  "paid_leave_days": [
    "3/6",
    "3/15",
    "4/27",
    "4/28"
  ]
}
```

月/日形式の文字列配列で管理。年をまたぐ有給日も管理可能。

### 4. scripts/run_jobcan.sh

- devcontainerの環境変数を使用してdocker composeを実行
- コンテナのログを標準出力に表示
- crontabから実行される想定

## データフロー

### 認証情報の流れ
- .env（ホスト）→ Dockerボリュームマウント → コンテナ内の.env → Pythonスクリプトで読み込み
- auth.json（ホスト）→ Dockerボリュームマウント → コンテナ内で使用

### 設定情報の流れ
- config.json（ホスト）→ Dockerボリュームマウント（read-only）→ Pythonスクリプトで読み込み

### ログの流れ
- Pythonスクリプト → 標準出力 → Dockerログ → ホスト側のcronログまたは実行ターミナル

## エラーハンドリング

### generate_auth.py

- ログインページへのアクセス失敗 → エラーメッセージを出力して終了
- 認証情報が不正 → エラーメッセージを出力して終了
- セッション保存失敗 → エラーメッセージを出力して終了

### main.py

- config.json読み込み失敗 → エラーメッセージを出力して終了
- auth.json読み込み失敗 → "セッションファイルが見つかりません。generate_auth.pyを実行してください" と出力して終了
- セッション期限切れ → エラーメッセージを出力（手動でgenerate_auth.py再実行が必要）
- PUSHボタンが見つからない → エラーメッセージを出力して終了
- ネットワークエラー → エラーメッセージを出力して終了

全てのエラーは標準出力に出力し、リトライや通知は行わない。

## テストとデプロイ

### テスト方針

**手動テスト**で動作確認:
- ローカル環境でgenerate_auth.pyを実行してauth.jsonが生成されることを確認
- ローカル環境でmain.pyを実行して打刻が成功することを確認
- Docker環境でentrypoint.shが正常に動作することを確認
- 土日・祝日・有給日の判定ロジックを手動でテスト（日付を変更して確認）

**自動テストは実装しない**:
- 実際のJobcanサーバーにアクセスする必要があるため、自動テストは困難
- シンプルなスクリプトのため、手動テストで十分

### デプロイ手順

1. `jobcan_kintai`ディレクトリを作成し、必要なファイルを配置
2. `.env`ファイルを作成して認証情報を設定
3. `config.json`を作成して有給日を設定
4. ローカルで`generate_auth.py`を実行してauth.jsonを生成
5. Docker環境でテスト実行
6. `scripts/run_jobcan.sh`がcrontabから実行可能であることを確認

## 技術スタック

- Python 3.12
- Playwright: ブラウザ自動化
- jpholiday: 日本の祝日判定
- pydantic: 設定ファイル読み込みとバリデーション
- Docker: コンテナ化
- uv: Pythonパッケージ管理

## セキュリティ考慮事項

- 認証情報は.envファイルで管理（gitignore対象）
- auth.jsonもgitignore対象
- Docker volumeでマウントし、コンテナイメージには含めない
- config.jsonはread-onlyでマウント
