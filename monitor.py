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
        # ブラウザの偽装度を最高レベルに設定
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 2000}
        )
        page = context.new_page()

        # --- 1. 成田ゆめ牧場 (4/4-5 監視) ---
        try:
            print("--- Narita Yume Farm Check ---")
            page.goto("https://yumebokujo.revn.jp/camp/reserve/calendar", timeout=60000)
            page.wait_for_timeout(5000)
            headers = page.locator("tr.calendar-head th").all()
            target_indices = [i for i, h in enumerate(headers) if "4/4" in h.inner_text() or "4/5" in h.inner_text()]
            
            if len(target_indices) >= 2:
                rows = page.locator("tr").all()
                for row in rows:
                    cells = row.locator("td").all()
                    if len(cells) < 1: continue
                    site_name = cells[0].inner_text()
                    if "一般" in site_name or "電源" in site_name:
                        # 4/4と4/5のマスを厳密にチェック
                        v_44 = any("残0" not in cells[idx].inner_text() and any(c.isdigit() for c in cells[idx].inner_text()) for idx in target_indices if "4/4" in headers[idx].inner_text())
                        v_45 = any("残0" not in cells[idx].inner_text() and any(c.isdigit() for c in cells[idx].inner_text()) for idx in target_indices if "4/5" in headers[idx].inner_text())
                        if v_44 and v_45:
                            send_line(f"【空きあり】成田ゆめ牧場\n{site_name}：4/4-4/5\nhttps://yumebokujo.revn.jp/camp/reserve/calendar")
                            break
        except Exception as e: print(f"Error at Narita: {e}")

        # --- 2. リキャンプ館山 (5/9-11 テスト) ---
        try:
            print("--- Recamp Tateyama Test (Hard Mode) ---")
            test_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-09&stay_count=2"
            page.goto(test_url, timeout=60000, wait_until="networkidle")
            
            # 人間らしく少しスクロール
            page.mouse.wheel(0, 500)
            page.wait_for_timeout(10000)

            # 判定ロジックA: 「予約する」ボタンの要素を直接探す
            reserve_buttons = page.locator("a:has-text('予約する'), button:has-text('予約する'), .c-btn:has-text('予約する')")
            btn_count = reserve_buttons.count()
            
            # 判定ロジックB: メインエリアのテキスト解析
            main_text = page.locator("body").inner_text()
            has_no_plan = "該当するプランがありません" in main_text

            print(f"Log Recamp: Found {btn_count} reserve buttons. NoPlanMsg: {has_no_plan}")

            # 「予約ボタンが見つかる」かつ「該当プランなしと言われていない」なら確実に空き
            if btn_count > 0 and not has_no_plan:
                send_line(f"【検証成功】リキャンプ館山を検知しました！\nボタン数: {btn_count}\n{test_url}")
            else:
                # 最終手段：プラン価格の「￥」マークがメインエリアにあるか
                if "￥" in main_text and not has_no_plan:
                    send_line(f"【検証成功】リキャンプ館山（価格検知）！\n{test_url}")

        except Exception as e: print(f"Error at Recamp: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
