import os
import requests
from playwright.sync_api import sync_playwright

# --- 設定情報（GitHubのSecretsから読み込み） ---
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

def send_line(message):
    """LINE公式アカウントを通じて通知を送信する"""
    if not LINE_TOKEN or not LINE_USER_ID:
        print("Error: LINE_TOKEN or LINE_USER_ID is not set.")
        return
    
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send LINE: {e}")

def check_campsites():
    with sync_playwright() as p:
        # ブラウザの起動（Headlessモード）
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # --- 1. 成田ゆめ牧場 (4/4-5 監視) ---
        # 条件：一般or電源のいずれかの行で、4/4と4/5の両方に「残0サイト」がないこと
        try:
            print("Checking Narita Yume Farm...")
            page.goto("https://yumebokujo.revn.jp/camp/reserve/calendar", timeout=60000)
            
            # カレンダーの各行（tr）をループして判定
            rows = page.locator("tr").all()
            vacant_found = False
            found_site_type = ""

            for row in rows:
                row_text = row.inner_text()
                # ターゲットとする区分（一般または電源）のみをチェック
              # 「一般」の行で、かつ「残0サイト」がない場合に必ず通知が飛ぶようにします
if "一般" in row_text and "残0サイト" not in row_text:
    vacant_found = True
    found_site_type = "テスト検証"
    break
                    # 「残0サイト」が含まれていなければ、空きがあると判定
                    # ※土日両方の枠に「残0サイト」がないことを行全体で判定
                    if "残0サイト" not in row_text and "受付前" not in row_text:
                        vacant_found = True
                        found_site_type = "一般" if "一般" in row_text else "電源"
                        break

            if vacant_found:
                msg = f"【空き通知】成田ゆめ牧場\n{found_site_type}サイトで 4/4(土)-4/5(日) の空きが出た可能性があります！\nhttps://yumebokujo.revn.jp/camp/reserve/calendar"
                send_line(msg)
        except Exception as e:
            print(f"Error at Narita Yume Farm: {e}")

        # --- 2. リキャンプ館山 (5/2-4 監視) ---
        # 条件：5/2から2泊で絞り込み、「該当プランなし」が消えて「予約する」が出現すること
        try:
            print("Checking Recamp Tateyama...")
            # 5/2〜2泊の条件を指定したURL
            tateyama_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-02&stay_count=2"
            page.goto(tateyama_url, timeout=60000)
            
            # 検索結果の読み込み待ち（3秒）
            page.wait_for_timeout(3000)
            
            content = page.content()
            # 「該当するプランがありません」という文字がなく、かつ「予約する」ボタンがある場合
            if "該当するプランがありません" not in content and "予約する" in content:
                msg = "【空き通知】リキャンプ館山\n5/2(土)-5/4(月) の空き（予約可能プラン）が出現しました！\n" + tateyama_url
                send_line(msg)
        except Exception as e:
            print(f"Error at Recamp Tateyama: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
