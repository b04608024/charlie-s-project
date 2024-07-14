import subprocess
import logging
import os
from datetime import datetime

# Function to list installed packages
def list_installed_packages():
    installed_packages = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
    print('Installed packages: \n{}'.format(installed_packages.decode('utf-8')))

list_installed_packages()

import pytz

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import schedule
import time
import requests

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

keywords = ["bioinformatics"]  # Default keyword
target_journals = ["Nature", "Science", "Cell", "EMBO", "PNAS"]
num_articles = 3  # Default number of articles to send per day
notification_time = "09:00"  # Default notification time
local_tz = pytz.timezone('Asia/Taipei')  # Set your local timezone here

@app.route("/")
def index():
    return "Line bot is running."

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info('Received request: %s', body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error('Invalid signature error')
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.lower()
    app.logger.info('Received message: %s', text)
    global num_articles
    global notification_time
    reply = ""

    if text.startswith("keyword:"):
        keyword = text.split(":", 1)[1].strip()
        keywords.append(keyword)
        reply = f"Keyword '{keyword}' added."
        app.logger.info('Added keyword: %s', keyword)
    elif text.startswith("journal:"):
        journal = text.split(":", 1)[1].strip()
        target_journals.append(journal)
        reply = f"Journal '{journal}' added."
        app.logger.info('Added journal: %s', journal)
    elif text.startswith("remove keyword:"):
        keyword = text.split(":", 1)[1].strip()
        if keyword in keywords:
            keywords.remove(keyword)
            reply = f"Keyword '{keyword}' removed."
            app.logger.info('Removed keyword: %s', keyword)
        else:
            reply = f"Keyword '{keyword}' not found."
            app.logger.info('Keyword not found: %s', keyword)
    elif text.startswith("remove journal:"):
        journal = text.split(":", 1)[1].strip()
        if journal in target_journals:
            target_journals.remove(journal)
            reply = f"Journal '{journal}' removed."
            app.logger.info('Removed journal: %s', journal)
        else:
            reply = f"Journal '{journal}' not found."
            app.logger.info('Journal not found: %s', journal)
    elif text.startswith("time:"):
        notification_time = text.split(":", 1)[1].strip()
        reply = f"Notification time set to {notification_time}."
        app.logger.info('Notification time set to: %s', notification_time)
    elif text.startswith("num articles:"):
        num_articles = int(text.split(":", 1)[1].strip())
        reply = f"Number of articles to send set to {num_articles}."
        app.logger.info('Number of articles set to: %d', num_articles)
    else:
        reply = ("Please send a valid command (e.g., 'keyword: DNA', 'journal: Nature', "
                 "'remove keyword: DNA', 'remove journal: Nature', 'time: 09:00', 'num articles: 2').")
        app.logger.info('Invalid command received: %s', text)

    if reply:
        app.logger.info('Sending reply: %s', reply)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
    else:
        app.logger.error('No valid command found in message: %s', text)

def search_articles():
    if not keywords:
        return
    search_query = " OR ".join(keywords)
    journal_query = " OR ".join([f'"{journal}"[Journal]' for journal in target_journals])
    query = f'{search_query} AND ({journal_query})'
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmode=json&sort=pub+date&retmax={num_articles}"
    response = requests.get(url)
    if response.status_code == 200:
        article_ids = response.json()['esearchresult']['idlist']
        for article_id in article_ids:
            fetch_article(article_id)
    else:
        app.logger.error("Error fetching articles: %s", response.text)

def fetch_article(article_id):
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={article_id}&retmode=json"
    response = requests.get(url)
    if response.status_code == 200:
        article = response.json()['result'][article_id]
        title = article['title']
        url = f"https://pubmed.ncbi.nlm.nih.gov/{article_id}/"
        message = f"Title: {title}\nLink: {url}"
        app.logger.info("Fetched article: %s", message)
        line_bot_api.broadcast(TextSendMessage(text=message))
    else:
        app.logger.error("Error fetching article %s: %s", article_id, response.text)

def job():
    app.logger.info("Running scheduled job")
    search_articles()

def convert_to_utc(local_time_str, local_tz):
    local_time = datetime.strptime(local_time_str, '%H:%M').replace(tzinfo=local_tz)
    utc_time = local_time.astimezone(pytz.utc)
    return utc_time.strftime('%H:%M')

utc_notification_time = convert_to_utc(notification_time, local_tz)
app.logger.info("Scheduled job time in UTC: %s", utc_notification_time)
schedule.every().day.at(utc_notification_time).do(job)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
