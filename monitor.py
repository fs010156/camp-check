import os
import requests
from playwright.sync_api import sync_playwright

# --- 設定情報 ---
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

def send_line(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, json=payload)

def check_campsites():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 画面サイズを大きめに設定（スマホ版と誤認されないため）
        page = browser.new_page(viewport={'width': 1280, 'height': 800})

        try:
            print("Checking Recamp Tateyama (Retry Test Mode)...")
            # 3/24(火)に変更（より確実に空いていそうな日程）
            test_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-03-24&stay_count=1"
            page.goto(test_url, timeout=60000)
            
            # ページが完全に読み込まれるまでしっかり待機（5秒）
            page.wait_for_timeout(5000)
            
            # デバッグ用：現在のページタイトルをログに出す
            print(f"Page Title: {page.title()}")

            content = page.content()
            
            # 判定ロジックの強化：
            # 「予約する」ボタンがある、または「プラン名」が表示されているかを確認
            if "予約する" in content or "プラン一覧" in content:
                 # さらに「該当するプランがありません」というエラーが出ていないことを確認
                if "該当するプランがありません" not in content:
                    send_line("【検証成功】リキャンプ館山の空きを検知しました！\n" + test_url)
                else:
                    print("Status: Plan not found message exists.")
            else:
                print("Status: No 'Reserve' button and no 'Plan list' found.")

        except Exception as e:
            print(f"Error: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
