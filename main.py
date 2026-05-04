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
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

configuration = Configuration(access_token=line_access_token)
handler = WebhookHandler(line_channel_secret)

# 【最重要】現在最も安定しているモデル名に固定します
model = genai.GenerativeModel('gemini-1.5-flash')

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
        print(f"エラー内容: {e}")
        # 失敗したときにLINEにエラー内容の一部を出すようにしました（原因特定のため）
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f"ごめんなさい、占えませんでした。({str(e)[:20]})")]
                )
            )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
