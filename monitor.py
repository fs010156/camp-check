import os
import requests
from playwright.sync_api import sync_playwright

# --- 設定情報（GitHubのSecretsから読み込み） ---
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

def send_line(message):
    """LINEにメッセージを送信する関数"""
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
        # ブラウザ起動（Headlessモード）
        browser = p.chromium.launch(headless=True)
        # 画面サイズを広めに設定（描画のズレを防ぐ）
        page = browser.new_page(viewport={'width': 1280, 'height': 800})

        # --- 1. 成田ゆめ牧場 (4/4-5 ピンポイント監視) ---
        try:
            print("Checking Narita Yume Farm...")
            page.goto("https://yumebokujo.revn.jp/camp/reserve/calendar", timeout=60000)
            
            # カレンダーのヘッダーからターゲット日の列番号を特定
            headers = page.locator("tr.calendar-head th").all()
            target_indices = []
            for i, h in enumerate(headers):
                h_text = h.inner_text().replace('\n', '')
                if "4/4" in h_text or "4/5" in h_text:
                    print(f"Log: Found target column '{h_text}' at index {i}")
                    target_indices.append(i)
            
            # 各サイト（一般/電源）の行をチェック
            rows = page.locator("tr").all()
            for row in rows:
                cells = row.locator("td").all()
                if len(cells) == 0: continue
                
                site_name = cells[0].inner_text()
                if "一般" in site_name or "電源" in site_name:
                    is_4_4_ok = False
                    is_4_5_ok = False
                    
                    for idx in target_indices:
                        if idx < len(cells):
                            cell_content = cells[idx].inner_text()
                            # 「残0」がなく、かつ何らかの数字（残数）が含まれているか
                            if "残0" not in cell_content and any(c.isdigit() for c in cell_content):
                                if "4/4" in headers[idx].inner_text(): is_4_4_ok = True
                                if "4/5" in headers[idx].inner_text(): is_4_5_ok = True
                    
                    # 4/4と4/5の両方が空いている場合のみ通知
                    if is_4_4_ok and is_4_5_ok:
                        send_line(f"【至急】成田ゆめ牧場\n{site_name}：4/4(土)・4/5(日) 両方の空きを検知！\nhttps://yumebokujo.revn.jp/camp/reserve/calendar")
                        break
        except Exception as e:
            print(f"Error at Narita: {e}")

        # --- 2. リキャンプ館山 (5/2-4 エリア限定監視) ---
        try:
            print("Checking Recamp Tateyama...")
            tateyama_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-02&stay_count=2"
            page.goto(tateyama_url, timeout=60000)
            
            # 通信と描画の完了をしっかり待機
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(10000)

            # メインのプランリストエリアに絞ってテキスト解析
            main_area = page.locator("#main_contents, .c-planListContainer, .c-planList")
            if main_area.count() > 0:
                area_text = main_area.first.inner_text()
                # 「該当プランなし」がなく、かつ「予約」や「￥」などの空きを示す言葉があるか
                has_no_plan = "該当するプランがありません" in area_text
                has_positive_word = any(word in area_text for word in ["予約", "残りわずか", "￥", "選択する"])

                if not has_no_plan and has_positive_word:
                    send_line(f"【至急】リキャンプ館山\n5/2(土)〜5/4(月) 2泊枠の空きを検知！\n{tateyama_url}")
                else:
                    print(f"Log Recamp: No vacancy (NoPlanMsg={has_no_plan})")
            else:
                print("Log Recamp: Plan list area not found.")
        except Exception as e:
            print(f"Error at Recamp: {e}")

        browser.close()

if __name__ == "__main__":
