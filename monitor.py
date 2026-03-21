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
            locale="ja-JP", timezone_id="Asia/Tokyo", viewport={'width': 1280, 'height': 3000}
        )
        page = context.new_page()

        # --- C&C山中湖 (5月ダイレクト遷移チェック) ---
        target_days = ["10", "23", "30"] # 10日はテスト用
        target_sites = ["チョイ広め", "広めのオート", "東屋", "プレミアム"]
        
        try:
            print("--- C&C Yamanakako: Direct Jump to May ---")
            page.goto("https://reser.yagai-kikaku.com/cc_reserve/sv_open", timeout=60000)
            page.wait_for_timeout(5000)

            # 「5月」というリンクを直接探してクリック
            may_link = page.get_by_role("link", name="5月", exact=True).first
            if may_link.is_visible():
                may_link.click()
                print("Log: Clicked '5月' link.")
                page.wait_for_timeout(5000)
            else:
                print("Log: '5月' link not found. Checking if already in May.")

            # 5月の画面になった状態で各日程をチェック
            for day_num in target_days:
                print(f"Checking May {day_num}...")
                
                # 日付の数字リンクをクリック（例: "10", "23", "30"）
                # exact=Trueにすることで、"30"を探すときに"23"に反応するのを防ぎます
                day_link = page.get_by_role("link", name=day_num, exact=True).first
                
                if day_link.is_visible():
                    day_link.click()
                    page.wait_for_timeout(5000)
                    
                    # 詳細画面のスキャン
                    cells = page.locator("td").all()
                    found_v = False
                    for i, cell in enumerate(cells):
                        text = cell.inner_text().replace(" ", "").replace("\n", "")
                        if any(s in text for s in target_sites):
                            # 周辺5セル以内に「×」がなければ空きとみなす
                            look_range = cells[i:i+6]
                            combined_text = "".join([c.inner_text() for c in look_range])
                            
                            if "×" not in combined_text:
                                date_label = "5/10(テスト)" if day_num == "10" else f"5/{day_num}"
                                send_line(f"【検証成功】C&C山中湖空き！\n日程: {date_label}\nサイト: {text}\nURL: {page.url}")
                                found_v = True
                                break
                    
                    # カレンダー画面に戻る
                    page.go_back()
                    page.wait_for_timeout(3000)
                    # 戻った後に再度5月であることを確認（必要なら再クリック）
                    if "2026年5月" not in page.locator("body").inner_text():
                        page.get_by_role("link", name="5月", exact=True).first.click()
                        page.wait_for_timeout(3000)
                else:
                    print(f"Log: Day {day_num} link not found.")

        except Exception as e:
            print(f"Error C&C: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
