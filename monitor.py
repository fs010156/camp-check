import os
import requests
from playwright.sync_api import sync_playwright

# --- 設定情報 ---
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

def send_line(message):
    if not LINE_TOKEN or not LINE_USER_ID: return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, json=payload)

def check_campsites():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 800})

        # --- 1. 成田ゆめ牧場 (4/4-5 厳密監視) ---
        try:
            page.goto("https://yumebokujo.revn.jp/camp/reserve/calendar", timeout=60000)
            header_cells = page.locator("tr th").all()
            col_indices = [i for i, c in enumerate(header_cells) if "4/4" in c.inner_text() or "4/5" in c.inner_text()]
            rows = page.locator("tr").all()
            for row in rows:
                row_text = row.inner_text()
                if "一般" in row_text or "電源" in row_text:
                    cells = row.locator("td").all()
                    if all("残0サイト" not in cells[idx-1].inner_text() and "受付前" not in cells[idx-1].inner_text() and cells[idx-1].inner_text().strip() != "" for idx in col_indices):
                        site_type = "一般" if "一般" in row_text else "電源"
                        send_line(f"【空きあり】成田ゆめ牧場\n{site_type}サイト 4/4-4/5\nhttps://yumebokujo.revn.jp/camp/reserve/calendar")
                        break
        except Exception as e: print(f"Error at Narita: {e}")

        # --- 2. リキャンプ館山 (5/2-4 検索エリア限定監視) ---
        try:
            tateyama_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-02&stay_count=2"
            page.goto(tateyama_url, timeout=60000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(10000)

            # 【重要】ページ全体ではなく、検索結果のメインリスト部分（id="main_contents" 等）に絞る
            # なっぷのプラン一覧を包んでいるコンテナを指定
            plan_list = page.locator("#main_contents, .c-planList") 
            
            if plan_list.count() > 0:
                list_text = plan_list.first.inner_text()
                
                # 「該当プランなし」が含まれず、かつリスト内に「予約」や「￥」がある場合のみ通知
                if "該当するプランがありません" not in list_text and ("予約" in list_text or "￥" in list_text):
                    send_line(f"【空きあり】リキャンプ館山\n5/2(土)〜5/4(月) 2泊枠\n{tateyama_url}")
                else:
                    print("Log Recamp: Main list has no available plans.")
            else:
                print("Log Recamp: Plan list container not found.")

        except Exception as e: print(f"Error at Recamp: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
