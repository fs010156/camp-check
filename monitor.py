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

        # --- C&C山中湖 (5/23, 5/30 本番監視モード) ---
        target_days = ["23", "30"] 
        target_keywords = ["チョイ広め", "広めのオート", "東屋", "プレミアム"]
        
        try:
            print("--- C&C Production Scan Start ---")
            page.goto("https://reser.yagai-kikaku.com/cc_reserve/sv_open", timeout=60000)
            page.wait_for_timeout(5000)

            # 「はじめに」ページ突破
            if "はじめに" in page.locator("body").inner_text()[:300]:
                enter_btn = page.locator("a:has-text('空室状況'), a:has-text('予約状況'), a:has-text('次へ')").first
                if enter_btn.is_visible():
                    enter_btn.click()
                    page.wait_for_timeout(7000)

            # 5月へ切り替え
            may_btn = page.get_by_role("link", name="5月", exact=True).first
            if may_btn.is_visible():
                may_btn.click()
                page.wait_for_timeout(8000)

            # 表の解析
            page.wait_for_selector("table", timeout=20000)
            rows = page.locator("tr").all()
            date_to_column = {}
            
            for row in rows[:20]:
                cells = row.locator("td, th").all()
                texts = [c.inner_text().strip() for c in cells]
                # 日付ヘッダーの特定
                if "23" in texts or "30" in texts:
                    for day in target_days:
                        if day in texts:
                            date_to_column[day] = texts.index(day)
                    if date_to_column: break
            
            if not date_to_column: return

            # 空き情報の抽出
            for day, col_idx in date_to_column.items():
                available_sites = []
                for row in rows:
                    cells = row.locator("td, th").all()
                    if len(cells) <= col_idx: continue
                    
                    full_name = cells[0].inner_text().strip().split('\n')[0].strip()
                    if any(ng in full_name for ng in ["ログイン", "2026", "前月", "翌月"]): continue
                    
                    if any(kw in full_name for kw in target_keywords):
                        status = cells[col_idx].inner_text().strip()
                        # 空き判定 (×以外 且つ 空欄/△/○/予約)
                        if status != "×" and "定休日" not in status:
                            if status == "" or any(m in status for m in ["○", "△", "予約"]):
                                available_sites.append(full_name)
                
                if available_sites:
                    unique_sites = list(dict.fromkeys(available_sites))
                    msg = f"【C&C山中湖 空き発生！】\n日程: 5/{day}(土)〜1泊\nサイト:\n・" + "\n・".join(unique_sites) + "\n\n予約を急いでください！\nhttps://reser.yagai-kikaku.com/cc_reserve/sv_open"
                    send_line(msg)

        except Exception as e:
            print(f"Error C&C: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
