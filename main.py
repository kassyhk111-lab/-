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

# APIの初期化
if api_key:
    genai.configure(api_key=api_key.strip()) # strip()で前後の空白を自動削除
else:
    print("APIキーがRenderで見つかりません！")

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
    # 診断開始
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name.replace('models/', ''))
    except Exception as e:
        available_models = [f"取得失敗: {str(e)[:30]}"]

    user_message = event.message.text
    # 診断結果を元にモデルを選択（1.5-flashがあれば使い、なければ一番最初に見つかったものを使う）
    target_model = 'gemini-1.5-flash' if 'gemini-1.5-flash' in available_models else available_models[0]

    try:
        model = genai.GenerativeModel(target_model)
        response = model.generate_content("あなたは占い師です。短く占って：" + user_message)
        reply_text = response.text
    except Exception as e:
        # 失敗したら使えるモデルのリストを教えてくれる
        reply_text = f"【診断結果】\n使えるモデル: {', '.join(available_models[:3])}\nエラー: {str(e)[:30]}"

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
