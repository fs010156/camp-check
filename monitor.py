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

        # --- 1. 成田ゆめ牧場 (4/4-5) ---
        try:
            print("Checking Narita...")
            page.goto("https://yumebokujo.revn.jp/camp/reserve/calendar", timeout=60000)
            page.wait_for_timeout(7000)
            header_els = page.locator("tr.calendar-head th")
            if header_els.count() > 0:
                headers = header_els.all()
                target_indices = [i for i, h in enumerate(headers) if "4/4" in h.inner_text() or "4/5" in h.inner_text()]
                if len(target_indices) >= 2:
                    for row in page.locator("tr").all():
                        cells = row.locator("td").all()
                        if len(cells) <= max(target_indices): continue
                        if any(x in cells[0].inner_text() for x in ["一般", "電源"]):
                            v44 = any("残0" not in cells[idx].inner_text() and any(c.isdigit() for c in cells[idx].inner_text()) for idx in target_indices if "4/4" in headers[idx].inner_text())
                            v45 = any("残0" not in cells[idx].inner_text() and any(c.isdigit() for c in cells[idx].inner_text()) for idx in target_indices if "4/5" in headers[idx].inner_text())
                            if v44 and v45:
                                send_line(f"【通知】成田ゆめ牧場空き！\n4/4-4/5 2連泊可能です。")
                                break
        except Exception as e: print(f"Error Narita: {e}")

        # --- 2. リキャンプ館山 (5/2-4) ---
        try:
            print("Checking Recamp...")
            target_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-02&stay_count=2"
            page.goto(target_url, timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(15000)
            plans = page.locator(".c-planList__item, .c-planCard").all()
            for plan in plans:
                if not any(x in plan.inner_text() for x in ["×", "満室"]) and (plan.get_by_text("予約する").is_visible() or plan.get_by_text("選択する").is_visible()):
                    send_line(f"【至急】リキャンプ館山空き！\n5/2-5/4 2泊予約可能です。")
                    break
        except Exception as e: print(f"Error Recamp: {e}")

        # --- 3. キャンプ・アンド・キャビンズ山中湖 (5/10 テスト用) ---
        # ★テストのため、あえて空きがある5/10を指定しています
        target_dates = ["20260510"] 
        target_sites = ["チョイ広め", "広めのオート", "東屋", "プレミアム"]
        
        for d in target_dates:
            try:
                print(f"Checking C&C Yamanakako TEST for {d}...")
                cc_url = f"https://reser.yagai-kikaku.com/cc_reserve/sv_open?ymd={d}"
                page.goto(cc_url, timeout=60000)
                page.wait_for_timeout(10000)

                rows = page.locator("tr").all()
                for row in rows:
                    row_text = row.inner_text()
                    if any(site in row_text for site in target_sites):
                        # 「×」が含まれていなければ検知（△や空欄をパスさせる）
                        if "×" not in row_text:
                            send_line(f"【検証成功】C&C山中湖の検知に成功！\n日程: 5/10(日)\nサイト: {row_text.splitlines()[0][:25]}...\n{cc_url}")
                            break
            except Exception as e: print(f"Error C&C Test: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
