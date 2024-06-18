from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
	ApiClient, Configuration, MessagingApi,
	ReplyMessageRequest, PushMessageRequest,
	TextMessage, PostbackAction
)
from linebot.v3.webhooks import (
	FollowEvent, MessageEvent, PostbackEvent, TextMessageContent, 
)

import os
import re
from datetime import datetime
import sys
import time
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

## .env ファイル読み込み
from dotenv import load_dotenv
load_dotenv()

## 環境変数を変数に割り当て
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]
DOWNLOAD_PASS = os.environ["DOWNLOAD_PASS"]

## Flask アプリのインスタンス化
app = Flask(__name__)

## LINE のアクセストークン読み込み
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

pattern:str = r"https://\d{1,2}\.gigafile\.nu/[a-zA-Z0-9\-]+"
group_line_id:str = 'C1b2c6d35f278a550903d14ae0373d4d7'
user_id:str = 'U878d04bfc79632d6da1c44dc35a1a1c7'
chat_type:str = 'user'


## コールバックのおまじない
@app.route("/callback", methods=['POST'])
def callback():
	# get X-Line-Signature header value
	signature = request.headers['X-Line-Signature']

	# get request body as text
	body = request.get_data(as_text=True)
	app.logger.info("Request body: " + body)

	# handle webhook body
	try:
		handler.handle(body, signature)
	except InvalidSignatureError:
		app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
		abort(400)

	return 'OK'

## 友達追加時のメッセージ送信
@handler.add(FollowEvent)
def handle_follow(event):
	## APIインスタンス化
	with ApiClient(configuration) as api_client:
		line_bot_api = MessagingApi(api_client)

	## 返信
	line_bot_api.reply_message(ReplyMessageRequest(
		replyToken=event.reply_token,
		messages=[TextMessage(text='Thank You!')]
	))
	
## オウム返しメッセージ
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
	## APIインスタンス化
	with ApiClient(configuration) as api_client:
		line_bot_api = MessagingApi(api_client)

	## 受信メッセージの中身を取得
	received_message = event.message.text

    
	send_to:str = user_id
	if event.source.type == 'group':
		send_to = event.source.group_id
	

	is_match = re.search(pattern,received_message)
	if is_match:
		gigafile_url:str = is_match.group(0)
		message:str =   'ギガファイル便のURLを検出しました。\n'\
			            'ダウンロードを開始します。\n'\
			            'リンク : {link} \n'\
			            '保存先 : {save_pass} \n'\
			            '日時 : {now_time} \n'.format(
			link = gigafile_url,
			save_pass = DOWNLOAD_PASS,
			now_time = __get_time_jpn()
        )

		line_bot_api.reply_message(ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[TextMessage(text=message)]
        ))

		__download(gigafile_url)

		is_compleated:bool = __wait_for_download_completion()

		if is_compleated:
			comp_message:str =   'ダウンロードが完了しました。\n'\
			            'リンク : {link} \n'\
			            '保存先 : {save_pass} \n'\
			            '日時 : {now_time} \n'.format(
                link = gigafile_url,
                save_pass = DOWNLOAD_PASS,
                now_time = __get_time_jpn()
            )

			__push_message(send_to, comp_message)


## 起動確認用ウェブサイトのトップページ
@app.route('/', methods=['GET'])
def toppage():
	return 'Hello world!'


def __push_message(send_to:str, messages:str):
	with ApiClient(configuration) as api_client:
		line_bot_api = MessagingApi(api_client)
	line_bot_api.push_message(PushMessageRequest(
		to=send_to, messages=[TextMessage(text=messages)]
	))


def __get_time_jpn() -> str:

	# 現在の日付と時刻を取得
    current_date = datetime.now()

    # 指定された形式でフォーマット
    formatted_date_jp = current_date.strftime("%Y年%m月%d日%H時%M分%S秒")

    return formatted_date_jp

def __download(url:str):
    global driver
    options = Options()
    options.page_load_strategy = 'eager'
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--remote-debugging-port=9222')
	# options.page_load_strategy = 'eager'
    options.add_experimental_option("prefs", {
        "download.default_directory": DOWNLOAD_PASS,
        "download.prompt_for_download": False,
    })
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_size(950, 800)
    driver.get(url)
    
    if len(driver.find_elements("xpath", "//button[text()='まとめてダウンロード']")) > 0:
        element = driver.find_element("xpath", "//button[text()='まとめてダウンロード']")
        driver.execute_script("arguments[0].scrollIntoView();", element)
        element.click()
        time.sleep(5)
    else:
        element = driver.find_element("xpath", "//button[text()='ダウンロード開始']")
        driver.execute_script("arguments[0].scrollIntoView();", element)
        element.click()
        time.sleep(5)


def __wait_for_download_completion() -> bool:
    while True:
        download_files = [f for f in os.listdir(DOWNLOAD_PASS) if f.endswith('.crdownload')]
        if not download_files:
            print("全てのダウンロードが完了しました。")
            return True
        time.sleep(1)

## ボット起動コード
if __name__ == "__main__":
	## ローカルでテストする時のために、`debug=True` にしておく
	app.run()