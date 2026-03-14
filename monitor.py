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
                if "一般" in row_text or "電源" in row_text:
                    # 「残0サイト」が含まれていなければ、空きがあると判定
                    # ※土日両方の枠に「残0サイト」がないことを行全体で判定
                    if "残0サイト" not in row_text and "受付前" not in row_text:
                        vacant_
