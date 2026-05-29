from fastapi import FastAPI, Request
from telegram import Update

app = FastAPI()

# esto lo conectaremos desde tu bot global
application = None


def set_application(app_instance):
    global application
    application = app_instance


@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()

    update = Update.de_json(data, application.bot)
    await application.process_update(update)

    return {"ok": True}