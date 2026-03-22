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
            locale="ja-JP", timezone_id="Asia/Tokyo", viewport={'width': 1600, 'height': 3000}
        )
        page = context.new_page()

        # --- C&C山中湖 (誤検知ガード強化版) ---
        target_days = ["10", "23", "30"] 
        target_keywords = ["チョイ広め", "広めのオート", "東屋", "プレミアム"]
        
        try:
            print("--- C&C Table Scan Start (Strict Mode) ---")
            page.goto("https://reser.yagai-kikaku.com/cc_reserve/sv_open", timeout=60000)
            page.wait_for_timeout(5000)

            # 5月へ切り替え
            may_btn = page.get_by_role("link", name="5月", exact=True).first
            if may_btn.is_visible():
                may_btn.click()
                page.wait_for_timeout(8000)

            rows = page.locator("tr").all()
            date_to_column = {}
            
            # 1. 日付ヘッダーの特定（9, 10, 11が並んでいる行を探す）
            for row in rows[:20]:
                cells = row.locator("td, th").all()
                texts = [c.inner_text().strip() for c in cells]
                if "9" in texts and "10" in texts and "11" in texts:
                    for day in target_days:
                        if day in texts:
                            date_to_column[day] = texts.index(day)
                    break
            
            if not date_to_column:
                print("Log: Could not find strict date header.")
                return

            # 2. 空き情報の精査
            for day, col_idx in date_to_column.items():
                available_sites = []
                for row in rows:
                    cells = row.locator("td, th").all()
                    if len(cells) <= col_idx: continue
                    
                    # サイト名のセル（0番目）を厳格にチェック
                    site_cell_text = cells[0].inner_text().strip()
                    # 改行で分割して1行目（純粋な名前部分）だけ見る
                    clean_name = site_cell_text.split('\n')[0].strip()
                    
                    # NGワードが含まれていたら無視
                    if any(ng in clean_name for ng in ["ログイン", "2026年", "前月", "翌月"]):
                        continue
                    
                    # 希望キーワードが含まれているか
                    if any(kw in clean_name for kw in target_keywords):
                        status = cells[col_idx].inner_text().strip()
                        
                        # 空き判定： 「×」がなく、かつ「定休日」でもなく、かつ「空欄」か「△」か「○」がある
                        # status.strip() が空（""）の場合も C&Cでは空き(○)を意味することが多いため許可
                        if status != "×" and "定休日" not in status:
                            if status == "" or any(mark in status for mark in ["○", "△", "予約"]):
                                available_sites.append(clean_name)
                
                if available_sites:
                    day_label = "5/10(テスト)" if day == "10" else f"5/{day}(土)"
                    unique_sites = list(dict.fromkeys(available_sites))
                    
                    msg = f"【C&C山中湖 空きあり】\n日程: {day_label}\nサイト:\n・" + "\n・".join(unique_sites) + "\n\n予約:\nhttps://reser.yagai-kikaku.com/cc_reserve/sv_open"
                    send_line(msg)
                    print(f"Log: Match found for {day_label}")

        except Exception as e:
            print(f"Error C&C: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
