import os

from dotenv import load_dotenv
from fastapi import BackgroundTasks
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from linebot import LineBotApi
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent
from pydantic import BaseModel
from pydantic import Field

app = FastAPI()


@app.get("/")
async def api_root():
    return {"message": "health check"}


load_dotenv()
line_bot_api = LineBotApi(os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])


@app.get("/health")
def check_healtch():
    return {"message": "health check"}


class Question(BaseModel):
    query: str = Field(description="メッセージ")


@app.post("/callback")
async def callback(
    request: Request,
    background_tasks: BackgroundTasks,
    summary="LINE Message APIからのコールバックです。",
):
    body = await request.body()
    try:
        background_tasks.add_task(handler.handle, body.decode("utf-8"))
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature") from None
    return "ok"


# LINE Messaging APIからのメッセージイベントを処理
@handler.add(MessageEvent)
def handle_message(event):
    if event.type != "message" or event.message.type != "text":
        return
    # ai_message = talk(Question(query=event.message.text))
    # line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ai_message))


# Run application
if __name__ == "__main__":
    app.run()
