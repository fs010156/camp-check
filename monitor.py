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
            locale="ja-JP", timezone_id="Asia/Tokyo", viewport={'width': 1600, 'height': 2500}
        )
        page = context.new_page()

        # --- C&C山中湖 (判定ロジック緩和版) ---
        target_days = ["10", "23", "30"] 
        target_sites = ["チョイ広め", "広めのオート", "東屋", "プレミアム"]
        
        try:
            print("--- C&C Table Scan Start ---")
            page.goto("https://reser.yagai-kikaku.com/cc_reserve/sv_open", timeout=60000)
            page.wait_for_timeout(5000)

            # 5月へ切り替え
            may_btn = page.get_by_role("link", name="5月", exact=True).first
            if may_btn.is_visible():
                may_btn.click()
                page.wait_for_timeout(8000)
            else:
                print("Log: May link not found.")

            rows = page.locator("tr").all()
            date_to_column = {}
            
            # 日付ヘッダー特定
            for row in rows[:15]:
                cells = row.locator("td, th").all()
                texts = [c.inner_text().strip() for c in cells]
                if "10" in texts and "20" in texts:
                    for day in target_days:
                        if day in texts:
                            date_to_column[day] = texts.index(day)
                    break
            
            if not date_to_column:
                print("Log: Date header not found. Check if page is loaded.")
                return

            print(f"Log: Target columns -> {date_to_column}")

            # 空き情報の抽出
            for day, col_idx in date_to_column.items():
                available_found = []
                for row in rows:
                    cells = row.locator("td, th").all()
                    if len(cells) <= col_idx: continue
                    
                    # 比較用に「すべての空白と改行を除去した名前」を作る
                    raw_text = cells[0].inner_text()
                    clean_name_for_match = raw_text.replace(" ", "").replace("\n", "").replace("\t", "").replace("　", "")
                    
                    # 表示用に「最初の1行だけ」を抜き出す
                    display_name = raw_text.strip().split('\n')[0].strip()
                    
                    # キーワードが含まれているか判定
                    if any(s in clean_name_for_match for s in target_sites):
                        status = cells[col_idx].inner_text().strip()
                        # ×や定休日以外を「空き」とみなす
                        if status != "×" and "定休日" not in status:
                            available_found.append(display_name)
                
                if available_found:
                    day_label = "5/10(テスト)" if day == "10" else f"5/{day}(土)"
                    unique_list = list(dict.fromkeys(available_found))
                    msg = f"【C&C山中湖 空き！】\n日程: {day_label}\nサイト:\n・" + "\n・".join(unique_list) + "\n\n予約:\nhttps://reser.yagai-kikaku.com/cc_reserve/sv_open"
                    send_line(msg)
                    print(f"Log: Success for {day_label}")

        except Exception as e:
            print(f"Error C&C: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
