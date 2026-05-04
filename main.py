import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import google.generativeai as genai

app = Flask(__name__)

# 設定
line_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_channel_secret = os.getenv('LINE_CHANNEL_SECRET')
api_key = os.getenv('GEMINI_API_KEY')

# AIの設定
if api_key:
    genai.configure(api_key=api_key.strip())

# 【修正】モデル名を正式なパスで指定します
model = genai.GenerativeModel('models/gemini-1.5-flash')

configuration = Configuration(access_token=line_access_token)
handler = WebhookHandler(line_channel_secret)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    # 米印（**）を使わないように、かなり厳しくAIに指示します
    system_prompt = (
        "あなたは一流の占い師です。優雅な敬語で占ってください。"
        "【厳禁】文中に ** や * などの記号は絶対に一か所も使わないでください。"
        "文章だけで構成し、最後に『良い一日を！』と付けてください。"
    )

    try:
        response = model.generate_content(system_prompt + "\n\n相談：" + user_message)
        
        # 万が一AIが米印を使っても、ここで強制的に消去します
        clean_text = response.text.replace("*", "")

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=clean_text)]
                )
            )
    except Exception as e:
        # 失敗したとき、エラーの内容をLINEに送る
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f"失敗：{str(e)[:40]}")]
                )
            )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
