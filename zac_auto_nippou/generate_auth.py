import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

def login_and_save_auth():
    # .envファイルから環境変数を読み込む
    load_dotenv()
    zac_id = os.getenv("ZAC_ID")
    zac_password = os.getenv("ZAC_PASSWORD")

    if not zac_id or not zac_password:
        print("エラー: .envファイルにZAC_IDとZAC_PASSWORDを設定してください。")
        print(".env.sampleを参考に.envファイルを作成してください。")
        return

    with sync_playwright() as p:
        # ヘッドレスモードで起動（headless=Falseにするとブラウザが表示されます）
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("ZACのログイン画面を開きます...")
        page.goto("https://secure.zac.ai/beex/b/asp/Shinsei/Nippou")

        # 第1段階: 社外接続の認証
        print("第1段階: 社外接続の認証を行います...")
        try:
            # ログインIDを入力
            login_id_input = page.get_by_role("textbox", name="ログインID")
            login_id_input.fill(zac_id)

            # パスワードを入力
            password_input = page.get_by_role("textbox", name="パスワード")
            password_input.fill(zac_password)

            # 接続ボタンをクリック
            connect_button = page.get_by_role("button", name="接続")
            connect_button.click()

            print("第1段階のログイン処理を送信しました。画面遷移を待機中...")
            page.wait_for_load_state("networkidle")

        except Exception as e:
            print(f"第1段階のログインに失敗しました: {e}")
            browser.close()
            return

        # 第2段階: ZACの通常ログイン（必要な場合）
        print(f"現在のURL: {page.url}")

        # URLに"user_logon"が含まれている場合は、さらにログインが必要
        if "user_logon" in page.url or "LogOn" in page.url:
            print("第2段階: ZACの通常ログインを行います...")
            try:
                # ページの状態を確認するために少し待機
                page.wait_for_timeout(2000)

                # パスワードの入力欄（ログインIDは第1段階から引き継がれている）
                password_input = page.get_by_role("textbox", name="パスワード")
                if password_input.is_visible():
                    password_input.fill(zac_password)
                    print("パスワードを入力しました。")

                    # ログインボタンをクリック
                    login_button = page.get_by_role("button", name="ログイン")
                    if login_button.is_visible():
                        login_button.click()
                        print("第2段階のログイン処理を送信しました。画面遷移を待機中...")
                        page.wait_for_load_state("networkidle")
                    else:
                        print("警告: ログインボタンが見つかりませんでした。")
                else:
                    print("警告: パスワード入力欄が見つかりませんでした。")

            except Exception as e:
                print(f"第2段階のログイン処理でエラーが発生しました: {e}")
                print("継続して日報画面への到達を確認します...")

        # 日報画面に到達するまで待機（最大60秒）
        try:
            print("日報画面への到達を待機中...")
            page.wait_for_url("**/asp/Shinsei/Nippou**", timeout=60000)
            print("日報画面へのアクセスを確認しました。")
        except Exception as e:
            print(f"日報画面への到達を確認できませんでした: {e}")
            print(f"現在のURL: {page.url}")
            print("手動で確認が必要な場合があります。")
            browser.close()
            return

        print("セッション情報(auth.json)を保存します。")
        context.storage_state(path="auth.json")
        print("保存完了しました。ブラウザを閉じます。")
        browser.close()

if __name__ == "__main__":
    login_and_save_auth()
