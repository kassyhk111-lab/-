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

# 【修正】通信を安定させる設定を追加
if api_key:
    genai.configure(api_key=api_key.strip(), transport='rest')
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
    # 米印を使わない、ココナラ宣伝入りのプロンプト
    system_prompt = (
        "あなたはプロの西洋占星術師です。優雅な敬語で占ってください。"
        "回答に ** などの記号は一切使わないでください。"
        "最後に必ず『詳細鑑定はココナラへ：https://coconala.com/users/あなたのID』と付けてください。"
    )

    try:
        # AIで回答作成
        response = model.generate_content(system_prompt + "\n\n相談：" + user_message)
        
        # 文章をきれいに掃除（米印を消す）
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
        # 【重要】エラーが出たらLINEに詳細を報告させる
        error_msg = str(e)
        with ApiClient(configuration) a
