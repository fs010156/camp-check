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
        # ブラウザの偽装設定を「日本国内のPC」に徹底
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            viewport={'width': 1280, 'height': 1200}
        )
        page = context.new_page()

        # --- 1. 成田ゆめ牧場 (4/4-5 監視) ---
        # (ロジックは安定しているため維持)
        try:
            page.goto("https://yumebokujo.revn.jp/camp/reserve/calendar", timeout=60000)
            page.wait_for_timeout(5000)
            headers = page.locator("tr.calendar-head th").all()
            target_indices = [i for i, h in enumerate(headers) if "4/4" in h.inner_text() or "4/5" in h.inner_text()]
            if len(target_indices) >= 2:
                for row in page.locator("tr").all():
                    cells = row.locator("td").all()
                    if len(cells) < 1: continue
                    if any(x in cells[0].inner_text() for x in ["一般", "電源"]):
                        v44 = any("残0" not in cells[idx].inner_text() and any(c.isdigit() for c in cells[idx].inner_text()) for idx in target_indices if "4/4" in headers[idx].inner_text())
                        v45 = any("残0" not in cells[idx].inner_text() and any(c.isdigit() for c in cells[idx].inner_text()) for idx in target_indices if "4/5" in headers[idx].inner_text())
                        if v44 and v45:
                            send_line(f"【空き】成田ゆめ牧場\n{cells[0].inner_text()} 4/4-5")
        except Exception as e: print(f"Error Narita: {e}")

        # --- 2. リキャンプ館山 5/9-11 強制報告モード ---
        try:
            print("--- Recamp Tateyama Diagnosis ---")
            test_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-09&stay_count=2"
            page.goto(test_url, timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(10000)

            # メインコンテンツの文字を抽出
            main_area = page.locator("#main_contents, body")
            visible_text = main_area.first.inner_text()[:300] # 最初の300文字だけ取得
            
            # 空き判定
            has_no_plan = "該当するプランがありません" in visible_text
            # ￥マークや「予約」という文字をより厳しく、かつ広く探す
            reserve_btn = page.locator("text='予約する'").count()
            
            # 【検証用】何が見えていてもいなくても、現在の状況をLINEに飛ばす
            status_msg = f"【リキャンプ検証中】\nプランなし表示: {has_no_plan}\n予約ボタン数: {reserve_btn}\n取得テキスト冒頭: {visible_text}"
            send_line(status_msg)

        except Exception as e:
            send_line(f"【エラー報告】リキャンプ：{str(e)}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
