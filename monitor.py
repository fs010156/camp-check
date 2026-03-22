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

        # --- C&C山中湖 (待機処理強化版) ---
        target_days = ["10", "23", "30"] 
        target_keywords = ["チョイ広め", "広めのオート", "東屋", "プレミアム"]
        
        try:
            print("--- C&C Scan Start ---")
            page.goto("https://reser.yagai-kikaku.com/cc_reserve/sv_open", timeout=60000)
            page.wait_for_timeout(5000)

            # 5月へ切り替え
            may_btn = page.get_by_role("link", name="5月", exact=True).first
            if may_btn.is_visible():
                may_btn.click()
                print("Log: Clicked '5月'. Waiting for table update...")
                
                # 【重要】表の中のヘッダーが「5月」に変わるまで待機
                # 画像の上部にある「2026年5月」という文字を探します
                try:
                    page.wait_for_function(
                        "() => document.querySelector('body').innerText.includes('2026年5月')",
                        timeout=20000
                    )
                    print("Log: Confirmed May 2026 display.")
                except:
                    print("Log: Wait timeout, but proceeding...")
                
                page.wait_for_timeout(5000) # 念押しの待機
            else:
                print("Log: '5月' link not found.")
                return

            # 下段のカレンダー表を特定
            target_table = page.locator("table:has-text('宿泊施設タイプ')").first
            rows = target_table.locator("tr").all()
            
            date_to_column = {}
            # 日付ヘッダーの特定
            for row in rows[:15]:
                cells = row.locator("td, th").all()
                texts = [c.inner_text().strip() for c in cells]
                if "10" in texts and ("9" in texts or "11" in texts):
                    for day in target_days:
                        if day in texts:
                            date_to_column[day] = texts.index(day)
                    break
            
            if not date_to_column:
                print("Log: Date header not found. Current texts in header row: ", texts)
                return

            # 空き情報の精査
            for day, col_idx in date_to_column.items():
                available_sites = []
                for row in rows:
                    cells = row.locator("td, th").all()
                    if len(cells) <= col_idx: continue
                    
                    full_site_text = cells[0].inner_text().strip()
                    clean_name = full_site_text.splitlines()[0].strip()
                    
                    if any(ng in clean_name for ng in ["ログイン", "2026", "宿泊施設タイプ"]): continue
                    
                    if any(kw in clean_name for kw in target_keywords):
                        status = cells[col_idx].inner_text().strip()
                        # 空判定： ×がなく、かつ(空欄/△/○)
                        if status != "×" and "定休日" not in status:
                            if status == "" or any(m in status for m in ["○", "△", "予約"]):
                                available_sites.append(clean_name)
                
                if available_sites:
                    day_label = "5/10(テスト)" if day == "10" else f"5/{day}(土)"
                    unique_sites = list(dict.fromkeys(available_sites))
                    msg = f"【C&C山中湖 空き！】\n日程: {day_label}\nサイト:\n・" + "\n・".join(unique_sites) + "\n\n予約はこちら:\nhttps://reser.yagai-kikaku.com/cc_reserve/sv_open"
                    send_line(msg)

        except Exception as e:
            print(f"Error C&C: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
