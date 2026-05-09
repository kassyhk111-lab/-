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

# 環境変数
LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 安全チェック（ここ重要）
if not GEMINI_API_KEY:
    raise Exception("GEMINI_API_KEY が未設定")

# Gemini（旧安定SDKに統一）
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")


@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_data(as_text=True)
    signature = request.headers.get("X-Line-Signature")

    try:
        handler.handle(body, signature)
    except Exception:
        abort(400)

    return "OK"


handler = WebhookHandler(LINE_CHANNEL_SECRET)


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text

    prompt = (
        "あなたはプロの西洋占星術師です。"
        "丁寧な敬語で占ってください。"
        "記号は使わないでください。"
        "\n\n相談内容：" + user_message
    )

    try:
        response = model.generate_content(prompt)
        reply_text = response.text

    except Exception as e:
        reply_text = f"エラー：{str(e)[:80]}"

    with ApiClient(Configuration(access_token=LINE_ACCESS_TOKEN)) as api_client:
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
