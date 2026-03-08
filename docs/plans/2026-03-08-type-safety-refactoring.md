# Type Safety Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor `main.py` and `generate_auth.py` to use Pydantic models for type safety, replacing all dict-based data structures with typed models.

**Architecture:** Add Pydantic model definitions at the top of each file. Convert all dict arguments and return values to typed Pydantic models. Replace `python-dotenv` with `pydantic-settings` for environment variable handling. Maintain backward compatibility for `config.json` format.

**Tech Stack:** Python 3.12, Pydantic 2.x, pydantic-settings, Playwright

---

## Task 1: Update Dependencies

**Files:**
- Modify: `pyproject.toml` (dependencies section)

**Step 1: Remove python-dotenv and add pydantic packages**

Run:
```bash
cd /workspaces/task-automation
uv remove python-dotenv
uv add pydantic pydantic-settings
```

Expected: Dependencies updated successfully

**Step 2: Verify dependencies**

Run:
```bash
uv pip list | grep -E "(pydantic|dotenv)"
```

Expected: Shows `pydantic` and `pydantic-settings`, no `python-dotenv`

**Step 3: Commit dependency changes**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: replace python-dotenv with pydantic-settings

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Refactor generate_auth.py - Add Pydantic Models

**Files:**
- Modify: `zac_auto_nippou/generate_auth.py:1-14`

**Step 1: Add Pydantic model at top of file**

Replace the imports section (lines 1-3) with:

```python
import os
from playwright.sync_api import sync_playwright
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class ZacCredentials(BaseSettings):
    """環境変数（.env）の構造"""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    zac_id: str = Field(min_length=1)
    zac_password: str = Field(min_length=1)
```

**Step 2: Verify syntax**

Run:
```bash
cd /workspaces/task-automation
python -m py_compile zac_auto_nippou/generate_auth.py
```

Expected: No syntax errors

**Step 3: Commit model addition**

```bash
git add zac_auto_nippou/generate_auth.py
git commit -m "feat: add ZacCredentials Pydantic model to generate_auth.py

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Refactor generate_auth.py - Use Pydantic Model

**Files:**
- Modify: `zac_auto_nippou/generate_auth.py:5-14` (inside `login_and_save_auth` function)

**Step 1: Replace dotenv with Pydantic settings**

Replace lines 6-14 (from `load_dotenv()` to `return`) with:

```python
    try:
        credentials = ZacCredentials()
    except ValidationError as e:
        print("エラー: .envファイルにZAC_IDとZAC_PASSWORDを設定してください。")
        print(".env.sampleを参考に.envファイルを作成してください。")
        print(f"詳細: {e}")
        return

    zac_id = credentials.zac_id
    zac_password = credentials.zac_password
```

**Step 2: Test the refactored file**

Run:
```bash
cd /workspaces/task-automation
uv run python -c "from zac_auto_nippou.generate_auth import login_and_save_auth; print('Import successful')"
```

Expected: "Import successful" (no import errors)

**Step 3: Commit the changes**

```bash
git add zac_auto_nippou/generate_auth.py
git commit -m "refactor: use ZacCredentials model for environment variables

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Refactor main.py - Add Enum Definitions

**Files:**
- Modify: `zac_auto_nippou/main.py:1-6`

**Step 1: Add imports and enum definitions**

After the existing imports (after line 6), add:

```python
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class DayType(str, Enum):
    """日のタイプ"""
    PAID_LEAVE = "paid_leave"
    WORKDAY = "workday"


class TaskContent(str, Enum):
    """作業内容の種類（ZACのid_sagyou_naiyouのvalue値）"""
    PROJECT_WORK = "1"           # 案件作業
    PAID_LEAVE = "27"            # 有給・リフレッシュ・特別休暇
    SELF_DEVELOPMENT = "55"      # 自己啓発
```

**Step 2: Verify syntax**

Run:
```bash
cd /workspaces/task-automation
python -m py_compile zac_auto_nippou/main.py
```

Expected: No syntax errors

**Step 3: Commit enum definitions**

```bash
git add zac_auto_nippou/main.py
git commit -m "feat: add DayType and TaskContent enums

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Refactor main.py - Add Data Model Definitions

**Files:**
- Modify: `zac_auto_nippou/main.py` (after enum definitions)

**Step 1: Add Pydantic model definitions**

After the enum definitions, add:

```python
class ProjectAllocation(BaseModel):
    """プロジェクトへの工数配分"""
    project_code: str
    hours: float = Field(gt=0)


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


class Task(BaseModel):
    """個別タスクの構造"""
    code: str
    content: TaskContent
    hours: float = Field(gt=0, le=24)


class DaySchedule(BaseModel):
    """1日のスケジュール構造"""
    type: DayType
    tasks: list[Task]
    is_week_last_day: bool = False


class ScheduleResult(BaseModel):
    """calculate_scheduleの戻り値"""
    schedule: dict[int, DaySchedule]
```

**Step 2: Verify syntax**

Run:
```bash
cd /workspaces/task-automation
python -m py_compile zac_auto_nippou/main.py
```

Expected: No syntax errors

**Step 3: Commit model definitions**

```bash
git add zac_auto_nippou/main.py
git commit -m "feat: add Pydantic models for main.py data structures

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Refactor main.py - Update is_weekday Function Signature

**Files:**
- Modify: `zac_auto_nippou/main.py:8` (function definition line)

**Step 1: Add type hints to is_weekday**

Change line 8 from:
```python
def is_weekday(day, target_year, target_month):
```

To:
```python
def is_weekday(day: int, target_year: int, target_month: int) -> bool:
```

**Step 2: Verify syntax**

Run:
```bash
cd /workspaces/task-automation
python -m py_compile zac_auto_nippou/main.py
```

Expected: No syntax errors

**Step 3: Commit type hint addition**

```bash
git add zac_auto_nippou/main.py
git commit -m "refactor: add type hints to is_weekday function

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Refactor main.py - Update calculate_schedule Signature and Config Access

**Files:**
- Modify: `zac_auto_nippou/main.py:15-20` (function signature and initial variable assignments)

**Step 1: Update function signature and config access**

Change lines 15-19 from:
```python
def calculate_schedule(config):
    target_year = config["target_year"]
    target_month = config["target_month"]
    paid_leave_days = config["paid_leave_days"]
    project_hours = config["project_hours"]
```

To:
```python
def calculate_schedule(config: Config) -> ScheduleResult:
    target_year = config.target_year
    target_month = config.target_month
    paid_leave_days = config.paid_leave_days
    project_hours = config.project_hours
```

**Step 2: Verify syntax**

Run:
```bash
cd /workspaces/task-automation
python -m py_compile zac_auto_nippou/main.py
```

Expected: No syntax errors

**Step 3: Commit signature and access pattern update**

```bash
git add zac_auto_nippou/main.py
git commit -m "refactor: update calculate_schedule signature and config access

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Refactor main.py - Convert Paid Leave Tasks to Pydantic Models

**Files:**
- Modify: `zac_auto_nippou/main.py:46-52` (paid leave schedule creation)

**Step 1: Replace dict with DaySchedule model**

Change lines 47-52 from:
```python
    for day in paid_leave_days:
        schedule[day] = {
            "type": "paid_leave",
            # contentはid_sagyou_naiyouのvalue属性（27="有給・リフレッシュ・特別休暇"）
            "tasks": [{"code": "", "content": "27", "hours": 8}]
        }
```

To:
```python
    for day in paid_leave_days:
        schedule[day] = DaySchedule(
            type=DayType.PAID_LEAVE,
            tasks=[Task(code="", content=TaskContent.PAID_LEAVE, hours=8)]
        )
```

**Step 2: Verify syntax**

Run:
```bash
cd /workspaces/task-automation
python -m py_compile zac_auto_nippou/main.py
```

Expected: No syntax errors

**Step 3: Commit paid leave conversion**

```bash
git add zac_auto_nippou/main.py
git commit -m "refactor: convert paid leave tasks to Pydantic models

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Refactor main.py - Convert Task Queue to Pydantic Models

**Files:**
- Modify: `zac_auto_nippou/main.py:54-58` (task queue creation)

**Step 1: Replace dict with Task model**

Change lines 55-58 from:
```python
    task_queue = []
    for code, hours in project_hours.items():
        # contentはid_sagyou_naiyouのvalue属性（1="案件作業"）
        task_queue.append({"code": code, "content": "1", "hours": hours})
```

To:
```python
    task_queue: list[Task] = []
    for project in project_hours:
        task_queue.append(Task(
            code=project.project_code,
            content=TaskContent.PROJECT_WORK,
            hours=project.hours
        ))
```

**Step 2: Verify syntax**

Run:
```bash
cd /workspaces/task-automation
python -m py_compile zac_auto_nippou/main.py
```

Expected: No syntax errors

**Step 3: Commit task queue conversion**

```bash
git add zac_auto_nippou/main.py
git commit -m "refactor: convert task queue to use Task models

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Refactor main.py - Convert Workday Task Creation to Pydantic Models

**Files:**
- Modify: `zac_auto_nippou/main.py:61-79` (workday loop task creation)

**Step 1: Update task creation in workday loop**

Change lines 61-79 from:
```python
    for day in workdays:
        remaining_hours = 8
        tasks_today = []

        while remaining_hours > 0 and task_queue:
            task = task_queue[0]
            if task["hours"] <= remaining_hours:
                tasks_today.append({"code": task["code"], "content": task["content"], "hours": task["hours"]})
                remaining_hours -= task["hours"]
                task_queue.pop(0)  # 使い切った案件はキューから削除
            else:
                tasks_today.append({"code": task["code"], "content": task["content"], "hours": remaining_hours})
                task["hours"] -= remaining_hours
                remaining_hours = 0

        # もし時間が余ったら自己啓発で埋める
        if remaining_hours > 0:
            # contentはid_sagyou_naiyouのvalue属性（55="自己啓発"）
            tasks_today.append({"code": "", "content": "55", "hours": remaining_hours})
```

To:
```python
    for day in workdays:
        remaining_hours = 8
        tasks_today: list[Task] = []

        while remaining_hours > 0 and task_queue:
            task = task_queue[0]
            if task.hours <= remaining_hours:
                tasks_today.append(Task(code=task.code, content=task.content, hours=task.hours))
                remaining_hours -= task.hours
                task_queue.pop(0)  # 使い切った案件はキューから削除
            else:
                tasks_today.append(Task(code=task.code, content=task.content, hours=remaining_hours))
                task.hours -= remaining_hours
                remaining_hours = 0

        # もし時間が余ったら自己啓発で埋める
        if remaining_hours > 0:
            tasks_today.append(Task(code="", content=TaskContent.SELF_DEVELOPMENT, hours=remaining_hours))
```

**Step 2: Verify syntax**

Run:
```bash
cd /workspaces/task-automation
python -m py_compile zac_auto_nippou/main.py
```

Expected: No syntax errors

**Step 3: Commit workday task conversion**

```bash
git add zac_auto_nippou/main.py
git commit -m "refactor: convert workday task creation to Task models

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 11: Refactor main.py - Update DaySchedule Creation and Return Value

**Files:**
- Modify: `zac_auto_nippou/main.py:81-86` (schedule assignment and return statement)

**Step 1: Replace dict with DaySchedule and update return**

Change lines 81-86 from:
```python
        schedule[day] = {
            "type": "workday",
            "tasks": tasks_today
        }

    return schedule, week_last_days
```

To:
```python
        schedule[day] = DaySchedule(
            type=DayType.WORKDAY,
            tasks=tasks_today
        )

    # week_last_daysをis_week_last_dayフラグとして各DayScheduleに設定
    for day in week_last_days:
        if day in schedule:
            schedule[day].is_week_last_day = True

    return ScheduleResult(schedule=schedule)
```

**Step 2: Verify syntax**

Run:
```bash
cd /workspaces/task-automation
python -m py_compile zac_auto_nippou/main.py
```

Expected: No syntax errors

**Step 3: Commit schedule creation and return value update**

```bash
git add zac_auto_nippou/main.py
git commit -m "refactor: use DaySchedule model and ScheduleResult return type

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 12: Refactor main.py - Update run_automation Signature and Schedule Access

**Files:**
- Modify: `zac_auto_nippou/main.py:88-109` (function signature and initial schedule usage)

**Step 1: Update function signature and schedule variable**

Change lines 88-89 from:
```python
def run_automation(config):
    schedule, week_last_days = calculate_schedule(config)
```

To:
```python
def run_automation(config: Config) -> None:
    result = calculate_schedule(config)
```

Also update line 90 from:
```python
    print(f"カレンダーと配分を計算しました: {config['target_year']}年{config['target_month']}月")
```

To:
```python
    print(f"カレンダーと配分を計算しました: {config.target_year}年{config.target_month}月")
```

And update line 107 from:
```python
        for day in range(1, calendar.monthrange(config["target_year"], config["target_month"])[1] + 1):
            if day not in schedule:
```

To:
```python
        for day in range(1, calendar.monthrange(config.target_year, config.target_month)[1] + 1):
            if day not in result.schedule:
```

And update line 111 from:
```python
            current_date = date(config["target_year"], config["target_month"], day)
```

To:
```python
            current_date = date(config.target_year, config.target_month, day)
```

And update line 119 from:
```python
            formatted_date = f"{config['target_year']:04d}/{config['target_month']:02d}/{day:02d}"
```

To:
```python
            formatted_date = f"{config.target_year:04d}/{config.target_month:02d}/{day:02d}"
```

And update line 141 from:
```python
            day_info = schedule[day]
```

To:
```python
            day_info = result.schedule[day]
```

**Step 2: Verify syntax**

Run:
```bash
cd /workspaces/task-automation
python -m py_compile zac_auto_nippou/main.py
```

Expected: No syntax errors

**Step 3: Commit signature and access updates**

```bash
git add zac_auto_nippou/main.py
git commit -m "refactor: update run_automation signature and schedule access

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 13: Refactor main.py - Update Day Info Type Checks

**Files:**
- Modify: `zac_auto_nippou/main.py:143-164` (day_info type checking)

**Step 1: Replace string comparison with enum comparison**

Change lines 146 and 154 from:
```python
                if day_info["type"] == "paid_leave":
```
and
```python
                elif day_info["type"] == "workday":
```

To:
```python
                if day_info.type == DayType.PAID_LEAVE:
```
and
```python
                elif day_info.type == DayType.WORKDAY:
```

**Step 2: Verify syntax**

Run:
```bash
cd /workspaces/task-automation
python -m py_compile zac_auto_nippou/main.py
```

Expected: No syntax errors

**Step 3: Commit type check updates**

```bash
git add zac_auto_nippou/main.py
git commit -m "refactor: use DayType enum for type checks

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 14: Refactor main.py - Update Task Iteration and Access

**Files:**
- Modify: `zac_auto_nippou/main.py:166-194` (task iteration loop)

**Step 1: Update task access from dict to model attributes**

Change line 172 from:
```python
            for i, task in enumerate(day_info["tasks"]):
```

To:
```python
            for i, task in enumerate(day_info.tasks):
```

Change line 173 from:
```python
                print(f"  > 入力項目: value={content_dict[task['content']]} プロジェクトコード={task['code']} ({task['hours']}時間)")
```

To:
```python
                print(f"  > 入力項目: value={content_dict[task.content.value]} プロジェクトコード={task.code} ({task.hours}時間)")
```

Change line 178 from:
```python
                    frame.locator(f"select[name='id_sagyou_naiyou{row_num}']").select_option(task["content"])
```

To:
```python
                    frame.locator(f"select[name='id_sagyou_naiyou{row_num}']").select_option(task.content.value)
```

Change lines 181-182 from:
```python
                    if task["code"]:
                        frame.locator(f"input[name='code_project{row_num}']").fill(task["code"])
```

To:
```python
                    if task.code:
                        frame.locator(f"input[name='code_project{row_num}']").fill(task.code)
```

Change line 188 from:
```python
                    frame.locator(f"select[name='time_required_hour{row_num}']").select_option(str(task["hours"]))
```

To:
```python
                    frame.locator(f"select[name='time_required_hour{row_num}']").select_option(str(int(task.hours)))
```

**Step 2: Verify syntax**

Run:
```bash
cd /workspaces/task-automation
python -m py_compile zac_auto_nippou/main.py
```

Expected: No syntax errors

**Step 3: Commit task access updates**

```bash
git add zac_auto_nippou/main.py
git commit -m "refactor: update task iteration to use Task model attributes

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 15: Refactor main.py - Update Main Block to Use Config Model

**Files:**
- Modify: `zac_auto_nippou/main.py:222-225` (main block)

**Step 1: Update config loading to use Pydantic model**

Change lines 223-225 from:
```python
if __name__ == "__main__":
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    run_automation(config)
```

To:
```python
if __name__ == "__main__":
    with open("config.json", "r", encoding="utf-8") as f:
        config_dict = json.load(f)
    config = Config(**config_dict)
    run_automation(config)
```

**Step 2: Verify syntax**

Run:
```bash
cd /workspaces/task-automation
python -m py_compile zac_auto_nippou/main.py
```

Expected: No syntax errors

**Step 3: Commit main block update**

```bash
git add zac_auto_nippou/main.py
git commit -m "refactor: use Config model in main block

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 16: Verify generate_auth.py Functionality

**Files:**
- Test: `zac_auto_nippou/generate_auth.py`

**Step 1: Test import and model validation**

Run:
```bash
cd /workspaces/task-automation
uv run python -c "
from zac_auto_nippou.generate_auth import ZacCredentials, login_and_save_auth
print('✓ Imports successful')
print('✓ ZacCredentials model available')
print('✓ login_and_save_auth function available')
"
```

Expected: All checkmarks printed, no errors

**Step 2: Test with missing credentials (expected to fail gracefully)**

Run:
```bash
cd /workspaces/task-automation
# Temporarily rename .env if it exists
if [ -f zac_auto_nippou/.env ]; then mv zac_auto_nippou/.env zac_auto_nippou/.env.backup; fi
cd zac_auto_nippou && uv run python -c "
from generate_auth import ZacCredentials
from pydantic import ValidationError
try:
    creds = ZacCredentials()
    print('ERROR: Should have raised ValidationError')
except ValidationError as e:
    print('✓ ValidationError raised correctly for missing credentials')
"
# Restore .env if it was backed up
if [ -f zac_auto_nippou/.env.backup ]; then mv zac_auto_nippou/.env.backup zac_auto_nippou/.env; fi
```

Expected: "✓ ValidationError raised correctly for missing credentials"

**Step 3: Document verification success**

No commit needed (verification only)

---

## Task 17: Verify main.py Functionality

**Files:**
- Test: `zac_auto_nippou/main.py`

**Step 1: Test imports and model definitions**

Run:
```bash
cd /workspaces/task-automation
uv run python -c "
from zac_auto_nippou.main import (
    DayType, TaskContent, ProjectAllocation, Config,
    Task, DaySchedule, ScheduleResult,
    is_weekday, calculate_schedule, run_automation
)
print('✓ All imports successful')
print('✓ All models available')
print('✓ All functions available')
"
```

Expected: All checkmarks printed, no errors

**Step 2: Test Config model with sample data**

Run:
```bash
cd /workspaces/task-automation
uv run python -c "
from zac_auto_nippou.main import Config, ProjectAllocation
import json

# Test with dict format (backward compatibility)
config_dict = {
    'target_year': 2026,
    'target_month': 3,
    'paid_leave_days': [6],
    'project_hours': {'PJ001': 20, 'PJ002': 4}
}
config = Config(**config_dict)
print('✓ Config model created from dict format')
print(f'  - Year: {config.target_year}')
print(f'  - Month: {config.target_month}')
print(f'  - Paid leave days: {config.paid_leave_days}')
print(f'  - Projects: {len(config.project_hours)} allocations')
for proj in config.project_hours:
    print(f'    - {proj.project_code}: {proj.hours}h')
"
```

Expected: Config model created successfully, all values printed correctly

**Step 3: Test calculate_schedule function**

Run:
```bash
cd /workspaces/task-automation
uv run python -c "
from zac_auto_nippou.main import Config, calculate_schedule
from datetime import date

config_dict = {
    'target_year': 2026,
    'target_month': 3,
    'paid_leave_days': [6],
    'project_hours': {'PJ001': 16, 'PJ002': 8}
}
config = Config(**config_dict)
result = calculate_schedule(config)

print('✓ calculate_schedule executed successfully')
print(f'  - Schedule has {len(result.schedule)} days')
print(f'  - Sample day 6 (paid leave): type={result.schedule[6].type}')
print(f'  - Sample day 6 tasks: {len(result.schedule[6].tasks)} task(s)')
if 2 in result.schedule:
    print(f'  - Sample day 2 (workday): type={result.schedule[2].type}')
    print(f'  - Sample day 2 tasks: {len(result.schedule[2].tasks)} task(s)')
"
```

Expected: Schedule calculated successfully, sample values printed

**Step 4: Document verification success**

No commit needed (verification only)

---

## Task 18: Full Integration Test

**Files:**
- Test: `zac_auto_nippou/generate_auth.py`
- Test: `zac_auto_nippou/main.py`

**Step 1: Run generate_auth.py (requires .env file)**

Run:
```bash
cd /workspaces/task-automation
uv run python zac_auto_nippou/generate_auth.py
```

Expected:
- If .env exists: Authentication process starts
- If .env missing: Clear error message about missing credentials
- No import errors or type errors

**Step 2: Run main.py (requires config.json and auth.json)**

Run:
```bash
cd /workspaces/task-automation
uv run python zac_auto_nippou/main.py
```

Expected:
- If config.json and auth.json exist: Automation process starts
- If files missing: Clear error message
- No import errors, no type errors, Pydantic models work correctly

**Step 3: Commit integration test documentation**

```bash
git add -A
git commit -m "test: verify full integration of type-safe refactoring

Both generate_auth.py and main.py execute without errors.
All Pydantic models validate correctly.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 19: Update Documentation

**Files:**
- Modify: `zac_auto_nippou/README.md:5-13`

**Step 1: Update dependencies section**

After line 8 (after `## 実行方法 (ローカル)`), verify that the dependencies section accurately reflects the changes:

The current text mentions `uv sync` which will install the new dependencies. No changes needed unless we want to explicitly mention the Pydantic dependency.

**Step 2: Add migration notes (optional)**

If desired, add a note about the refactoring at the end of README.md:

```markdown

## 変更履歴

### 2026-03-08: 型安全性の向上

- `python-dotenv` を `pydantic-settings` に置き換え
- すべてのデータ構造をPydanticモデルに変換
- 関数の型ヒントを追加
- 既存の`config.json`形式との後方互換性を維持
```

**Step 3: Commit documentation update**

```bash
git add zac_auto_nippou/README.md
git commit -m "docs: add migration notes for type safety refactoring

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 20: Final Verification and Cleanup

**Files:**
- Review: All modified files

**Step 1: Run final syntax check on all Python files**

Run:
```bash
cd /workspaces/task-automation
python -m py_compile zac_auto_nippou/generate_auth.py
python -m py_compile zac_auto_nippou/main.py
echo "✓ All files compile successfully"
```

Expected: "✓ All files compile successfully"

**Step 2: Verify all commits are present**

Run:
```bash
cd /workspaces/task-automation
git log --oneline --since="2026-03-08" | head -20
```

Expected: List of commits from this refactoring session

**Step 3: Run full end-to-end test**

Run:
```bash
cd /workspaces/task-automation
# This will test the full workflow if .env and config.json are properly set up
uv run python zac_auto_nippou/generate_auth.py && uv run python zac_auto_nippou/main.py
```

Expected: Both scripts execute without type errors or import errors

**Step 4: Create final summary commit if needed**

Only if there are uncommitted changes:
```bash
git add -A
git commit -m "chore: final cleanup after type safety refactoring

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Completion Checklist

- [ ] Dependencies updated (python-dotenv removed, pydantic added)
- [ ] generate_auth.py refactored with ZacCredentials model
- [ ] main.py enums defined (DayType, TaskContent)
- [ ] main.py Pydantic models defined (Config, Task, DaySchedule, etc.)
- [ ] All function signatures updated with type hints
- [ ] calculate_schedule uses Config input and returns ScheduleResult
- [ ] run_automation uses typed models throughout
- [ ] All dict access converted to model attribute access
- [ ] Backward compatibility maintained for config.json
- [ ] Integration tests pass
- [ ] Documentation updated
- [ ] All changes committed

## Success Criteria

1. ✅ `uv run python zac_auto_nippou/generate_auth.py` executes without errors
2. ✅ `uv run python zac_auto_nippou/main.py` executes without errors
3. ✅ All Pydantic models validate input data correctly
4. ✅ Existing `config.json` format still works (backward compatibility)
5. ✅ Type hints enable IDE autocomplete and type checking
6. ✅ All commits follow conventional commit format
