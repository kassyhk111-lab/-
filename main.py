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

# LINEとGeminiの設定
line_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_channel_secret = os.getenv('LINE_CHANNEL_SECRET')
api_key = os.getenv('GEMINI_API_KEY')

# APIの初期化（安定版 v1 を使用するように設定）
genai.configure(api_key=api_key)

configuration = Configuration(access_token=line_access_token)
handler = WebhookHandler(line_channel_secret)

# 【修正ポイント】モデル名の前に 'models/' を付け、最新のフラッシュモデルを指定
model = genai.GenerativeModel('models/gemini-1.5-flash')

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
    system_prompt = "あなたはプロの西洋占星術師です。親しみやすく占ってください。"
    
    try:
        # AIで返信を生成
        response = model.generate_content(system_prompt + "\n\n内容：" + user_message)
        
        # 返信を送信
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=response.text)]
                )
            )
    except Exception as e:
        error_str = str(e)
        print(f"Error: {error_str}")
        # LINEに原因を短く表示
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f"占い失敗：{error_str[:30]}")]
                )
            )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
