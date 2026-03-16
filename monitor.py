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

        # --- 1. 成田ゆめ牧場 (4/4-5 ピンポイント判定) ---
        try:
            print("Checking Narita Yume Farm...")
            page.goto("https://yumebokujo.revn.jp/camp/reserve/calendar", timeout=60000)
            
            # 日付の列（4/4, 4/5）が何番目にあるか正確に取得
            headers = page.locator("tr.calendar-head th").all()
            target_indices = []
            for i, h in enumerate(headers):
                h_text = h.inner_text()
                if "4/4" in h_text or "4/5" in h_text:
                    target_indices.append(i)
            
            # ターゲット（一般/電源）の行だけをループ
            # 行を特定するために、各行の最初のtd（サイト名）を確認
            rows = page.locator("tr").all()
            for row in rows:
                first_cell = row.locator("td").first
                if first_cell.count() == 0: continue
                site_name = first_cell.inner_text()
                
                if "一般" in site_name or "電源" in site_name:
                    cells = row.locator("td").all()
                    
                    # 特定した列（4/4と4/5）のセルの中身を個別に確認
                    is_4_4_ok = False
                    is_4_5_ok = False
                    
                    # cells[idx] でピンポイントにアクセス（thとtdのズレを考慮）
                    for idx in target_indices:
                        if idx < len(cells):
                            cell_content = cells[idx].inner_text()
                            # 「残0」という文字がなく、かつ「数字（残数）」が含まれているかチェック
                            if "残0" not in cell_content and any(c.isdigit() for c in cell_content):
                                if "4/4" in headers[idx].inner_text(): is_4_4_ok = True
                                if "4/5" in headers[idx].inner_text(): is_4_5_ok = True
                    
                    # 両方の日に「残0」以外の数字がある場合のみ通知
                    if is_4_4_ok and is_4_5_ok:
                        send_line(f"【空きあり】成田ゆめ牧場\n{site_name}：4/4(土)・4/5(日)両方に空きを確認！\nhttps://yumebokujo.revn.jp/camp/reserve/calendar")
                        break
        except Exception as e: print(f"Error at Narita: {e}")

        # --- 2. リキャンプ館山 (5/2-4 検索エリア限定監視) ---
        try:
            print("Checking Recamp Tateyama...")
            tateyama_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-02&stay_count=2"
            page.goto(tateyama_url, timeout=60000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(10000)

            # メインコンテンツエリアを特定
            main_area = page.locator("#main_contents, .c-planListContainer")
            if main_area.count() > 0:
                area_text = main_area.first.inner_text()
                # 絞り込み条件に合致しない時の文言がないこと、かつ「予約」または「￥」があること
                if "該当するプランがありません" not in area_text and ("予約" in area_text or "￥" in area_text):
                    send_line(f"【空きあり】リキャンプ館山\n5/2(土)〜5/4(月) 2泊枠\n{tateyama_url}")
        except Exception as e: print(f"Error at Recamp: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
