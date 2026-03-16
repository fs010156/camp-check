import os
import requests
from playwright.sync_api import sync_playwright

# --- 設定情報（GitHubのSecretsから読み込み） ---
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

def send_line(message):
    """LINEにメッセージを送信する"""
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
        # 日本のPC環境を偽装してブラウザ起動
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
            print("--- Checking Narita Yume Farm (4/4-5) ---")
            page.goto("https://yumebokujo.revn.jp/camp/reserve/calendar", timeout=60000, wait_until="domcontentloaded")
            # ページ全体の読み込みを少し長めに待つ
            page.wait_for_timeout(10000)

            # ヘッダー要素の取得（存在確認付き）
            header_elements = page.locator("tr.calendar-head th")
            if header_elements.count() == 0:
                print("Log: Calendar header not found. Site structure might have changed.")
            else:
                headers = header_elements.all()
                target_indices = []
                for i, h in enumerate(headers):
                    h_text = h.inner_text().replace('\n', '')
                    if "4/4" in h_text or "4/5" in h_text:
                        print(f"Log: Found column '{h_text}' at index {i}")
                        target_indices.append(i)
                
                if len(target_indices) < 2:
                    print(f"Log: Target columns not fully found (Found: {len(target_indices)}).")
                else:
                    rows = page.locator("tr").all()
                    for row in rows:
                        cells = row.locator("td").all()
                        if len(cells) <= max(target_indices): continue
                        
                        site_name = cells[0].inner_text()
                        if "一般" in site_name or "電源" in site_name:
                            # 各日付の空き状況を確認
                            v44 = False
                            v45 = False
                            for idx in target_indices:
                                h_text = headers[idx].inner_text()
                                cell_content = cells[idx].inner_text()
                                if "残0" not in cell_content and any(c.isdigit() for c in cell_content):
                                    if "4/4" in h_text: v44 = True
                                    if "4/5" in h_text: v45 = True
                            
                            if v44 and v45:
                                send_line(f"【至急】成田ゆめ牧場\n{site_name}：4/4(土)-4/5(日) 両方の空きを検知！\nhttps://yumebokujo.revn.jp/camp/reserve/calendar")
                                break
        except Exception as e:
            print(f"Error Narita: {e}")

        # --- 2. リキャンプ館山 (5/2-4 GW連泊監視) ---
        try:
            print("--- Checking Recamp Tateyama (5/2-4) ---")
            target_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-02&stay_count=2"
            page.goto(target_url, timeout=60000, wait_until="networkidle")
            
            # JavaScript描画をじっくり待機
            page.wait_for_timeout(15000)

            # 判定：プランなし表示がなく、かつ「予約」や「選択」ボタンが見つかること
            has_no_plan = page.get_by_text("該当するプランがありません").is_visible()
            
            # ボタン要素を個別にカウント（エラー回避のため）
            btn_reserve = page.locator("a, button, .c-btn").filter(has_text="予約").count()
            btn_select = page.locator("a, button, .c-btn").filter(has_text="選択").count()
            btns = btn_reserve + btn_select

            # バックアップ判定：ボタンがなくても「￥」マークがあれば空きとみなす
            body_text = page.locator("body").inner_text()
            has_yen = "￥" in body_text

            if not has_no_plan and (btns > 0 or has_yen):
                send_line(f"【至急】リキャンプ館山に空き！\n5/2(土)〜5/4(月) 2泊枠が予約可能です！\n{target_url}")
            else:
                print(f"Log Recamp: No vacancy (NoPlan={has_no_plan}, Btns={btns}, Yen={has_yen})")

        except Exception as e:
            print(f"Error Recamp: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
