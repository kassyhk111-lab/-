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

# 環境変数の取得
line_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_channel_secret = os.getenv('LINE_CHANNEL_SECRET')
api_key = os.getenv('GEMINI_API_KEY')

# AIの設定（APIキーがある場合のみ設定する）
if api_key:
    genai.configure(api_key=api_key.strip())

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
    # 占い師の設定
    system_prompt = (
        "あなたは一流の西洋占星術師です。優雅な敬語で占ってください。"
        "回答に ** などの記号は一切使わないでください。"
        "最後に必ず『詳細鑑定はココナラへ：https://coconala.com/users/あなたのID』と付けてください。"
    )

    try:
        # メッセージ受信時にモデルを初期化する（起動時のエラーを防ぐため）
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(system_prompt + "\n\n相談内容：" + user_message)
        
        # 文章をきれいに整える
        reply_text = response.text.replace("*", "")

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
    except Exception as e:
        # エラーが起きたらLINEに報告する
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f"占い失敗：{str(e)[:50]}")]
                )
            )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
