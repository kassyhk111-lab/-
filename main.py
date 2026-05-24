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
def get_ai_reply(user_data, user_message):

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
あなたは西洋占星術の占い師HIDEです。

以下の情報をもとに、
優しく、寄り添うように鑑定してください。

【名前】
{user_data.get("name", "")}

【生年月日】
{user_data.get("birth", "")}

【相談内容】
{user_data.get("problem", "")}

【理想の未来】
{user_message}
"""

    json_data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": prompt
            }
        ]
    }

    try:

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=json_data
        )

        result = response.json()

        ai_reply = result["choices"][0]["message"]["content"]

        ai_reply += """

━━━━━━━━━━━

今回の鑑定では、
恋愛運に大きな転換期が出ていました🔮

ただ、
今回の無料鑑定では、
まだ“表面部分”しか見れていません。

本格鑑定では、

・相手の本音
・今後3ヶ月の流れ
・恋愛成就のタイミング
・あなたが今やるべきこと

まで深く読み解いていきます✨

続きが気になる方はこちら👇

（ここにココナラURL）

━━━━━━━━━━━
"""

        return ai_reply

    except Exception as e:

        print(e)

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

    if user_id not in user_states:

        user_states[user_id] = {
            "step": "completed"
        }

    current_step = user_states[user_id]["step"]

    # 名前入力
    if current_step == "waiting_name":

        user_states[user_id]["name"] = user_message
        user_states[user_id]["step"] = "waiting_birth"

        reply_text = (
            f"{user_message}さん、ありがとうございます✨\n\n"
            "次に生年月日を教えてください😊\n"
            "（例：1995/03/21）"
        )

    # 生年月日入力
    elif current_step == "waiting_birth":

        user_states[user_id]["birth"] = user_message
        user_states[user_id]["step"] = "waiting_problem"

        reply_text = (
            "ありがとうございます🔮\n\n"
            "今、特に占ってほしいことを教えてください✨"
        )

    # 悩み入力
    elif current_step == "waiting_problem":

        user_states[user_id]["problem"] = user_message
        user_states[user_id]["step"] = "waiting_future"

        reply_text = (
            "ありがとうございます✨\n\n"
            "では最後に、\n"
            "これからどうなっていきたいですか？🔮"
        )

    # 理想未来入力 → AI鑑定
    elif current_step == "waiting_future":

        reply_text = get_ai_reply(
            user_states[user_id],
            user_message
        )

        user_states[user_id]["step"] = "completed"

    # 通常会話
    else:

        reply_text = (
            "鑑定をご希望の場合は、\n"
            "一度ブロック解除して最初からお試しください🔮"
        )

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
