from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
	ApiClient, Configuration, MessagingApi,
	ReplyMessageRequest, PushMessageRequest,
	TextMessage, PostbackAction
)
from linebot.v3.webhooks import (
	FollowEvent, MessageEvent, PostbackEvent, TextMessageContent
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

pattern:str = r"https://gigafile\.nu/[a-zA-Z0-9]+"


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

	## APIを呼んで送信者のプロフィール取得
	profile = line_bot_api.get_profile(event.source.user_id)
	display_name = profile.display_name

	is_match = re.search(pattern,received_message)
	if is_match:
		gigafile_url:str = is_match.group(0)
		message:str = """
            @{display_name}
            ギガファイル便のURLを検出しました。
			ダウンロードを開始します。
			リンク : {link}
			保存先 : {save_pass}
			日時 : {now_time}
        """.format(
			display_name = display_name,
			link = gigafile_url,
			save_pass = DOWNLOAD_PASS,
			now_time = __get_time_jpn()
        )

		__reply_message(event, message)

		__download()

		is_compleated:bool = __wait_for_download_completion()

		if is_compleated:
			__reply_message(event, "全てのダウンロードが完了しました。")


## 起動確認用ウェブサイトのトップページ
@app.route('/', methods=['GET'])
def toppage():
	return 'Hello world!'

## LINE メッセージ返信共通関数
def __reply_message(event:MessageEvent, message:str):

	## APIインスタンス化
	with ApiClient(configuration) as api_client:
		line_bot_api = MessagingApi(api_client)
	line_bot_api.reply_message(ReplyMessageRequest(
		replyToken=event.reply_token,
		messages=[TextMessage(text=message)]
	))


def __get_time_jpn() -> str:

	# 現在の日付と時刻を取得
    current_date = datetime.now()

    # 指定された形式でフォーマット
    formatted_date_jp = current_date.strftime("%Y年%m月%d日%H時%M分%S秒")

    return formatted_date_jp

def __download(url):
    global driver
    options = Options()
    options.page_load_strategy = 'eager'
    options.add_experimental_option("prefs", {
        "download.default_directory": DOWNLOAD_PASS,
        "download.prompt_for_download": False,
    })
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    element = driver.find_element("xpath", "//button[text()='まとめてダウンロード']")
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
	app.run(host="0.0.0.0", port=8000, debug=True)