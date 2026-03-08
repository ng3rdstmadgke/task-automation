# Jobcan 勤怠打刻自動化

Jobcanの勤怠打刻を自動化するスクリプトです。

- 土日・祝日・有給休暇を自動判定
- 平日のみ自動打刻を実行

## 事前準備

### 1. 依存ライブラリをインストール

```bash
cd $PROJECT_DIR/jobcan_kintai
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

## 実行方法 (ローカル)

```bash
# generate_auth.pyは事前にログインセッションファイル(auth.json)を生成
uv run python generate_auth.py && uv run python main.py
```

## 実行方法 (Docker)

```bash
./scripts/run_jobcan.sh
```

## crontabへの登録

以下のようにcrontabに登録すると、9:00と18:00に自動実行されます。

```bash
0 9 * * * /path/to/jobcan_kintai/scripts/run_jobcan.sh >> /tmp/jobcan_kintai.log 2>&1
0 18 * * * /path/to/jobcan_kintai/scripts/run_jobcan.sh >> /tmp/jobcan_kintai.log 2>&1
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
