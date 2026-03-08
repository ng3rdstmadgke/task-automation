import json
import calendar
from datetime import date
import jpholiday
import os
from playwright.sync_api import sync_playwright
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
    hours: float = Field(gt=0)


class DaySchedule(BaseModel):
    """1日のスケジュール構造"""
    type: DayType
    tasks: list[Task]
    is_week_last_day: bool = False


class ScheduleResult(BaseModel):
    """calculate_scheduleの戻り値"""
    schedule: dict[int, DaySchedule]


def is_weekday(day: int, target_year: int, target_month: int) -> bool:
    d = date(target_year, target_month, day)
    # 土日または祝日の場合False（平日の場合True）
    if d.weekday() >= 5 or jpholiday.is_holiday(d):
        return False
    return True

def calculate_schedule(config: Config) -> ScheduleResult:
    target_year = config.target_year
    target_month = config.target_month
    paid_leave_days = config.paid_leave_days
    project_hours = config.project_hours
    
    num_days = calendar.monthrange(target_year, target_month)[1]
    
    workdays = []
    paid_days_set = set(paid_leave_days)
    
    for day in range(1, num_days + 1):
        if is_weekday(day, target_year, target_month):
            if day not in paid_days_set:
                workdays.append(day)
                
    # 週の最後の日（週報確定のため）を算出（月曜日始まり）
    valid_days = sorted(workdays + paid_leave_days)
    week_to_days = {}
    for day in valid_days:
        d = date(target_year, target_month, day)
        iso_year, iso_week, iso_weekday = d.isocalendar()
        week_key = (iso_year, iso_week)
        if week_key not in week_to_days:
            week_to_days[week_key] = []
        week_to_days[week_key].append(day)
        
    week_last_days = set([max(days) for days in week_to_days.values()])
    
    schedule = {}
    
    # 1. 有給日のスケジュールを設定
    for day in paid_leave_days:
        schedule[day] = DaySchedule(
            type=DayType.PAID_LEAVE,
            tasks=[Task(code="", content=TaskContent.PAID_LEAVE, hours=8)],
            is_week_last_day=day in week_last_days
        )
        
    # 2. 案件時間のキューを作成
    task_queue: list[Task] = []
    for project in project_hours:
        task_queue.append(Task(
            code=project.project_code,
            content=TaskContent.PROJECT_WORK,
            hours=project.hours
        ))
        
    # 3. 通常稼働日のスケジュールを設定
    for day in workdays:
        remaining_hours = 8.0
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

        schedule[day] = DaySchedule(
            type=DayType.WORKDAY,
            tasks=tasks_today,
            is_week_last_day=day in week_last_days
        )

    return ScheduleResult(schedule=schedule)

def run_automation(config: Config):
    result = calculate_schedule(config)
    schedule = result.schedule
    print(f"カレンダーと配分を計算しました: {config.target_year}年{config.target_month}月")
    
    with sync_playwright() as p:
        auth_file = "auth.json"
        
        # 認証状態のロード または 初回ログイン待機
        if os.path.exists(auth_file):
            print("既存のセッション（auth.json）を利用してログインをスキップします。")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=auth_file)
        else:
            print("auth.jsonが見つかりません。generate_auth.pyを実行してください。")
            return
            
        page = context.pages[0] if context.pages else context.new_page()

        # 指定月の日数分ループ
        for day in range(1, calendar.monthrange(config.target_year, config.target_month)[1] + 1):
            if day not in schedule:
                continue # 土日・祝日スキップ

            current_date = date(config.target_year, config.target_month, day)
            if current_date > date.today():
                print(f"{day}日は未来の日付のためスキップします。")
                continue

            print(f"--- {day}日 の処理を開始 ---")

            # 該当日付の日報ページに直接アクセス
            formatted_date = f"{config.target_year:04d}/{config.target_month:02d}/{day:02d}"
            url = f"https://secure.zac.ai/beex/b/asp/Shinsei/Nippou?date_nippou={formatted_date}"
            
            try:
                page.goto(url)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
                
                frame = page.frame_locator("#classic_window")
                
                # 日報フォームが表示されているか確認
                time_in_hour = frame.locator("select[name='time_in_hour']")
                if time_in_hour.count() == 0:
                    print(f"  {day}日の日報フォームが表示されませんでした。スキップします。")
                    continue
                    
                print(f"  {day}日の日報フォームを表示しました。")
                
            except Exception as e:
                print(f"  {day}日へのアクセスに失敗しました: {e}")
                continue
            
            day_info = schedule[day]
            
            try:
                # --- 出退勤時間の入力 ---
                # select_option()はvalue属性で選択（例: "9" → <option value="9">9</option>）
                if day_info.type == DayType.PAID_LEAVE:
                    frame.locator("select[name='time_in_hour']").select_option("9")
                    frame.locator("select[name='time_in_minute']").select_option("0")
                    frame.locator("select[name='time_out_hour']").select_option("17")
                    frame.locator("select[name='time_out_minute']").select_option("0")

                    frame.locator("select[name='time_break_input_hour']").select_option("0")
                    frame.locator("select[name='time_break_input_minute']").select_option("0")
                elif day_info.type == DayType.WORKDAY:
                    frame.locator("select[name='time_in_hour']").select_option("9")
                    frame.locator("select[name='time_in_minute']").select_option("0")
                    frame.locator("select[name='time_out_hour']").select_option("18")
                    frame.locator("select[name='time_out_minute']").select_option("0")

                    frame.locator("select[name='time_break_input_hour']").select_option("1")
                    frame.locator("select[name='time_break_input_minute']").select_option("0")
            except Exception as e:
                print(f"  時間の入力に失敗しました: {e}")
                continue
                
            # --- 案件の入力 ---
            content_dict = {
                "1": "案件作業",
                "27": "有給・リフレッシュ・特別休暇",
                "55": "自己啓発",
            }
            for i, task in enumerate(day_info.tasks):
                print(f"  > 入力項目: value={content_dict[task.content.value]} プロジェクトコード={task.code} ({task.hours}時間)")
                try:
                    row_num = i + 1  # 行番号は1から始まる

                    # 作業内容をセレクトボックスでvalue属性で選択（例: "1"=案件作業, "55"=自己啓発, "27"=有給）
                    frame.locator(f"select[name='id_sagyou_naiyou{row_num}']").select_option(task.content.value)
                    page.wait_for_timeout(2000)  # 作業内容選択後のJavaScript処理を待つ

                    if task.code:
                        # 案件コードを入力してTabキーでフォーカスを外し、読み込みを発生させる
                        frame.locator(f"input[name='code_project{row_num}']").fill(task.code)
                        frame.locator(f"input[name='code_project{row_num}']").press("Tab")
                        page.wait_for_timeout(2000)  # 非同期の名称自動表示を待つ

                    # 所要時間（時）- value属性で選択
                    frame.locator(f"select[name='time_required_hour{row_num}']").select_option(str(int(task.hours)))
                    # 所要時間（分）- value属性で選択
                    frame.locator(f"select[name='time_required_minute{row_num}']").select_option("0")

                except Exception as e:
                    print(f"  案件行 {i+1} の入力中にエラーが発生しました: {e}")
                    
            # --- 日報の確定 ---
            # 確定ボタン（id="button7"）をクリック
            confirm_btn = frame.locator("input#button7")
            if confirm_btn.count() > 0:
                print("  確定ボタンをクリックします...")
                confirm_btn.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
                print("  確定処理完了")
                
                # --- 週報の確定（週の最後の日のみ） ---
                #if day_info.is_week_last_day:
                #    # 週の確定で再度画面がリフレッシュされる場合がある
                #    frame = page.frame_locator("#classic_window")
                #    # 週報確定ボタンにはidやnameがないため、valueで判定
                #    weekly_confirm = frame.locator("input[value='週報確定']")
                #    if weekly_confirm.count() > 0:
                #        print("  [週報] 週報確定ボタンをクリックします...")
                #        weekly_confirm.click()
                #        page.wait_for_load_state("networkidle")
                #        page.wait_for_timeout(3000)
                #        print(f"  [週報] {day}日は週の最後のため、週報を確定しました。")
            
            print(f"{day}日の処理完了。")

        print("指定された月の処理がすべて完了しました！ブラウザを閉じます。")

if __name__ == "__main__":
    with open("config.json", "r", encoding="utf-8") as f:
        config_dict = json.load(f)
    config = Config(**config_dict)
    run_automation(config)
