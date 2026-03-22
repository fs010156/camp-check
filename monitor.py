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
            locale="ja-JP", viewport={'width': 1600, 'height': 3000}
        )
        page = context.new_page()

        try:
            print("--- C&C Yamanakako: Simple Scan Start ---")
            page.goto("https://reser.yagai-kikaku.com/cc_reserve/sv_open", timeout=60000)
            page.wait_for_timeout(5000)

            # 5月へ切り替え
            page.get_by_role("link", name="5月", exact=True).first.click()
            page.wait_for_timeout(8000)

            # 5/10の列番号を特定（再トライ）
            rows = page.locator("tr").all()
            target_col = -1
            for row in rows[:15]:
                texts = [c.inner_text().strip() for c in row.locator("td, th").all()]
                if "10" in texts:
                    target_col = texts.index("10")
                    break
            
            if target_col == -1:
                print("Log: Could not find column for day 10.")
                return

            # 希望サイトのリスト
            target_keywords = ["チョイ広め", "広めのオート", "東屋", "プレミアム"]
            found_list = []

            for row in rows:
                cells = row.locator("td").all()
                if len(cells) <= target_col: continue
                
                site_name = cells[0].inner_text().split('\n')[0].strip()
                
                # 指定キーワードが含まれるサイトか？
                if any(kw in site_name for kw in target_keywords):
                    status = cells[target_col].inner_text().strip()
                    
                    # 判定：「×」が含まれておらず、かつ「定休日」でもない場合
                    # (C&Cの空欄は「予約可能」を意味するため)
                    if "×" not in status and "定休日" not in status:
                        found_list.append(site_name)
            
            if found_list:
                msg = f"【C&C山中湖 検証成功】\n日程: 5/10(テスト)\nサイト:\n・" + "\n・".join(list(dict.fromkeys(found_list)))
                send_line(msg)
                print("Log: Success notification sent.")
            else:
                print("Log: No vacancy found for day 10.")

        except Exception as e:
            print(f"Error: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
