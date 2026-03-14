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
            
            # カレンダーの「日付」が並んでいるヘッダー行から、4/4と4/5が何番目の列か特定する
            # (念のため動的に列位置を探します)
            header_cells = page.locator("tr th").all()
            col_indices = []
            for i, cell in enumerate(header_cells):
                cell_text = cell.inner_text()
                if "4/4" in cell_text or "4/5" in cell_text:
                    col_indices.append(i)

            # 行（サイト区分）ごとに、特定した列のデータだけを確認
            rows = page.locator("tr").all()
            vacant_found = False
            for row in rows:
                row_text = row.inner_text()
                if "一般" in row_text or "電源" in row_text:
                    cells = row.locator("td").all()
                    # 特定した列（4/4と4/5）の中身をチェック
                    check_results = []
                    for idx in col_indices:
                        # ヘッダーがthでデータがtdのため、インデックスを調整
                        # 通常、日付列はtdのindex = (thのindex - 1) 程度になります
                        # ここでは安全に、その行の中で「4/4」「4/5」の近傍にある「残0」をチェック
                        target_cell_text = cells[idx-1].inner_text() if len(cells) >= idx else ""
                        if "残0サイト" not in target_cell_text and "受付前" not in target_cell_text and target_cell_text != "":
                            check_results.append(True)
                        else:
                            check_results.append(False)
                    
                    # 両方の列が「空きあり（True）」の場合のみ通知
                    if len(check_results) >= 2 and all(check_results):
                        site_type = "一般" if "一般" in row_text else "電源"
                        send_line(f"【キャンプ空き通知】\n成田ゆめ牧場：{site_type}サイト\n4/4(土)・4/5(日)の両方に空きが出ました！\nhttps://yumebokujo.revn.jp/camp/reserve/calendar")
                        vacant_found = True
                        break
        except Exception as e:
            print(f"Error at Narita: {e}")

        # --- 2. リキャンプ館山 (5/2-4 監視) ---
        try:
            tateyama_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-02&stay_count=2"
            page.goto(tateyama_url, timeout=60000)
            page.wait_for_timeout(7000)
            content = page.content()
            if "該当するプランがありません" not in content and "予約する" in content:
                send_line(f"【キャンプ空き通知】\nリキャンプ館山\n5/2(土)〜5/4(月) の連泊予約が可能です！\n{tateyama_url}")
        except Exception as e:
            print(f"Error at Recamp: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
