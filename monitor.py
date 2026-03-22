import os
import requests
from playwright.sync_api import sync_playwright

# --- 設定情報 ---
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

def send_line_text(message):
    if not LINE_TOKEN or not LINE_USER_ID: return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, json=payload)

def send_line_image(image_path):
    # 注: LINE Botで画像を送るには公開URLが必要なため、
    # ここでは「画像が保存できたか」をテキストで報告し、
    # 代わりに「画面の文字情報を凝縮して」送る方法を採ります。
    pass

def check_campsites():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="ja-JP", viewport={'width': 1280, 'height': 2000}
        )
        page = context.new_page()

        try:
            print("--- C&C Final Diagnosis ---")
            page.goto("https://reser.yagai-kikaku.com/cc_reserve/sv_open", timeout=60000)
            page.wait_for_timeout(3000)

            # 5月をクリック
            may_btn = page.get_by_role("link", name="5月", exact=True).first
            if may_btn.is_visible():
                may_btn.click()
                page.wait_for_timeout(10000) # 10秒待機
            
            # 診断: 画面に表示されている「月」の文字を強制取得
            current_view = page.locator("body").inner_text()
            month_check = "5月が見つかりました" if "5月" in current_view else "まだ5月ではありません"
            
            # 診断報告（LINE）
            diagnosis_msg = f"【最終診断レポート】\nステータス: {month_check}\n冒頭100文字: {current_view[:100].replace('', '')}"
            send_line_text(diagnosis_msg)

            # 表の解析（5/10ターゲット）
            rows = page.locator("tr").all()
            target_col = -1
            for row in rows:
                cells = row.locator("td, th").all()
                texts = [c.inner_text().strip() for c in cells]
                if "10" in texts and "1" in texts:
                    target_col = texts.index("10")
                    break
            
            if target_col != -1:
                target_keywords = ["チョイ広め", "広めのオート", "東屋", "プレミアム"]
                found = []
                for row in rows:
                    cells = row.locator("td").all()
                    if len(cells) <= target_col: continue
                    name = cells[0].inner_text().split('\n')[0].strip()
                    if any(k in name for k in target_keywords):
                        status = cells[target_col].inner_text().strip()
                        if "×" not in status:
                            found.append(name)
                
                if found:
                    send_line_text(f"【成功】5/10空き検知！\n・" + "\n・".join(found))
                else:
                    send_line_text("【診断】日付列は見つかりましたが、指定サイトに空き(×以外)がありませんでした。")
            else:
                send_line_text("【診断】日付の列(10日)が特定できませんでした。")

        except Exception as e:
            send_line_text(f"【致命的エラー】\n{str(e)}")

        browser.close()

if __name__ == "__main__":
    check_campsites()
