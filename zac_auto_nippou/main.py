import json
import calendar
from datetime import date
import jpholiday
import os
from playwright.sync_api import sync_playwright


def is_workday_or_paid(day, target_year, target_month, paid_leave_days):
    d = date(target_year, target_month, day)
    # 土日 または 祝日 は対象外
    if d.weekday() >= 5 or jpholiday.is_holiday(d):
        return False
    return True

def calculate_schedule(config):
    target_year = config["target_year"]
    target_month = config["target_month"]
    paid_leave_days = config["paid_leave_days"]
    project_hours = config["project_hours"]
    
    num_days = calendar.monthrange(target_year, target_month)[1]
    
    workdays = []
    paid_days_set = set(paid_leave_days)
    
    for day in range(1, num_days + 1):
        if is_workday_or_paid(day, target_year, target_month, paid_leave_days):
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
        schedule[day] = {
            "type": "paid_leave",
            # contentはid_sagyou_naiyouのvalue属性（27="有給・リフレッシュ・特別休暇"）
            "tasks": [{"code": "", "content": "27", "hours": 8}]
        }
        
    # 2. 案件時間のキューを作成
    task_queue = []
    for code, hours in project_hours.items():
        # contentはid_sagyou_naiyouのvalue属性（1="案件作業"）
        task_queue.append({"code": code, "content": "1", "hours": hours})
        
    # 3. 通常稼働日のスケジュールを設定
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
            
        schedule[day] = {
            "type": "workday",
            "tasks": tasks_today
        }
        
    return schedule, week_last_days

def run_automation(config):
    schedule, week_last_days = calculate_schedule(config)
    print(f"カレンダーと配分を計算しました: {config['target_year']}年{config['target_month']}月")
    
    with sync_playwright() as p:
        auth_file = "auth.json"
        
        # 認証状態のロード または 初回ログイン待機
        if os.path.exists(auth_file):
            print("既存のセッション（auth.json）を利用してログインをスキップします。")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=auth_file)
        else:
            print("auth.jsonが見つかりません。初回はホストマシンのローカル環境でスクリプトを実行し、作成されたauth.jsonを共有してください。")
            # Docker環境でGUIは出せないため、ここで終了するかHeadlessで処理可能な自動ログインを組む必要があります。
            # 今回は事前に用意した auth.json がある前提とします。
            print("Docker環境のHeadlessモードでは手動ログインができないため処理を中断します。")
            return
            
            # 手動でローカル作成する場合は以下を使用します（参考）
            # browser = p.chromium.launch(headless=False)
            # context = browser.new_context()
            # page = context.new_page()
            # page.goto("https://secure.zac.ai/beex/b/asp/Shinsei/Nippou")
            # print("ブラウザ上でログインを完了させてください。日報画面を検知するまで待機します...")
            # page.wait_for_url("**/asp/Shinsei/Nippou**", timeout=0)
            # context.storage_state(path=auth_file)
            
        page = context.pages[0] if context.pages else context.new_page()

        if page.url.find("Nippou") == -1:
             page.goto("https://secure.zac.ai/beex/b/asp/Shinsei/Nippou")
             page.wait_for_load_state("networkidle")
             page.wait_for_timeout(2000)  # 画面が安定するまで待機

        # 指定月の日数分ループ
        for day in range(1, calendar.monthrange(config["target_year"], config["target_month"])[1] + 1):
            if day not in schedule:
                continue # 土日・祝日スキップ
                
            current_date = date(config["target_year"], config["target_month"], day)
            if current_date > date.today():
                print(f"{day}日は未来の日付のためスキップします。")
                continue
                
            print(f"--- {day}日 の処理を開始 ---")
            
            try:
                # iframe "classic_window" を特定
                frame = page.frame_locator("#classic_window")

                # DOMが安定するまで少し待機
                page.wait_for_timeout(500)

                # 左の小さなカレンダー表から日付リンクをクリック
                day_str = str(day)

                # カレンダー内のリンクを.count()と.nth()で処理（.all()を使わない）
                calendar_locator = frame.locator("table td a")
                link_count = calendar_locator.count()
                clicked = False

                import re
                for i in range(link_count):
                    try:
                        # 毎回nth()で取得（DOMの最新状態を反映）
                        link = calendar_locator.nth(i)
                        text = link.text_content().strip()
                        match = re.match(r'^(\d+)', text)
                        if match:
                            number = match.group(1)
                            if number == day_str:
                                # クリック
                                link.click()
                                page.wait_for_load_state("networkidle")
                                page.wait_for_timeout(3000)  # 画面遷移後の安定化待機（3秒）
                                clicked = True
                                break
                    except:
                        continue

                if not clicked:
                    print(f"{day}日 のリンクが見つかりませんでした。")
            except Exception as e:
                print(f"{day}日 の画面遷移に失敗しました: {e}")
                continue
                
            # iframe を再取得（画面遷移でリロードされている可能性があるため）
            frame = page.frame_locator("#classic_window")

            day_info = schedule[day]
            
            try:
                # --- 出退勤時間の入力 ---
                # select_option()はvalue属性で選択（例: "9" → <option value="9">9</option>）
                if day_info["type"] == "paid_leave":
                    frame.locator("select[name='time_in_hour']").select_option("9")
                    frame.locator("select[name='time_in_minute']").select_option("0")
                    frame.locator("select[name='time_out_hour']").select_option("17")
                    frame.locator("select[name='time_out_minute']").select_option("0")
                    frame.locator("select[name='time_break_input_hour']").select_option("0")
                    frame.locator("select[name='time_break_input_minute']").select_option("0")
                elif day_info["type"] == "workday":
                    frame.locator("select[name='time_in_hour']").select_option(config["default_times"]["arrival"])
                    frame.locator("select[name='time_in_minute']").select_option("0")
                    frame.locator("select[name='time_out_hour']").select_option(config["default_times"]["departure"])
                    frame.locator("select[name='time_out_minute']").select_option("0")
                    frame.locator("select[name='time_break_input_hour']").select_option(config["default_times"]["break"])
                    frame.locator("select[name='time_break_input_minute']").select_option("0")
            except Exception as e:
                print(f"時間の入力に失敗しましたが、一旦続行します。詳細: {e}")
                continue
                
            # --- 案件の入力 ---
            content_dict = {
                "1": "案件作業",
                "27": "有給・リフレッシュ・特別休暇",
                "55": "自己啓発",
            }
            for i, task in enumerate(day_info["tasks"]):
                print(f"  > 入力項目: value={content_dict[task['content']]} プロジェクトコード={task['code']} ({task['hours']}時間)")
                try:
                    row_num = i + 1  # 行番号は1から始まる

                    # 作業内容をセレクトボックスでvalue属性で選択（例: "1"=案件作業, "55"=自己啓発, "27"=有給）
                    frame.locator(f"select[name='id_sagyou_naiyou{row_num}']").select_option(task["content"])

                    if task["code"]:
                        # 案件コードを入力してTabキーでフォーカスを外し、読み込みを発生させる
                        frame.locator(f"input[name='code_project{row_num}']").fill(task["code"])
                        frame.locator(f"input[name='code_project{row_num}']").press("Tab")
                        page.wait_for_timeout(1000)  # 非同期の名称自動表示を待つ

                    # 所要時間（時）
                    frame.locator(f"select[name='time_required_hour{row_num}']").select_option(str(task["hours"]))
                    # 所要時間（分）
                    frame.locator(f"select[name='time_required_minute{row_num}']").select_option("0")

                except Exception as e:
                    print(f"案件行 {i+1} の入力中にエラーが発生しました。セレクタの調整が必要かもしれません。: {e}")
                    
            # --- 日報の確定 ---
            # 確定ボタン（id="button7"）をクリック
            confirm_btn = frame.locator("input#button7")
            if confirm_btn.count() > 0:
                print("  確定ボタンをクリックします...")
                confirm_btn.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(1000)
                print("  確定処理完了")
                
                # --- 週報の確定（週の最後の日のみ） ---
                #if day in week_last_days:
                #    # 週の確定で再度画面がリフレッシュされる場合がある
                #    frame = page.frame_locator("#classic_window")
                #    # 週報確定ボタンにはidやnameがないため、valueで判定
                #    weekly_confirm = frame.locator("input[value='週報確定']")
                #    if weekly_confirm.count() > 0:
                #        print("  [週報] 週報確定ボタンをクリックします...")
                #        weekly_confirm.click()
                #        page.wait_for_load_state("networkidle")
                #        page.wait_for_timeout(1000)
                #        print(f"  [週報] {day}日は週の最後のため、週報を確定しました。")
            
            print(f"{day}日の処理完了。")

            # 次の日付選択の前に待機（画面が安定するまで）
            page.wait_for_timeout(2000)

        print("指定された月の処理がすべて完了しました！ブラウザを閉じます。")

if __name__ == "__main__":
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    run_automation(config)
