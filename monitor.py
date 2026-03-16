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

        # --- 1. 成田ゆめ牧場 (4/4-5 監視) ---
        try:
            print("--- [START] Narita Yume Farm Check ---")
            page.goto("https://yumebokujo.revn.jp/camp/reserve/calendar", timeout=60000)
            page.wait_for_timeout(7000)
            header_els = page.locator("tr.calendar-head th")
            if header_els.count() > 0:
                headers = header_els.all()
                target_indices = [i for i, h in enumerate(headers) if "4/4" in h.inner_text() or "4/5" in h.inner_text()]
                if len(target_indices) >= 2:
                    found_narita = False
                    for row in page.locator("tr").all():
                        cells = row.locator("td").all()
                        if len(cells) <= max(target_indices): continue
                        site_name = cells[0].inner_text()
                        if any(x in site_name for x in ["一般", "電源"]):
                            v44 = any("残0" not in cells[idx].inner_text() and any(c.isdigit() for c in cells[idx].inner_text()) for idx in target_indices if "4/4" in headers[idx].inner_text())
                            v45 = any("残0" not in cells[idx].inner_text() and any(c.isdigit() for c in cells[idx].inner_text()) for idx in target_indices if "4/5" in headers[idx].inner_text())
                            if v44 and v45:
                                send_line(f"【至急】成田ゆめ牧場\n{site_name}：4/4-4/5 両方空き！\nhttps://yumebokujo.revn.jp/camp/reserve/calendar")
                                found_narita = True
                                break
                    if not found_narita: print("Log: Narita is still fully booked.")
        except Exception as e: print(f"Error Narita: {e}")

        # --- 2. リキャンプ館山 (5/2-4 GW監視) ---
        try:
            print("--- [START] Recamp Tateyama Check ---")
            target_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-02&stay_count=2"
            page.goto(target_url, timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(15000)

            # プラン要素の抽出
            plans = page.locator(".c-planList__item, .c-planCard, [id^='plan_']").all()
            real_vacancy = False

            if len(plans) > 0:
                print(f"Log: Found {len(plans)} plan items. Analyzing each...")
                for plan in plans:
                    plan_text = plan.inner_text()
                    # 判定：満室（×）がなく、かつ予約/選択ボタンが見えること
                    has_error = any(x in plan_text for x in ["×", "満室", "該当なし"])
                    has_btn = plan.get_by_text("予約する").is_visible() or plan.get_by_text("選択する").is_visible()
                    
                    if not has_error and has_btn:
                        real_vacancy = True
                        break
            
            # バックアップ判定
            if not real_vacancy:
                body_text = page.locator("body").inner_text()
                if "該当するプランがありません" not in body_text and "予約する" in body_text:
                    if body_text.count("予約する") > body_text.count("×"):
                        real_vacancy = True

            if real_vacancy:
                send_line(f"【至急】リキャンプ館山に空き！\n5/2(土)〜5/4(月) 2泊枠\n{target_url}")
            else:
                # ★ここが重要：空きがない理由を具体的にログに残す
                print(f"Log: Recamp Check Finished. Result: No Vacancy. (Confirmed {len(plans)} plans were all booked.)")

        except Exception as e: print(f"Error Recamp: {e}")
        browser.close()

if __name__ == "__main__":
    check_campsites()
