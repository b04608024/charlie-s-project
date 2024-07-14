# -*- coding: utf-8 -*-
"""
Created on Wed Jun 26 10:16:53 2024

@author: alien
"""

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
import schedule
import time
import threading
from datetime import datetime

app = Flask(__name__)

# Your LINE Bot Channel Access Token and Channel Secret
LINE_CHANNEL_ACCESS_TOKEN = 'EtivmfiXe9l2oIbk5ZPChrDCxhpp5CdCBwnufZuVUb36XfQKbk2HkT+gK0bYY2BxzhSBk86nUnAw/PJ5h/Y+5CcDKlxYeq8NYaH3KWtxavdhOwhtuk+HYllAoeWn87dZVt8lFKL8JYacGBfmr1RdHQdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '46184d758a3dcbff8dcc63739c63ca0f'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    # Get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # Get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # Handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

def send_daily_picture(user_id='Ub11277a8e3b6e7c1e428ed59c2fd1bcd'):
    image_url = 'https://pbs.twimg.com/media/DutSvz1X4AE7XGn.jpg'
    line_bot_api.push_message(user_id, ImageSendMessage(original_content_url=image_url, preview_image_url=image_url))

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Schedule the job every day at a specific time
schedule.every().day.at("22:00").do(send_daily_picture)

# Start the scheduler in a separate thread
threading.Thread(target=run_schedule).start()

user_schedules = {}

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text
    
    if text.startswith("schedule "):
        time_str = text.split("schedule ")[1]
        try:
            datetime.strptime(time_str, "%H:%M")
            user_schedules[user_id] = time_str
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"Scheduled picture message at {time_str} daily."))
        except ValueError:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Invalid time format. Please use HH:MM format."))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="To schedule a picture message, send 'schedule HH:MM'."))

def send_user_picture(user_id, time_str):
    schedule.every().day.at(time_str).do(lambda: send_daily_picture(user_id))

def run_user_schedules():
    while True:
        for user_id, time_str in user_schedules.items():
            send_user_picture(user_id, time_str)
        schedule.run_pending()
        time.sleep(1)

# Start the user schedule thread
threading.Thread(target=run_user_schedules).start()

if __name__ == "__main__":
    app.run(port=5000)



