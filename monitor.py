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
            locale="ja-JP", timezone_id="Asia/Tokyo", viewport={'width': 1280, 'height': 2000}
        )
        page = context.new_page()

        # --- 1 & 2. 成田・リキャンプ (通常通り) ---
        # (中略：既存のロジックを維持しつつ、C&Cのテストに集中します)

        # --- 3. C&C山中湖 (5/10 テスト診断モード) ---
        target_dates = ["20260510"] 
        target_sites = ["チョイ広め", "広めのオート", "東屋", "プレミアム"]
        
        for d in target_dates:
            try:
                print(f"--- C&C Diagnostic Check for {d} ---")
                cc_url = f"https://reser.yagai-kikaku.com/cc_reserve/sv_open?ymd={d}"
                page.goto(cc_url, timeout=60000)
                page.wait_for_timeout(20000) # 20秒じっくり待つ

                # 診断用：ページ全体のテキストを取得
                full_text = page.locator("body").inner_text()
                
                # LINEで現在の「見え方」を強制報告（デバッグ用）
                debug_info = f"【C&C診断】\n文字数: {len(full_text)}\n冒頭: {full_text[:50].replace('', '')}\n'×'の数: {full_text.count('×')}"
                send_line(debug_info)

                rows = page.locator("tr").all()
                found_any_site = False
                for row in rows:
                    row_text = row.inner_text()
                    if any(site in row_text for site in target_sites):
                        found_any_site = True
                        if "×" not in row_text:
                            send_line(f"【検証成功】C&C山中湖検知！\nサイト: {row_text.splitlines()[0][:20]}\n{cc_url}")
                            return # 1つ見つかれば終了

                if not found_any_site:
                    send_line(f"【報告】指定サイトの行が見つかりませんでした。")

            except Exception as e:
                send_line(f"【エラー】C&Cチェック中に障害: {str(e)}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
