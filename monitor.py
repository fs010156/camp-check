import os
import requests
from playwright.sync_api import sync_playwright

# --- 設定情報（GitHubのSecretsから自動読み込み） ---
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
        # ブラウザ起動
        browser = p.chromium.launch(headless=True)
        # 画面サイズを広めに設定
        page = browser.new_page(viewport={'width': 1280, 'height': 800})

        # --- 1. 成田ゆめ牧場 (4/4-5 厳密監視) ---
        try:
            print("Checking Narita Yume Farm...")
            page.goto("https://yumebokujo.revn.jp/camp/reserve/calendar", timeout=60000)
            
            header_cells = page.locator("tr th").all()
            col_indices = []
            for i, cell in enumerate(header_cells):
                cell_text = cell.inner_text()
                if "4/4" in cell_text or "4/5" in cell_text:
                    col_indices.append(i)

            rows = page.locator("tr").all()
            for row in rows:
                row_text = row.inner_text()
                if "一般" in row_text or "電源" in row_text:
                    cells = row.locator("td").all()
                    check_results = []
                    for idx in col_indices:
                        target_cell_text = cells[idx-1].inner_text() if len(cells) >= idx else ""
                        # 「残0サイト」がなく、かつ「受付前」でもない、かつ空でない場合にTrue
                        if "残0サイト" not in target_cell_text and "受付前" not in target_cell_text and target_cell_text.strip() != "":
                            check_results.append(True)
                        else:
                            check_results.append(False)
                    
                    if len(check_results) >= 2 and all(check_results):
                        site_type = "一般" if "一般" in row_text else "電源"
                        send_line(f"【至急】成田ゆめ牧場\n{site_type}サイト 4/4(土)・4/5(日)に空きが出ました！\nhttps://yumebokujo.revn.jp/camp/reserve/calendar")
                        break
        except Exception as e:
            print(f"Error at Narita: {e}")

        # --- 2. リキャンプ館山 (5/2-4 監視ロジック強化版) ---
        try:
            print("Checking Recamp Tateyama...")
            tateyama_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-02&stay_count=2"
            page.goto(tateyama_url, timeout=60000)
            
            # 通信が安定するまで待ち、さらに10秒間待機してJavaScriptの描画を確実に完了させる
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(10000)

            content = page.content()
            
            # 判定ロジック：
            # 「該当プランなし」の文言が消えており、かつ何らかの空きを示す言葉がある場合
            has_no_plan = "該当するプランがありません" in content
            has_positive_word = any(word in content for word in ["予約する", "残りわずか", "残数", "選択する", "￥"])

            if not has_no_plan and has_positive_word:
                send_line(f"【至急】リキャンプ館山に空きが出ました！\n5/2(土)〜5/4(月) 2泊枠\n{tateyama_url}")
            else:
                print(f"Log Recamp: NoPlanMsg={has_no_plan}, PositiveWord={has_positive_word}")
        except Exception as e:
            print(f"Error at Recamp: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
