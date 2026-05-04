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

# 安全設定を「すべて許可」に設定（占いがブロックされないようにするため）
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    safety_settings=safety_settings
)

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
    system_prompt = "あなたはプロの西洋占星術師です。親しみやすく占ってください。最後に必ず『詳細鑑定はココナラへ：https://coconala.com/users/あなたのID』と付けてください。"
    
    print(f"受信メッセージ: {user_message}") # ログ出力

    try:
        # AIで返信を生成
        response = model.generate_content(system_prompt + "\n\n相談内容：" + user_message)
        
        # もし返信が空っぽだった場合の対策
        if not response.text:
            reply_text = "すみません、うまく占えませんでした。もう一度聞いてみてください。"
        else:
            reply_text = response.text

        # LINEに返信を送信
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
        print("返信送信成功")

    except Exception as e:
        print(f"エラー発生: {e}")
        # エラーが起きたことをユーザーに伝える（デバッグ用）
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="ごめんなさい、ちょっと考えがまとまりませんでした。もう一度送ってみてください！")]
                )
            )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
