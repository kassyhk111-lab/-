from flask import Flask, request, abort
import os
import requests

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    FollowEvent
)

app = Flask(__name__)

LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

configuration = Configuration(access_token=LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ユーザー状態保存
user_states = {}


# -------------------------
# OpenAI返信
# -------------------------
def get_ai_reply(user_message):

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    json_data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "あなたは優秀で親しみやすい西洋占星術の占い師です。"
                    "名前は占い師HIDEです。"
                    "優しく、自然な日本語で返信してください。"
                )
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=json_data
    )

    result = response.json()

    try:
        return result["choices"][0]["message"]["content"]

    except:
        return "現在AI返信でエラーが発生しています。"


# -------------------------
# Webhook
# -------------------------
@app.route("/callback", methods=["POST"])
def callback():

    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)

    except InvalidSignatureError:
        abort(400)

    return "OK"


# -------------------------
# 友達追加時
# -------------------------
@handler.add(FollowEvent)
def handle_follow(event):

    user_id = event.source.user_id

    user_states[user_id] = {
        "step": "waiting_name"
    }

    welcome_message = (
        "友達追加ありがとうございます🔮\n\n"
        "西洋占星術鑑定をしている\n"
        "占い師HIDEです✨\n\n"
        "あなた専用の占いを始めます😊\n\n"
        "まずは、お名前（ニックネームOK）を教えてください✨"
    )

    with ApiClient(configuration) as api_client:

        line_bot_api = MessagingApi(api_client)

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=welcome_message)
                ]
            )
        )


# -------------------------
# メッセージ受信
# -------------------------
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):

    user_id = event.source.user_id
    user_message = event.message.text

    # 初回：名前入力
    if user_id in user_states:

        if user_states[user_id]["step"] == "waiting_name":

            user_states[user_id]["name"] = user_message
            user_states[user_id]["step"] = "waiting_birth"

            reply_text = (
                f"{user_message}さん、ありがとうございます✨\n\n"
                "次に生年月日を教えてください😊\n"
                "（例：1995/03/21）"
            )

        elif user_states[user_id]["step"] == "waiting_birth":

            user_states[user_id]["birth"] = user_message
            user_states[user_id]["step"] = "completed"

            reply_text = (
                "ありがとうございます🔮\n\n"
                "今、特に占ってほしいことを教えてください✨"
            )

        else:

            reply_text = get_ai_reply(user_message)

    else:

        reply_text = get_ai_reply(user_message)

    with ApiClient(configuration) as api_client:

        line_bot_api = MessagingApi(api_client)

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=reply_text)
                ]
            )
        )


# -------------------------
# 起動
# -------------------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8080))

    app.run(
        host="0.0.0.0",
        port=port
    )
