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

        # --- 成田ゆめ牧場の空きテスト ---
        try:
            print("Checking Narita Yume Farm (Test Mode)...")
            page.goto("https://yumebokujo.revn.jp/camp/reserve/calendar", timeout=60000)
            
            rows = page.locator("tr").all()
            found = False
            for row in rows:
                text = row.inner_text()
                # 「一般」か「電源」の行をチェック
                if "一般" in text or "電源" in text:
                    # その行の中に「残0サイト」ではない枠があるか確認
                    # ※「受付前」も除外します
                    if "残0サイト" not in text and "受付前" not in text:
                        # 念のため、何らかの数字（残数）が含まれているか確認
                        import re
                        if re.search(r'\d+', text): 
                            found = True
                            site_type = "一般" if "一般" in text else "電源"
                            break

            if found:
                send_line(f"【検証成功】成田ゆめ牧場の空きを検知しました！\n区分: {site_type}\n現在のカレンダーで「残0」以外の枠が存在します。")
            else:
                print("No vacancy found in the current calendar.")
        except Exception as e:
            print(f"Error: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
