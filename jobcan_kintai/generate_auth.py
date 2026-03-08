#!/usr/bin/env python3
"""
Jobcanにログインしてセッション情報を保存するスクリプト
"""
import asyncio
from playwright.async_api import async_playwright
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    jobcan_email: str
    jobcan_password: str


async def generate_auth():
    """Jobcanにログインしてauth.jsonを生成"""
    print("=== Jobcan 認証情報生成 ===")

    # 設定を読み込み
    try:
        settings = Settings()
        print(f"ログインID: {settings.jobcan_email}")
    except Exception as e:
        print(f"エラー: 環境変数の読み込みに失敗しました - {e}")
        print(".envファイルを確認してください")
        return False

    # ブラウザを起動
    async with async_playwright() as p:
        print("ブラウザを起動中...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # ログインページにアクセス
            print("ログインページにアクセス中...")
            await page.goto("https://id.jobcan.jp/users/sign_in", timeout=30000)
            await page.wait_for_load_state("networkidle")

            # メールアドレスを入力
            print("認証情報を入力中...")
            await page.fill('input[name="user[email]"]', settings.jobcan_email)
            await page.fill('input[name="user[password]"]', settings.jobcan_password)

            # ログインボタンをクリック
            print("ログイン中...")
            await page.click('input[type="submit"]')
            await page.wait_for_load_state("networkidle")

            # ログイン成功を確認（URLが変わることを確認）
            current_url = page.url
            if "sign_in" in current_url:
                print("エラー: ログインに失敗しました。認証情報を確認してください")
                return False

            print(f"ログイン成功: {current_url}")

            # セッション情報を保存
            print("セッション情報を保存中...")
            storage = await context.storage_state(path="auth.json")
            print("✓ auth.json を生成しました")

            return True

        except Exception as e:
            print(f"エラー: {e}")
            return False
        finally:
            await browser.close()


if __name__ == "__main__":
    success = asyncio.run(generate_auth())
    if success:
        print("=== 認証情報生成完了 ===")
    else:
        print("=== 認証情報生成失敗 ===")
        raise SystemExit(1)
