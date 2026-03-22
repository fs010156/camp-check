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
        # 画面を表示しないモード(headless=True)
        browser = p.chromium.launch(headless=True)
        # 人間のブラウザに見せかけるための設定
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        target_days = ["10", "23", "30"] 
        target_keywords = ["チョイ広め", "広めのオート", "東屋", "プレミアム"]
        
        try:
            print("--- C&C Session Initialization ---")
            # 1. まずはトップ付近にアクセスしてセッション(Cookie)を確立する
            page.goto("https://reser.yagai-kikaku.com/cc_reserve/sv_open", wait_until="networkidle")
            page.wait_for_timeout(5000)

            # 2. 「5月」リンクをクリック（Ajaxでの書き換えを狙う）
            may_btn = page.get_by_role("link", name="5月", exact=True).first
            if may_btn.is_visible():
                may_btn.click()
                print("Log: Clicked '5月'. Waiting for Ajax content...")
                # 3. 表のヘッダーが「5月」になるのを待つ
                page.wait_for_function("() => document.body.innerText.includes('2026年5月')", timeout=30000)
                page.wait_for_timeout(5000) 
            
            # 4. 表（Table）を特定
            # 「宿泊施設タイプ」という文字がある表を探す
            table = page.locator("table:has-text('宿泊施設タイプ')").last
            rows = table.locator("tr").all()
            
            # 日付の列番号を特定
            date_cols = {}
            for row in rows[:15]:
                cells = row.locator("td, th").all()
                texts = [c.inner_text().strip() for c in cells]
                if "10" in texts:
                    for d in target_days:
                        if d in texts: date_cols[d] = texts.index(d)
                    break

            if not date_cols:
                print("Log: Date columns not found. Table might be empty.")
                return

            # 5. 空き判定
            for day, idx in date_cols.items():
                found_list = []
                for row in rows:
                    cells = row.locator("td, th").all()
                    if len(cells) <= idx: continue
                    
                    name_raw = cells[0].inner_text().strip().splitlines()[0]
                    if any(kw in name_raw for kw in target_keywords):
                        status = cells[idx].inner_text().strip()
                        # 空判定: ×がなく、かつ(空欄 or ○ or △)
                        if status != "×" and "休" not in status:
                            found_list.append(name_raw)
                
                if found_list:
                    day_label = "5/10(テスト)" if day == "10" else f"5/{day}(土)"
                    msg = f"【C&C山中湖 空き！】\n日程: {day_label}\nサイト:\n・" + "\n・".join(list(set(found_list))) + "\n\n予約はこちら:\nhttps://reser.yagai-kikaku.com/cc_reserve/sv_open"
                    send_line(msg)
                    print(f"Log: Notified for {day}")

        except Exception as e:
            print(f"Error: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
