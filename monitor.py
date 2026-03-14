import os
import requests
from playwright.sync_api import sync_playwright

# LINE通知設定
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

        # --- 1. 成田ゆめ牧場 (4/4-5) ---
        try:
            page.goto("https://yumebokujo.revn.jp/camp/reserve/calendar", timeout=60000)
            # 「4月4日」のセルのテキストを取得
            target = page.locator("td", has_text="4月4日").first
            if target and "満" not in target.inner_text():
                send_line("【空きあり】成田ゆめ牧場 4/4に空きが出た可能性があります！\nhttps://yumebokujo.revn.jp/camp/reserve/calendar")
        except Exception as e:
            print(f"Error at Yume Bokujo: {e}")

        # --- 2. リキャンプ館山 (5/2-4) ---
        try:
            # なっぷのプラン一覧ページ
            page.goto("https://www.nap-camp.com/chiba/14639/plans", timeout=60000)
            # ページ内に「予約する」ボタン、または「×」以外の記号があるか簡易チェック
            # ※なっぷは非常に複雑なため、空きがあれば出る「予約する」の存在を確認
            if "予約する" in page.content():
                send_line("【空きあり】リキャンプ館山に予約可能なプランがあります！\nhttps://www.nap-camp.com/chiba/14639/plans")
        except Exception as e:
            print(f"Error at Recamp Tateyama: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
