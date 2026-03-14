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
    requests.post(url, headers=headers, json=payload)

def check_campsites():
    with sync_playwright() as p:
        # ブラウザ起動（Headlessモード）
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 800})

        # --- 1. 成田ゆめ牧場 (4/4-5 土日両方の空きを監視) ---
        try:
            page.goto("https://yumebokujo.revn.jp/camp/reserve/calendar", timeout=60000)
            rows = page.locator("tr").all()
            for row in rows:
                text = row.inner_text()
                # 「一般」か「電源」の行を対象にする
                if "一般" in text or "電源" in text:
                    # その行全体で「残0サイト」と「受付前」が含まれていなければ空きありと判定
                    if "残0サイト" not in text and "受付前" not in text:
                        site_type = "一般" if "一般" in text else "電源"
                        send_line(f"【キャンプ空き通知】\n成田ゆめ牧場：{site_type}サイト\n日程：4/4(土)〜4/5(日)に空きが出ました！\nhttps://yumebokujo.revn.jp/camp/reserve/calendar")
                        break # 通知は1回で十分なのでループを抜ける
        except Exception as e:
            print(f"Error at Narita Yume Farm: {e}")

        # --- 2. リキャンプ館山 (5/2-4 GW連泊を監視) ---
        try:
            # 5/2〜2泊の条件を指定したURL
            tateyama_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-02&stay_count=2"
            page.goto(tateyama_url, timeout=60000)
            
            # 検索結果の描画を待機（検証で有効だった7秒設定）
            page.wait_for_timeout(7000)
            
            content = page.content()
            # 「該当プランなし」が表示されておらず、かつ「予約する」ボタンがある場合
            if "該当するプランがありません" not in content and "予約する" in content:
                send_line(f"【キャンプ空き通知】\nリキャンプ館山\n日程：5/2(土)〜5/4(月) の連泊予約が可能です！\n{tateyama_url}")
        except Exception as e:
            print(f"Error at Recamp Tateyama: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
