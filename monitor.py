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
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="ja-JP", timezone_id="Asia/Tokyo", viewport={'width': 1600, 'height': 2000} # 横幅を広めに確保
        )
        page = context.new_page()

        # --- C&C山中湖 (一覧表マトリックス解析) ---
        target_days = ["10", "23", "30"] 
        target_sites = ["チョイ広め", "広めのオート", "東屋", "プレミアム"]
        
        try:
            print("--- C&C Yamanakako: Table Matrix Scan ---")
            page.goto("https://reser.yagai-kikaku.com/cc_reserve/sv_open", timeout=60000)
            page.wait_for_timeout(5000)

            # 「5月」をクリックして切り替え
            may_btn = page.get_by_role("link", name="5月", exact=True).first
            if may_btn.is_visible():
                may_btn.click()
                page.wait_for_timeout(7000)

            # 表（テーブル）の全行を取得
            rows = page.locator("tr").all()
            if len(rows) < 5:
                print("Log: Table not loaded correctly.")
                return

            # 1. 日付ヘッダー行から対象日の「列番号(Index)」を特定
            # 通常、1行目か2行目に「1 2 3...31」と並んでいる
            header_row_text = ""
            date_to_column = {}
            
            for row in rows[:5]: # 上位5行以内に日付ヘッダーがあるはず
                cells = row.locator("td, th").all()
                texts = [c.inner_text().strip() for c in cells]
                if "1" in texts and "2" in texts and "10" in texts:
                    header_row_text = texts
                    for day in target_days:
                        if day in texts:
                            date_to_column[day] = texts.index(day)
                    break
            
            if not date_to_column:
                print("Log: Could not identify date columns.")
                return

            print(f"Log: Identified columns for days: {date_to_column}")

            # 2. 各行をスキャンしてサイト名を特定し、対象列の空きを確認
            for row in rows:
                cells = row.locator("td, th").all()
                if not cells: continue
                
                row_header_text = cells[0].inner_text().replace(" ", "").replace("\n", "")
                
                # 希望のサイト名が含まれる行か？
                if any(s in row_header_text for s in target_sites):
                    # 各対象日（列）をチェック
                    for day, col_idx in date_to_column.items():
                        if col_idx < len(cells):
                            status = cells[col_idx].inner_text().strip()
                            # 判定： 「×」が含まれていなければ空きとみなす
                            if "×" not in status:
                                date_label = "5/10(テスト)" if day == "10" else f"5/{day}"
                                send_line(f"【検証成功】C&C山中湖空き！\n日程: {date_label}\nサイト: {row_header_text}\n状況: [{status if status else '空欄(◯)'}]\nhttps://reser.yagai-kikaku.com/cc_reserve/sv_open")
                                # 同じ日の重複通知を避けるため、見つかったら次の日へ
            
        except Exception as e:
            print(f"Error C&C: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
