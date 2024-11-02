import os

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks
from fastapi import FastAPI
from fastapi import Header
from fastapi import HTTPException
from fastapi import Request
from genre_template import genre_template
from input_comfirm_template import input_confirm_template
from linebot import LineBotApi
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import ButtonsTemplate
from linebot.models import CarouselColumn
from linebot.models import CarouselTemplate
from linebot.models import LocationMessage
from linebot.models import MessageAction
from linebot.models import MessageEvent
from linebot.models import TemplateSendMessage
from linebot.models import TextMessage
from linebot.models import URIAction
from reaction_dict import user_condition_reactions

app = FastAPI()
load_dotenv()
line_bot_api = LineBotApi(os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])
search_api_url = os.environ["SEARCH_API_URL"]

condition_list = ["絶好調", "普通", "疲れている"]
genre_list = ["アウトドア", "スポーツ", "ものづくり", "アート", "自然", "歴史", "公園"]
sense_list = ["みる！", "きく！", "あじわう！", "かおる！", "ふれる！"]

user_info = {
    "user_address": "",
    "user_latitude": 0.0,
    "user_longitude": 0.0,
    "user_condition": "",
    "genre": "",
    "sense": "",
}


@app.post("/linebot")
async def linebot(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature: str = Header(None),
) -> str:
    body = await request.body()
    try:
        background_tasks.add_task(handler.handle, body.decode("utf-8"), x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature") from None
    return "ok"


# APIにリクエストを送ってデータを取得する
def send_to_search_api(url: str, data: dict) -> dict:
    print(data)
    response = httpx.post(url, json=data)
    print(response)
    return response.json()


# LINE Messaging APIからのメッセージイベントを処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global user_info
    accept_message = TextMessage(text=event.message.text)
    if "はじめる" in accept_message.text:
        location_sentenses = ask_for_location()
        line_bot_api.reply_message(event.reply_token, location_sentenses)
        return "ok"
    elif accept_message.text in condition_list:
        messages = []
        messages.append(TextMessage(text=user_condition_reactions[accept_message.text]))
        user_info["user_condition"] = accept_message.text
        messages.append(
            TextMessage(text=genre_template.format(one_genre="\n".join(f"- {one_genre}" for one_genre in genre_list)))
        )
        line_bot_api.reply_message(event.reply_token, messages)
    elif accept_message.text in genre_list:
        messages = []
        messages.append(TextMessage(text=f"「{accept_message.text}」ですね！"))
        user_info["genre"] = accept_message.text
        messages.append(
            TextMessage(
                text=input_confirm_template.format(
                    user_address=user_info["user_address"],
                    condition=user_info["user_condition"],
                    genre=user_info["genre"],
                )
            )
        )
        line_bot_api.reply_message(event.reply_token, messages)
    elif accept_message.text in sense_list:
        message = accept_message.text
        user_info["sense"] = message.replace("！", "")
        response = recommend_place_pages()
        line_bot_api.reply_message(event.reply_token, response)
    else:
        message = TextMessage(text="お手数ですが、指定されている選択肢からお答えください。")
        line_bot_api.reply_message(event.reply_token, message)


def recommend_place_pages():
    data = {
        "keyword": user_info["genre"],
        "sense": user_info["sense"],
        "lat": user_info["user_latitude"],
        "lng": user_info["user_longitude"],
        "dist": 20.0,
    }
    responses = send_to_search_api(search_api_url, data)
    columns = [
        CarouselColumn(
            thumbnail_image_url=response["image_url"],
            title=response["名称"],
            text=response["要約"],
            actions=[URIAction(label="詳細を見る", uri=response["page_url"])],
        )
        for response in responses
    ]
    return TemplateSendMessage(alt_text="テンプレート", template=CarouselTemplate(columns=columns))


# ユーザーに選択肢を提示する
def choose_from_options(question: str, options: list):
    options = [{"type": "message", "label": option, "text": option} for option in options]
    messages = [MessageAction(label=option["label"], text=option["text"]) for option in options]
    return TemplateSendMessage(alt_text="テンプレート", template=ButtonsTemplate(text=question, actions=messages))


def ask_for_location():
    messages = [
        TextMessage(text="出発地点を登録してください！"),
        TextMessage(text="https://line.me/R/nv/location/"),
    ]
    return messages


@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    global user_info
    user_address = event.message.address
    user_latitude = event.message.latitude
    user_longitude = event.message.longitude
    user_info["user_address"] = user_address
    user_info["user_latitude"] = user_latitude
    user_info["user_longitude"] = user_longitude
    print(f"user_address: {user_address}, user_latitude: {user_latitude}, user_longitude: {user_longitude}")
    send_message = choose_from_options("今の体調を教えて！", condition_list)
    line_bot_api.reply_message(event.reply_token, send_message)


if __name__ == "__main__":
    app.run()
