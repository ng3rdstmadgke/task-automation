#!/usr/bin/env python3
"""
Jobcanの打刻を実行するメインスクリプト
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

from date_checker import should_skip_punch


async def punch_jobcan():
    """Jobcanで打刻を実行"""
    print("=== Jobcan 打刻処理 ===")

    today = datetime.now()
    print(f"実行日時: {today.strftime('%Y年%m月%d日 %H:%M:%S')}")

    should_skip, reason = should_skip_punch(today)
    if should_skip:
        print(f"打刻スキップ: {reason}")
        #return True

    print("打刻を実行します")

    auth_file = Path("auth.json")
    if not auth_file.exists():
        print("エラー: auth.json が見つかりません")
        print("generate_auth.py を実行してセッションファイルを生成してください")
        return False

    async with async_playwright() as p:
        print("ブラウザを起動中...")
        browser = await p.chromium.launch(headless=True)

        try:
            print("セッション情報を読み込み中...")
            context = await browser.new_context(storage_state="auth.json")
            page = await context.new_page()

            print("打刻ページにアクセス中...")
            await page.goto("https://ssl.jobcan.jp/jbcoauth/login", timeout=30000)
            await page.wait_for_load_state("networkidle")

            current_url = page.url
            if "sign_in" in current_url or "login" in current_url.split("/")[-1]:
                print("エラー: セッションが期限切れです")
                print("generate_auth.py を再実行してセッションを更新してください")
                return False

            print(f"ログイン状態確認: OK ({current_url})")

            print("PUSHボタンを探しています...")

            push_button = page.locator("#adit-button-push")
            if await push_button.count() > 0:
                print("PUSHボタンを発見: #adit-button-push")
                #await push_button.click()
            else:
                print("エラー: PUSHボタンが見つかりませんでした")
                print("ページの構造が変更されている可能性があります")
                await page.screenshot(path="tmp/error_screenshot.png")
                print("スクリーンショットを tmp/error_screenshot.png に保存しました")
                return False

            print("打刻処理中...")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)

            print("✓ 打刻完了")
            return True

        except Exception as e:
            print(f"エラー: {e}")
            try:
                await page.screenshot(path="tmp/error_screenshot.png")
                print("スクリーンショットを tmp/error_screenshot.png に保存しました")
            except:
                pass
            return False
        finally:
            await browser.close()


if __name__ == "__main__":
    print("標準出力バッファリングを無効化")
    sys.stdout.reconfigure(line_buffering=True)

    Path("tmp").mkdir(exist_ok=True)

    success = asyncio.run(punch_jobcan())
    if success:
        print("=== 処理完了 ===")
        sys.exit(0)
    else:
        print("=== 処理失敗 ===")
        sys.exit(1)
