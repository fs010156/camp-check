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
            print("--- C&C Yamanakako: Final Row Scan Start ---")
            page.goto("https://reser.yagai-kikaku.com/cc_reserve/sv_open", timeout=60000)
            page.wait_for_timeout(5000)

            # 「5月」をクリック
            may_link = page.get_by_role("link", name="5月", exact=True).first
            if may_link.is_visible():
                may_link.click()
                page.wait_for_timeout(10000)

            rows = page.locator("tr").all()
            target_col = -1
            
            # 【重要】日付ヘッダー行（1, 2, 3...が並んでいる行）を正しく探す
            for row in rows:
                cells = row.locator("td, th").all()
                texts = [c.inner_text().strip() for c in cells]
                # 「1」「2」「3」がこの順番で含まれていれば、それが日付ヘッダー
                if "1" in texts and "2" in texts and "3" in texts:
                    if "10" in texts:
                        target_col = texts.index("10")
                        print(f"Log: Found Date Header! Day 10 is at column {target_col}")
                        break
            
            if target_col == -1:
                print("Log: Failed to find the date header column.")
                return

            # 希望サイト
            target_keywords = ["チョイ広め", "広めのオート", "東屋", "プレミアム"]
            final_results = []

            for row in rows:
                cells = row.locator("td").all()
                if len(cells) <= target_col: continue
                
                # サイト名を取得（最初の改行まで）
                full_site_name = cells[0].inner_text().strip()
                clean_site_name = full_site_name.split('\n')[0].strip()
                
                if any(kw in clean_site_name for kw in target_keywords):
                    status = cells[target_col].inner_text().strip()
                    # 「×」という文字が全く含まれていないことを条件にする
                    if "×" not in status and "定休日" not in status:
                        final_results.append(clean_site_name)
            
            if final_results:
                # 重複を排除してメッセージ作成
                unique_sites = list(dict.fromkeys(final_results))
                msg = "【C&C山中湖 検証成功】\n日程: 5/10(テスト)\nサイト:\n・" + "\n・".join(unique_sites)
                send_line(msg)
                print("Log: Notification sent successfully.")
            else:
                print("Log: No vacant sites found for Day 10 in the identified column.")

        except Exception as e:
            print(f"Error occurred: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
