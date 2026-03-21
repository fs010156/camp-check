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
            locale="ja-JP", timezone_id="Asia/Tokyo", viewport={'width': 1600, 'height': 2000}
        )
        page = context.new_page()

        # --- C&C山中湖 (テキスト抽出の厳格化版) ---
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
                page.wait_for_timeout(7000)

            rows = page.locator("tr").all()
            date_to_column = {}
            
            # 日付ヘッダーから正確な列位置を特定
            for row in rows[:10]: # ヘッダー探索範囲を少し広めに
                cells = row.locator("td, th").all()
                texts = [c.inner_text().strip() for c in cells]
                if "10" in texts and "11" in texts:
                    for day in target_days:
                        if day in texts:
                            date_to_column[day] = texts.index(day)
                    break
            
            if not date_to_column:
                print("Log: Date columns not found.")
                return

            # 空き情報の抽出と通知
            # 日付ごとにまとめて通知する
            for day, col_idx in date_to_column.items():
                available_list = []
                for row in rows:
                    cells = row.locator("td, th").all()
                    if len(cells) <= col_idx: continue
                    
                    # サイト名のセルから「余計な文字」を排除
                    # .split() を使い、最初の単語（サイト名）だけを抽出
                    raw_name = cells[0].inner_text().strip()
                    clean_name = raw_name.split('\n')[0].split('\t')[0].strip()
                    
                    if any(s in clean_name for s in target_sites):
                        status = cells[col_idx].inner_text().strip()
                        # 「×」でも「定休日」でもなければ空きと判定
                        if status != "×" and "定休日" not in status:
                            available_list.append(clean_name)
                
                if available_list:
                    day_label = "5/10(テ)" if day == "10" else f"5/{day}(土)"
                    unique_sites = list(dict.fromkeys(available_list)) # 重複削除
                    sites_msg = "\n・".join(unique_sites)
                    
                    msg = f"【C&C山中湖 空きあり】\n日程: {day_label}\nサイト:\n・{sites_msg}\n\n予約はこちら:\nhttps://reser.yagai-kikaku.com/cc_reserve/sv_open"
                    send_line(msg)
                    print(f"Log: Sent notification for {day_label}")

        except Exception as e:
            print(f"Error C&C: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
