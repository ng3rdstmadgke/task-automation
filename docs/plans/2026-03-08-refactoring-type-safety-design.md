# ZAC Auto Nippou リファクタリング設計書

**作成日:** 2026-03-08

**目的:** `zac_auto_nippou/main.py`と`zac_auto_nippou/generate_auth.py`のリファクタリング。関数の引数・戻り値の型を明示し、dict型のデータ構造をPydanticモデルに置き換えることで型安全性を向上させる。

## アーキテクチャ概要

### リファクタリングの全体像

両ファイル（`main.py`と`generate_auth.py`）の冒頭にPydanticモデルを定義し、すべての関数に明示的な型ヒントを追加する。

### データフロー

1. **外部入力の型安全化**
   - `config.json` → `Config`モデル（Pydantic BaseModel）
   - `.env` → `ZacCredentials`モデル（pydantic-settings BaseSettings）

2. **内部データ構造の型安全化**
   - `calculate_schedule`の引数：`dict` → `Config`モデル
   - `calculate_schedule`の戻り値：`tuple[dict, set]` → `ScheduleResult`モデル
   - 中間データ：dict → `Task`、`DaySchedule`モデル

3. **依存関係の変更**
   - 削除：`python-dotenv`
   - 追加：`pydantic`、`pydantic-settings`

### ファイル構成

- `main.py`: 既存ファイルを修正（モデル定義を追加）
- `generate_auth.py`: 既存ファイルを修正（モデル定義を追加）
- 新規ファイルは作成しない（各ファイルは自己完結型）

## コンポーネント設計

### main.py のPydanticモデル

#### DayType（Enum）
```python
class DayType(str, Enum):
    """日のタイプ"""
    PAID_LEAVE = "paid_leave"
    WORKDAY = "workday"
```

#### TaskContent（Enum）
```python
class TaskContent(str, Enum):
    """作業内容の種類（ZACのid_sagyou_naiyouのvalue値）"""
    PROJECT_WORK = "1"           # 案件作業
    PAID_LEAVE = "27"            # 有給・リフレッシュ・特別休暇
    SELF_DEVELOPMENT = "55"      # 自己啓発
```

#### ProjectAllocation
```python
class ProjectAllocation(BaseModel):
    """プロジェクトへの工数配分"""
    project_code: str
    hours: float = Field(gt=0)
```

#### Config
```python
class Config(BaseModel):
    """config.json の構造"""
    target_year: int = Field(ge=2000, le=2100)
    target_month: int = Field(ge=1, le=12)
    paid_leave_days: list[int] = Field(default_factory=list)
    project_hours: list[ProjectAllocation]

    @field_validator('project_hours', mode='before')
    @classmethod
    def convert_project_hours_dict(cls, v):
        """後方互換性のため、dictからlist[ProjectAllocation]に自動変換"""
        if isinstance(v, dict):
            return [ProjectAllocation(project_code=k, hours=h) for k, h in v.items()]
        return v
```

#### Task
```python
class Task(BaseModel):
    """個別タスクの構造"""
    code: str
    content: TaskContent
    hours: float = Field(gt=0, le=24)
```

#### DaySchedule
```python
class DaySchedule(BaseModel):
    """1日のスケジュール構造"""
    type: DayType
    tasks: list[Task]
    is_week_last_day: bool = False
```

#### ScheduleResult
```python
class ScheduleResult(BaseModel):
    """calculate_scheduleの戻り値"""
    schedule: dict[int, DaySchedule]
```

### generate_auth.py のPydanticモデル

#### ZacCredentials
```python
class ZacCredentials(BaseSettings):
    """環境変数（.env）の構造"""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    zac_id: str = Field(min_length=1)
    zac_password: str = Field(min_length=1)
```

## 関数シグネチャの変更

### main.py

```python
def is_weekday(day: int, target_year: int, target_month: int) -> bool:
    """指定日が平日かどうかを判定"""
    ...

def calculate_schedule(config: Config) -> ScheduleResult:
    """月間スケジュールを計算"""
    ...

def run_automation(config: Config) -> None:
    """自動化処理を実行"""
    ...
```

### generate_auth.py

```python
def login_and_save_auth() -> None:
    """ZACにログインして認証情報を保存"""
    ...
```

## データフローの詳細変更

### 1. 設定ファイルの読み込み（main.py）

**変更前:**
```python
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
run_automation(config)
```

**変更後:**
```python
with open("config.json", "r", encoding="utf-8") as f:
    config_dict = json.load(f)
config = Config(**config_dict)
run_automation(config)
```

### 2. calculate_schedule関数の内部変更

**主な変更点:**

- **引数アクセス:** `config["target_year"]` → `config.target_year`
- **project_hoursのイテレーション:**
  ```python
  # 変更前
  for code, hours in project_hours.items():
      task_queue.append({"code": code, "content": "1", "hours": hours})

  # 変更後
  for project in config.project_hours:
      task_queue.append(Task(code=project.project_code, content=TaskContent.PROJECT_WORK, hours=project.hours))
  ```

- **タスク生成:**
  ```python
  # 変更前
  tasks_today.append({"code": "", "content": "55", "hours": remaining_hours})

  # 変更後
  tasks_today.append(Task(code="", content=TaskContent.SELF_DEVELOPMENT, hours=remaining_hours))
  ```

- **DaySchedule生成:**
  ```python
  # 変更前
  schedule[day] = {
      "type": "paid_leave",
      "tasks": [{"code": "", "content": "27", "hours": 8}]
  }

  # 変更後
  schedule[day] = DaySchedule(
      type=DayType.PAID_LEAVE,
      tasks=[Task(code="", content=TaskContent.PAID_LEAVE, hours=8)],
      is_week_last_day=(day in week_last_days)
  )
  ```

- **戻り値:**
  ```python
  # 変更前
  return schedule, week_last_days

  # 変更後
  return ScheduleResult(schedule=schedule)
  ```

### 3. run_automation関数の内部変更

**主な変更点:**

- **戻り値の受け取り:**
  ```python
  # 変更前
  schedule, week_last_days = calculate_schedule(config)

  # 変更後
  result = calculate_schedule(config)
  ```

- **スケジュールアクセス:**
  ```python
  # 変更前
  if day not in schedule:
      continue
  day_info = schedule[day]

  # 変更後
  if day not in result.schedule:
      continue
  day_info = result.schedule[day]
  ```

- **day_info/taskのアクセス:**
  ```python
  # 変更前
  if day_info["type"] == "paid_leave":
      ...
  for i, task in enumerate(day_info["tasks"]):
      print(f"value={content_dict[task['content']]} code={task['code']} ({task['hours']}時間)")
      frame.locator(f"select[name='id_sagyou_naiyou{row_num}']").select_option(task["content"])
      if task["code"]:
          frame.locator(f"input[name='code_project{row_num}']").fill(task["code"])

  # 変更後
  if day_info.type == DayType.PAID_LEAVE:
      ...
  for i, task in enumerate(day_info.tasks):
      print(f"value={content_dict[task.content.value]} code={task.code} ({task.hours}時間)")
      frame.locator(f"select[name='id_sagyou_naiyou{row_num}']").select_option(task.content.value)
      if task.code:
          frame.locator(f"input[name='code_project{row_num}']").fill(task.code)
  ```

- **週報確定の判定:**
  ```python
  # 変更前（コメントアウトされているが）
  if day in week_last_days:
      ...

  # 変更後
  if day_info.is_week_last_day:
      ...
  ```

### 4. generate_auth.pyの変更

**変更前:**
```python
from dotenv import load_dotenv

load_dotenv()
zac_id = os.getenv("ZAC_ID")
zac_password = os.getenv("ZAC_PASSWORD")

if not zac_id or not zac_password:
    print("エラー: .envファイルにZAC_IDとZAC_PASSWORDを設定してください。")
    return
```

**変更後:**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, ValidationError

try:
    credentials = ZacCredentials()
except ValidationError as e:
    print("エラー: .envファイルにZAC_IDとZAC_PASSWORDを設定してください。")
    print(f"詳細: {e}")
    return

zac_id = credentials.zac_id
zac_password = credentials.zac_password
```

## エラーハンドリング

### Pydanticによる自動バリデーション

1. **設定ファイルのバリデーション**
   - 年月の範囲チェック（2000-2100年、1-12月）
   - 必須フィールドの存在チェック
   - プロジェクト工数の正の値チェック

2. **環境変数のバリデーション**
   - ZAC_ID、ZAC_PASSWORDの存在と空文字チェック

3. **タスクデータのバリデーション**
   - TaskContentのEnum値チェック（"1", "27", "55"のみ）
   - 作業時間の範囲チェック（0 < hours ≤ 24）

### 既存のエラーハンドリング

- Playwright関連のtry-exceptブロックは維持
- ページ遷移失敗、要素が見つからない場合の処理は変更なし

## テスト戦略

### 動作確認手順

1. **依存関係の更新**
   ```bash
   uv add pydantic pydantic-settings
   uv remove python-dotenv
   ```

2. **実行テスト**
   ```bash
   uv run python generate_auth.py && uv run python main.py
   ```

3. **エラー発生時**
   - ValidationErrorのメッセージから原因を特定
   - 該当箇所を修正して再テスト
   - 成功するまで繰り返し

### テストケース

- [ ] `config.json`の読み込みと型検証
- [ ] 無効な設定値（年月範囲外など）でのエラー
- [ ] `.env`の読み込みと型検証
- [ ] 環境変数未設定でのエラー
- [ ] スケジュール計算の正常動作
- [ ] ブラウザ自動化の正常動作

## 後方互換性

### config.jsonの形式

`project_hours`フィールドは、既存のdict形式（`{"PJ_CODE": hours}`）をそのまま使用可能。`field_validator`により自動的に`list[ProjectAllocation]`に変換される。

**既存形式（そのまま使える）:**
```json
{
  "project_hours": {
    "PJ_CODE_1": 20,
    "PJ_CODE_2": 4
  }
}
```

**新形式（こちらでも可）:**
```json
{
  "project_hours": [
    {"project_code": "PJ_CODE_1", "hours": 20},
    {"project_code": "PJ_CODE_2", "hours": 4}
  ]
}
```

## まとめ

このリファクタリングにより、以下のメリットが得られる：

1. **型安全性の向上**: すべての関数が明示的な型を持ち、IDEの補完が効く
2. **バリデーションの自動化**: 不正な設定値を実行前に検出
3. **コードの可読性向上**: dict["key"]ではなくobj.fieldでアクセス
4. **保守性の向上**: データ構造の変更が型定義により追跡しやすい
5. **後方互換性の維持**: 既存のconfig.jsonはそのまま使用可能
