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

	if '/schedule' in received_message:
		__get_246_schedule()

    
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
	__get_bass_on_top_schedule()
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
	download_url:str = ""
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
	driver.get_cookies()
    
	if len(driver.find_elements("xpath", "//button[text()='まとめてダウンロード']")) > 0:
		download_url = url + "/download.php?file=" + url.split("/")[-1]
		
	else:
		download_url = url + "/dl_zip.php?file=" + url.split("/")[-1]
		

def __wait_for_download_completion() -> bool:
    while True:
        download_files = [f for f in os.listdir(DOWNLOAD_PASS) if f.endswith('.crdownload')]
        if not download_files:
            print("全てのダウンロードが完了しました。")
            return True
        time.sleep(1)

def __get_246_schedule():
	global driver
	options = Options()
	options.page_load_strategy = 'eager'
	options.add_argument('--headless')
	options.add_argument('--disable-gpu')
	options.add_argument('--no-sandbox')
	options.add_argument('--disable-dev-shm-usage')
	options.add_argument('--remote-debugging-port=9222')
	driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
	driver.set_window_size(950, 800)
	driver.get('https://www.studio246.net/mypage/login.php')
	name_box = driver.find_element(By.NAME,'login_mail')
	name_box.send_keys("syota.mail.magazine5396@gmail.com")
	password_box = driver.find_element(By.NAME,'login_pass')
	password_box.send_keys("r13143256")
	login_btn = driver.find_element(By.NAME,'Submit_login')
	login_btn.click()
	driver.implicitly_wait(2)
	driver.get_cookies()
	driver.get('https://www.studio246.net/mypage/history.php?t=1718881330')
	tables = driver.find_elements(By.TAG_NAME, 'table')
	for idx, table in enumerate(tables):
		table_num = idx + 1

		# 利用日時を取得する
		studio_days = table.find_elements("xpath", "//*[@id='contents']/table[{}]/tbody/tr[2]/td/div[1]/p[2]".format(table_num))[0].text

		# 利用日時を日付変換し、現在時間との比較を行う
		if __judge_studio_days(studio_days):

			# display:noneとなっている要素があるため
			# 先にクリックしておく
			table_click = table.find_element("xpath", "//*[@id='contents']/table[{}]/tbody/tr[2]".format(table_num))
			table_click.click()
			
			# 0時のより後の場合のみ処理を行う
			# スタジオ名
			studio_name = table.find_elements("xpath", "//*[@id='contents']/table[{}]/tbody/tr[2]/td/div[1]/p[1]/span".format(table_num))[0].text
			# 開始時間:終了時間を取得
			date_end_time_str = table.find_elements("xpath", "//*[@id='contents']/table[{}]/tbody/tr[3]/td".format(table_num))[0].accessible_name
			# 開始時間/終了時間をリストに変換
			date_list = __change_date_element_to_string(date_end_time_str)
			# 予約番号を取得
			reservation_number = table.find_elements("xpath", "//*[@id='contents']/table[{}]/tbody/tr[5]/td".format(table_num))[0].text
			
			print(date_list)


def __get_bass_on_top_schedule():
	global driver
	options = Options()
	options.page_load_strategy = 'eager'
	options.add_argument('--headless')
	options.add_argument('--disable-gpu')
	options.add_argument('--no-sandbox')
	options.add_argument('--disable-dev-shm-usage')
	options.add_argument('--remote-debugging-port=9222')
	driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
	driver.set_window_size(950, 800)
	driver.get('https://studi-ol.com/')
	# ログイン情報入力
	flowting_btn = driver.find_element("xpath",'//*[@id="home"]/div[2]/header/div/div/nav/div/div[1]/ul/li/a')
	flowting_btn.click()
	name_box = driver.find_element("xpath", '//*[@id="email"]')
	name_box.send_keys("shota.5396@gmail.com")
	password_box = driver.find_element("xpath", '//*[@id="password"]')
	password_box.send_keys("r13143256")
	login_btn = driver.find_element("xpath",'//*[@id="home"]/div[2]/header/div/div/nav/div/div[1]/ul/li/div/form/p/button')
	login_btn.click()
	driver.implicitly_wait(3)
	driver.get_cookies()
	driver.get('https://studi-ol.com/user')
	tables = driver.find_element("xpath", '//*[@id="sb-site"]/div[3]/div/div[2]/div[1]/div[2]/div/div[2]')
	reservation_list = tables.find_elements(By.CLASS_NAME, 'text-left')
	for idx, table in enumerate(reservation_list):
		table_num = idx + 2

		# 利用日時を取得する
		studio_days = table.find_elements("xpath", "//*[@id='sb-site']/div[3]/div/div[2]/div[1]/div[2]/div/div[2]/div[{}]/p[2]".format(table_num))[0].text

		# 利用日時を日付変換し、現在時間との比較を行う
		if __judge_studio_days(studio_days):

			# display:noneとなっている要素があるため
			# 先にクリックしておく
			table_click = table.find_element("xpath", "//*[@id='contents']/table[{}]/tbody/tr[2]".format(table_num))
			table_click.click()
			
			# 0時のより後の場合のみ処理を行う
			# スタジオ名
			studio_name = table.find_elements("xpath", "//*[@id='contents']/table[{}]/tbody/tr[2]/td/div[1]/p[1]/span".format(table_num))[0].text
			# 開始時間:終了時間を取得
			date_end_time_str = table.find_elements("xpath", "//*[@id='contents']/table[{}]/tbody/tr[3]/td".format(table_num))[0].accessible_name
			# 開始時間/終了時間をリストに変換
			date_list = __change_date_element_to_string(date_end_time_str)
			# 予約番号を取得
			reservation_number = table.find_elements("xpath", "//*[@id='contents']/table[{}]/tbody/tr[5]/td".format(table_num))[0].text
			
			print(date_list)


def __judge_studio_days(studio_days:str) -> bool:

	res_value:bool = False
	pattern = r"利用日時：(\d{4}/\d{2}/\d{2}（[^）]+）\d{2}:\d{2})"

	date_match = re.search(pattern, studio_days)
	if date_match:
		datetime_str = date_match.group(1)
		# 日付部分と時刻部分を分離
		date_part, time_part = datetime_str.split('）')
		idx = date_part.find('（')
		date_part = date_part[:idx]
		date_time_str = f"{date_part} {time_part}"

		# 文字列をdatetimeオブジェクトに変換
		dt_format = "%Y/%m/%d %H:%M"
		datetime_obj = datetime.strptime(date_time_str, dt_format)

		# 今日の0時のdatetimeオブジェクトを作成
		today_midnight = datetime.combine(datetime.today(), datetime.min.time())

		# 日付が今日の0時より前かどうかを判定
		if datetime_obj > today_midnight:
			res_value = True
	
	return res_value

def __change_date_element_to_string(date_end_time_str:str) -> list:

	# 返却値
	res_datetime_list:list = []
	
	# 曜日を削除
	cleaned_text = re.sub(r'（.*?）', ' ', date_end_time_str)

	# 抽出
	dates_times = re.findall(r'\d{4}/\d{2}/\d{2} \d{2}:\d{2}', cleaned_text)

	# 抽出された日時をdatetimeオブジェクトに変換してリスト化
	# 日付オブジェクトと文字列型を格納
	if len(dates_times) != 0:
		for date in dates_times:
			obj:object = {
				'date_obj': datetime.strptime(date, '%Y/%m/%d %H:%M'),
				'date_string': date
			}
			res_datetime_list.append(obj)

	return res_datetime_list


## ボット起動コード
if __name__ == "__main__":
	## ローカルでテストする時のために、`debug=True` にしておく
	app.run(host="0.0.0.0", port=5000)
	# app.run()