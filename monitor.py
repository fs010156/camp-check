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
        page = browser.new_page()

        # --- リキャンプ館山の空きテスト ---
        try:
            print("Checking Recamp Tateyama (Test Mode)...")
            # 検証用URL：確実に空きがあると思われる「3月17日から1泊」を指定
            test_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-03-17&stay_count=1"
            page.goto(test_url, timeout=60000)
            
            # 検索結果の読み込みを待機
            page.wait_for_timeout(3000)
            
            content = page.content()
            # 「該当するプランがありません」がなく、かつ「予約する」があるか判定
            if "該当するプランがありません" not in content and "予約する" in content:
                send_line("【検証成功】リキャンプ館山の空きを検知しました！\n" + test_url)
            else:
                print("No vacancy found for the test date.")
                # もし空きがない場合は、ログに内容を出して原因を探ります
                if "該当するプランがありません" in content:
                    print("Status: Plan not found message exists.")
        except Exception as e:
            print(f"Error at Recamp Tateyama: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
