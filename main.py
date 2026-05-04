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

# 設定の読み込み
line_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_channel_secret = os.getenv('LINE_CHANNEL_SECRET')
api_key = os.getenv('GEMINI_API_KEY')

# AIの設定
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

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
    
    # 【ここが重要！】占い師の「性格」や「ルール」を決める指示書です
    system_prompt = (
        "あなたは一流の西洋占星術師です。"
        "以下のルールを厳守してください：\n"
        "1. 文中に ** などのマークダウン記号（米印）は絶対に使わないでください。太字にする必要はありません。\n"
        "2. 優雅で丁寧、かつ親しみやすい「占い師らしい」言葉遣いで話してください。\n"
        "3. 最後に必ず『詳細な鑑定をご希望の方は、ぜひココナラへお越しください：https://coconala.com/users/あなたのID』という案内を付けてください。"
    )

    try:
        # AIで回答作成
        response = model.generate_content(system_prompt + "\n\n相談内容：" + user_message)
        
        # 文章をきれいに整える（念のため米印をプログラムでも消す）
        clean_text = response.text.replace("*", "")

        # LINEに送信
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=clean_text)]
                )
            )
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
