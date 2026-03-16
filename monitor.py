import os
import requests
from playwright.sync_api import sync_playwright

# --- 設定情報 ---
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

def send_line(message):
    if not LINE_TOKEN or not LINE_USER_ID:
        return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    try:
        r = requests.post(url, headers=headers, json=payload)
        r.raise_for_status()
    except Exception as e:
        print(f"Failed to send LINE: {e}")

def check_campsites():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # iPhone等のモバイル端末として振る舞うことで表示を安定させる
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
        page = context.new_page()

        # --- 1. 成田ゆめ牧場 (4/4-5 監視) ---
        try:
            print("--- Narita Yume Farm Check Start ---")
            page.goto("https://yumebokujo.revn.jp/camp/reserve/calendar", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000) # カレンダー描画待ち

            # 日付列の特定
            headers = page.locator("tr.calendar-head th").all()
            target_indices = []
            for i, h in enumerate(headers):
                h_text = h.inner_text().replace('\n', '')
                if "4/4" in h_text or "4/5" in h_text:
                    print(f"Log: Found column '{h_text}' at index {i}")
                    target_indices.append(i)
            
            # 列が見つからない場合にエラーで落とさず、スキップするように修正
            if len(target_indices) < 2:
                print("Log: Target columns (4/4 or 4/5) not found. Skipping Narita.")
            else:
                rows = page.locator("tr").all()
                for row in rows:
                    cells = row.locator("td").all()
                    if len(cells) < max(target_indices): continue
                    
                    site_name = cells[0].inner_text()
                    if "一般" in site_name or "電源" in site_name:
                        is_4_4_ok = False
                        is_4_5_ok = False
                        
                        for idx in target_indices:
                            cell_content = cells[idx].inner_text()
                            if "残0" not in cell_content and any(c.isdigit() for c in cell_content):
                                if "4/4" in headers[idx].inner_text(): is_4_4_ok = True
                                if "4/5" in headers[idx].inner_text(): is_4_5_ok = True
                        
                        if is_4_4_ok and is_4_5_ok:
                            send_line(f"【至急】成田ゆめ牧場\n{site_name}：4/4-4/5 両方空きあり！\nhttps://yumebokujo.revn.jp/camp/reserve/calendar")
                            break
        except Exception as e:
            print(f"Error at Narita: {e}")

        # --- 2. リキャンプ館山 (5/2-4 監視) ---
        try:
            print("--- Recamp Tateyama Check Start ---")
            tateyama_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-02&stay_count=2"
            page.goto(tateyama_url, timeout=60000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(10000)

            main_area = page.locator("#main_contents, .c-planListContainer, .c-planList")
            if main_area.count() > 0:
                area_text = main_area.first.inner_text()
                has_no_plan = "該当するプランがありません" in area_text
                has_positive_word = any(word in area_text for word in ["予約", "残りわずか", "￥", "選択する"])

                if not has_no_plan and has_positive_word:
                    send_line(f"【至急】リキャンプ館山\n5/2-5/4 2泊枠の空きを検知！\n{tateyama_url}")
                else:
                    print(f"Log Recamp: No vacancy found.")
            else:
                print("Log Recamp: Plan list area not found.")
        except Exception as e:
            print(f"Error at Recamp: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
