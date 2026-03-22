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
            print("--- C&C Yamanakako: Waiting for Page Load ---")
            page.goto("https://reser.yagai-kikaku.com/cc_reserve/sv_open", timeout=60000)
            
            # 「5月」リンクをクリック
            may_link = page.get_by_role("link", name="5月", exact=True).first
            if may_link.is_visible():
                may_link.click()
                # 【重要】画面内に「2026年5月」が出るまでじっと待つ
                page.wait_for_selector("text=2026年5月", timeout=30000)
                print("Log: Confirmed 2026/05 page is loaded.")
            else:
                print("Log: May link not visible.")
                return

            # ページ全体の行を取得
            rows = page.locator("tr").all()
            target_col = -1
            
            # 日付ヘッダー行を特定
            for row in rows:
                cells = row.locator("td, th").all()
                texts = [c.inner_text().strip() for c in cells]
                # 「1」「2」「3」が並んでいる行を探し、その中の「10」の位置を特定
                if "1" in texts and "2" in texts and "3" in texts:
                    if "10" in texts:
                        target_col = texts.index("10")
                        print(f"Log: Day 10 column index is {target_col}")
                        break
            
            if target_col == -1:
                print("Log: Could not identify date column.")
                return

            target_keywords = ["チョイ広め", "広めのオート", "東屋", "プレミアム"]
            found_sites = []

            for row in rows:
                cells = row.locator("td").all()
                if len(cells) <= target_col: continue
                
                # サイト名（1行目）を取得
                site_raw = cells[0].inner_text().strip()
                site_name = site_raw.split('\n')[0].strip()
                
                # 希望サイトかつ「×」も「定休日」もない場合
                if any(kw in site_name for kw in target_keywords):
                    status = cells[target_col].inner_text().strip()
                    if "×" not in status and "定休日" not in status:
                        found_sites.append(site_name)
            
            if found_sites:
                unique_sites = list(dict.fromkeys(found_sites))
                msg = "【C&C山中湖 検証成功】\n日程: 5/10(テスト)\nサイト:\n・" + "\n・".join(unique_sites)
                send_line(msg)
                print("Log: Notification sent.")
            else:
                print("Log: No vacancy found on Day 10.")

        except Exception as e:
            print(f"Error: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
