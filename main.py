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

# LINEとGeminiの設定を読み込む
line_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_channel_secret = os.getenv('LINE_CHANNEL_SECRET')
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

configuration = Configuration(access_token=line_access_token)
handler = WebhookHandler(line_channel_secret)
model = genai.GenerativeModel(「gemini-pro」)

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
    # AIへの指示（プロンプト）
    system_prompt = "あなたはプロの西洋占星術師です。親しみやすく占ってください。最後に必ず『詳細鑑定はココナラへ：https://coconala.com/users/あなたのID』と付けてください。"
    user_message = event.message.text
    
    # AIで返信を生成
    response = model.generate_content(system_prompt + "\n\n相談内容：" + user_message)
    
    # LINEに返信を送信
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=response.text)]
            )
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
