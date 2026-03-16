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
        # 日本のPC環境を完全に再現
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            viewport={'width': 1280, 'height': 2000}
        )
        page = context.new_page()

        # --- 1. 成田ゆめ牧場 (4/4-5 監視) ---
        try:
            print("Checking Narita...")
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
                            break
        except Exception as e: print(f"Error Narita: {e}")

        # --- 2. リキャンプ館山 (5/9-11 テスト) ---
        try:
            print("Checking Recamp (Final logic)...")
            # ★テスト用URL（5/9から2泊）
            test_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-09&stay_count=2"
            page.goto(test_url, timeout=60000, wait_until="networkidle")
            
            # JavaScriptによるボタン描画を15秒間じっくり待つ
            page.wait_for_timeout(15000)

            # 判定ロジック：
            # 1. 「該当するプランがありません」の文字が【無い】こと
            # 2. ページ内に「予約」または「選択」という文字が含まれる【ボタンやリンク】があること
            has_no_plan = page.get_by_text("該当するプランがありません").is_visible()
            
            # あらゆるボタン・リンク要素から「予約」または「選択」を探す
            btn_reserve = page.locator("a, button, .c-btn").filter(has_text="予約").count()
            btn_select = page.locator("a, button, .c-btn").filter(has_text="選択").count()

            print(f"Log Recamp: NoPlan={has_no_plan}, ReserveBtns={btn_reserve}, SelectBtns={btn_select}")

            # 「プランなし」が出ておらず、かつ「予約」か「選択」ボタンが1つ以上あれば検知
            if not has_no_plan and (btn_reserve > 0 or btn_select > 0):
                send_line(f"【検証成功】リキャンプ館山：空きを検知しました！\n{test_url}")
            else:
                # 最終バックアップ判定：ボタンが見つからなくても、本文に価格（￥）があれば通知
                body_text = page.locator("body").inner_text()
                if not has_no_plan and "￥" in body_text:
                    send_line(f"【検証成功】リキャンプ館山：価格表示により空きを検知！\n{test_url}")

        except Exception as e: print(f"Error Recamp: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
