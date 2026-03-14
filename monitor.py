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
        page = browser.new_page(viewport={'width': 1280, 'height': 800})

        try:
            # 【検証条件】5月3日から1泊
            test_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-03&stay_count=1"
            print(f"Checking URL: {test_url}")
            page.goto(test_url, timeout=60000)
            
            # ページ読み込み待機
            page.wait_for_timeout(7000)
            
            content = page.content()
            
            # 判定ロジック
            if "該当するプランがありません" not in content and "予約する" in content:
                send_line("【検証中】5/3の空きを検知しました！\n" + test_url)
            else:
                # LINEが飛ばない理由をログに出力します
                print("結果：空きなし（正しく通知をスキップしました）")
                if "該当するプランがありません" in content:
                    print("理由：『該当するプランがありません』の文言を確認")
                if "予約する" not in content:
                    print("理由：『予約する』ボタンが見つかりません")

        except Exception as e:
            print(f"Error: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
