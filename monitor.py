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
        # 人間に見せかけるための詳細設定
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 1200}
        )
        page = context.new_page()

        # --- リキャンプ館山 5/9-11 再検証 ---
        try:
            print("--- Recamp Tateyama Diagnosis Start ---")
            test_url = "https://www.nap-camp.com/chiba/14639/plans?checkin_date=2026-05-09&stay_count=2"
            
            # ページ移動
            response = page.goto(test_url, timeout=60000, wait_until="networkidle")
            print(f"Log: HTTP Status = {response.status}")
            
            # JavaScriptの実行を十分に待つ
            page.wait_for_timeout(15000) 

            # 【重要】今の画面を画像として保存（GitHub ActionsのArtifactsで確認可能）
            page.screenshot(path="recamp_debug.png")
            print("Log: Screenshot saved as recamp_debug.png")

            # 判定処理
            content = page.content()
            main_area = page.locator("#main_contents, .c-planListContainer, .c-planList")
            
            if main_area.count() > 0:
                area_text = main_area.first.inner_text()
                has_no_plan = "該当するプランがありません" in area_text
                # 「予約」という文字の代わりに「￥」や「宿泊」など、もっと広い範囲で探す
                has_vacancy = any(word in area_text for word in ["￥", "選択する", "次へ", "残り"])

                print(f"Log: has_no_plan_msg={has_no_plan}, has_vacancy_keyword={has_vacancy}")

                if not has_no_plan and has_vacancy:
                    send_line(f"【検証成功】リキャンプ館山を検知！\n{test_url}")
                else:
                    print("Log: vacancy not found in main area text.")
            else:
                print("Log: CRITICAL - Main area not found in HTML.")
                # エリアが見つからない場合、HTML構造を一部出力して解析
                print(f"Log: HTML Length = {len(content)}")

        except Exception as e:
            print(f"Error: {e}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
