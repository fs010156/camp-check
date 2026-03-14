import os
import requests

# LINE通知設定
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

def send_line(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    r = requests.post(url, headers=headers, json=payload)
    print(f"Response: {r.status_code}, {r.text}")

if __name__ == "__main__":
    # 空き状況を無視して、即座にテストメッセージを送信します
    send_line("【疎通テスト】GitHub Actionsからの通知に成功しました！このメッセージが届いていれば、連携設定は完璧です。")
