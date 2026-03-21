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

        # --- 1. 成田ゆめ牧場 ---
        try:
            print("--- Narita Check ---")
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
                                send_line(f"【至急】成田ゆめ牧場空き！\nhttps://yumebokujo.revn.jp/camp/reserve/calendar")
                                break
        except Exception as e: print(f"Error Narita: {e}")

        # --- 2. リキャンプ館山 ---
        try:
            print("--- Recamp Check ---")
            target_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-02&stay_count=2"
            page.goto(target_url, timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(15000)

            plans = page.locator(".c-planList__item, .c-planCard").all()
            for plan in plans:
                plan_text = plan.inner_text()
                # 判定：満室（×）がなく、かつ予約ボタンがある
                if not any(x in plan_text for x in ["×", "満室"]) and (plan.get_by_text("予約する").is_visible() or plan.get_by_text("選択する").is_visible()):
                    # プランの個別ページURLを取得できれば取得
                    link_el = plan.locator("a").first
                    specific_url = link_el.get_attribute("href") if link_el.count() > 0 else None
                    full_url = f"https://www.nap-camp.com{specific_url}" if specific_url and specific_url.startswith("/") else target_url
                    
                    send_line(f"【至急】リキャンプ館山に予約可能枠！\n直通リンク:\n{full_url}")
                    break
        except Exception as e: print(f"Error Recamp: {e}")
        browser.close()

if __name__ == "__main__":
    check_campsites()
