# ZAC Auto Nippou

ZACの日報入力を自動化するスクリプトです。

## 実行方法 (ローカル)


### 1. 依存ライブラリをインストールし、ブラウザをセットアップします。

```bash
uv sync
uv run playwright install chromium
```

### 2. 環境変数ファイルを作成します。

```bash
cp .env.sample .env
```

`.env` ファイルを開き、ZACのログインIDとパスワードを設定してください。

```
ZAC_ID=your_actual_zac_id
ZAC_PASSWORD=your_actual_password
```

### 3. 設定ファイルの作成

```bash
cp config.sample.json config.json
```
config.json を開き修正

```js:config.json
{
  "target_year": 2026,  // 対象年
  "target_month": 3,  // 対象月
  "paid_leave_days": [6],  // 有給日
  "project_hours": {  // プロジェエクトコードと工数(時間)の辞書
    "xxxxxxx": 20,
    "xxxxxxx": 4
  }
}
```

### 4. 認証情報生成スクリプトを実行します。

```bash
# generate_auth.pyは事前にログインセッションファイル(auth.json)を生成
uv run python generate_auth.py && uv run python main.py
```

## 変更履歴

### 2026-03-08: 型安全性の向上

- `python-dotenv` を `pydantic-settings` に置き換え
- すべてのデータ構造をPydanticモデルに変換
- 関数の型ヒントを追加
- 既存の`config.json`形式との後方互換性を維持
