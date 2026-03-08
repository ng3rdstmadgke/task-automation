from playwright.sync_api import sync_playwright

def login_and_save_auth():
    with sync_playwright() as p:
        # 画面を表示して起動
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print("ZACのログイン画面を開きます。ブラウザ上で手動でログインし、日報画面まで進めてください...")
        page.goto("https://secure.zac.ai/beex/b/asp/Shinsei/Nippou")
        
        # 日報画面（URLにNippouが含まれる）に到達するまで無期限で待機
        page.wait_for_url("**/asp/Shinsei/Nippou**", timeout=0)
        
        print("日報画面へのアクセスを確認しました。セッション情報(auth.json)を保存します。")
        context.storage_state(path="auth.json")
        print("保存完了しました。ブラウザを閉じます。")
        browser.close()

if __name__ == "__main__":
    login_and_save_auth()
