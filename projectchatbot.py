import random
import logging
import mysql.connector
from mysql.connector import errorcode
import requests
import json
import os
import datetime
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
import openai
from datetime import datetime, timedelta

import threading

# local vars for GPT
user_conversations = {}
good_key = []

# config vars
TOKEN = (os.environ['ACCESS_TOKEN'])

config = {
    'user': os.environ['user'],
    'password': os.environ['pwd'],
    'host': os.environ['sqlhost'],
    'database': os.environ['db']
}


# Define the command names
START_CMD = "start"
RECOMMEND_CMD = "/recommend"
GET_CMD = "/get"


reply_keyboard = [
    [KeyboardButton(RECOMMEND_CMD)],
    [KeyboardButton(GET_CMD)]
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

# Define the inline keyboard options for movie recommendation
inline_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("收藏", callback_data="fav")],
    [InlineKeyboardButton("备选测试选项", callback_data="next")]
])

#  connect to sql
try:
    cnx = mysql.connector.connect(**config)
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
    else:
        print(err)
else:
    print("MySQL connection successful")
    cursor = cnx.cursor()

def update_user_info(user_id, user_nickname):
    now = datetime.datetime.now()
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    query = "INSERT INTO User_info_test_1 (user_id, user_nickname, user_last_active) " \
            "VALUES (%s, %s, %s) " \
            "ON DUPLICATE KEY UPDATE " \
            "user_nickname = VALUES(user_nickname), " \
            "user_last_active = VALUES(user_last_active)"
    values = (user_id, user_nickname, timestamp)
    cursor.execute(query, values)
    cnx.commit()

# 从接口拿到推荐电影的数据, 随机传入page参数, 返回带有海报url的电影
def get_upcoming_movies(page):
    url = "https://moviesdatabase.p.rapidapi.com/titles/x/upcoming"

    headers = {
        "X-RapidAPI-Key": "4274575d4fmsh03bcb3689951fd1p1f6d31jsn91881054f5d7",
        "X-RapidAPI-Host": "moviesdatabase.p.rapidapi.com"
    }

    response = requests.request("GET", url, headers=headers, params={'page': page})

    movies = json.loads(response.text)['results']

    reply = []

    for movie in movies:
        if movie['primaryImage']:
            tmp = {}
            tmp['id'] = movie['id']
            tmp['poster_url'] = movie['primaryImage']['url']
            tmp['title'] = movie['titleText']['text']
            reply.append(tmp)

    return reply

# 用movie_id去查电影信息
def get_movie_details(movie_id):
    url = "https://moviesdatabase.p.rapidapi.com/titles/x/titles-by-ids"

    querystring = {"idsList": movie_id}

    headers = {
        "X-RapidAPI-Key": "4274575d4fmsh03bcb3689951fd1p1f6d31jsn91881054f5d7",
        "X-RapidAPI-Host": "moviesdatabase.p.rapidapi.com"
    }

    response = requests.request("GET", url, headers=headers, params=querystring)

    movie = json.loads(response.text)['results'][0]

    tmp = {}
    tmp['id'] = movie['id']
    tmp['title'] = movie['titleText']['text']
    tmp['poster_url'] = movie['primaryImage']['url']

    return tmp

def start(update, context):
    user_id = update.message.from_user.id
    user_nickname = update.message.from_user.username
    update_user_info(user_id, user_nickname)
    message = "欢迎使用电影推荐机器人！\n" \
              "您可以使用以下命令：\n" \
              "/recommend - 随机推荐一部即将上映的电影\n /get - 随机获取一部您收藏的电影\n"
    context.bot.send_message(chat_id=user_id, text=message, reply_markup=markup)

# movies = [
#     {"id": 123, "title": "title", "director": "director", "cast": "cast", "duration": "duration", "poster_url": "https://maimaidx-eng.com/maimai-mobile/img/chara_01.png"},
#     {"id": 456, "title": "title2", "director": "director2", "cast": "cast2", "duration": "duration2",
#      "poster_url": "https://maimaidx-eng.com/maimai-mobile/img/btn_page_top.png"},
# ]

def recommend(update, context):
    message = "以下是即将上映的电影：\n\n"
    movies = get_upcoming_movies(random.choice([1, 2, 3, 4]))
    # index = context.user_data['last_viewed']
    print(movies)
    movie = random.choice(movies)

    # print(movie)
    movie_id = movie["id"]
    movie_title = movie["title"]
    movie_poster_url = movie["poster_url"]

    message += "<b>" + movie_title + "</b>\n"

    context.user_data[movie_id] = {
        "title": movie_title,
        "poster_url": movie_poster_url
    }
    context.user_data['recommended'] = movie_id

    context.bot.send_photo(chat_id=update.effective_chat.id, photo=movie_poster_url, caption=message, parse_mode="HTML", reply_markup=inline_keyboard)

# 用户点击按钮的回调函数
def button_callback(update, context):

    # get query params
    query = update.callback_query
    user_id = query.from_user.id
    message_id = query.message.message_id
    query_data = query.data

    if query_data == "fav":
        # print(context)
        movie_id = context.user_data['recommended']
        #
        # print(movie_id)
        sql_query = "INSERT INTO User_favorite_test_1 (user_id, movie_id) " \
                "VALUES (%s, %s) " \
                "ON DUPLICATE KEY UPDATE user_id = user_id"
        values = (user_id, movie_id)
        cursor.execute(sql_query, values)
        cnx.commit()

        context.bot.answer_callback_query(
            query.id,
            text="电影已收藏！")
    # else:
    #     context.bot.answer_callback_query(
    #         query.id,
    #         text='备选按钮'
    #     )

# 从用户收藏的电影中随机返回一个
def get(update, context):
    user_id = update.effective_user.id
    query = "SELECT movie_id FROM User_favorite_test_1 WHERE user_id = %s ORDER BY RAND() LIMIT 3"
    values = (user_id,)
    cursor.execute(query, values)
    result = cursor.fetchall()
    if not result:
        context.bot.send_message(chat_id=user_id, text="您还没有收藏任何电影！")
    else:
        message = "以下是您的推荐电影：\n\n"
        row = random.choice(result)
        movie_id = row[0]
        movie = get_movie_details(movie_id)
        if movie:
            movie_title = movie["title"]
            movie_poster_url = movie["poster_url"]
            message += "<b>" + movie_title + "</b>\n"
            context.user_data["current_movie"] = movie_id
        context.bot.send_photo(chat_id=user_id, photo=movie_poster_url, caption=message, parse_mode="HTML"
                               # , reply_markup=inline_keyboard
                               )

# GPT
def ask(update: Update, msg: CallbackContext) -> None:
    if len(msg.args) < 1:
        update.message.reply_text("你好像没有输入问题内容捏, 示例: /ask 能不能给我喵一个？")
        return
    query = ''
    for ele in msg.args:
        query += ele

    user_id = update.effective_chat.id
    user_message = query
    logging.info("user Id: " + str(user_id) + " User Ask: " + user_message)

    initial_prompt = """
        Now you are a assistant.
    """
    global user_conversations

    if user_id not in user_conversations:
        user_conversations[user_id] = {
            'history': [{"role": "system", "content": initial_prompt},
                        ],
            'expiration': datetime.now() + timedelta(minutes=10)
        }

    if user_id in user_conversations and datetime.now() > user_conversations[user_id]['expiration']:
        del user_conversations[user_id]
        user_conversations[user_id] = {
            'history': [{"role": "system", "content": initial_prompt},
                        ],
            'expiration': datetime.now() + timedelta(minutes=10)
        }

    # If the conversation history is still valid, send the user's message to the API
    user_conversations[user_id]['history'].append({'role': 'user', 'content': user_message})

    # url = "https://chatgpt-api.shn.hk/v1/"
    # headers = {"Content-Type": "application/json", "User-Agent": "PostmanRuntime/7.31.3"}
    # data = {"model": "gpt-3.5-turbo", "messages": user_conversations[user_id]['history']}
    if len(good_key) < 1:
        update.message.reply_text('Oops! we encountered a problem with GPT key, maybe try me later.')
    openai.api_key = good_key[0]
    # openAi python sdk
    result = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=user_conversations[user_id]['history']
    )

    reply = result['choices'][0]['message']['content']
    user_conversations[user_id]['history'].append({'role': 'assistant', 'content': reply})
    logging.info("GPT: " + reply)
    update.message.reply_text(reply)

def find_a_working_key():
    global good_key
    url = "https://freeopenai.xyz/api.txt"
    response = requests.get(url)
    lines = response.text.split("\n")

    for key in lines:
        openai.api_key = key[:-1]
        try:
            # Use the key to make a test request to the API
            response = openai.Completion.create(
                engine="text-davinci-002",
                prompt="Hello, World!",
                max_tokens=5,
                n=1,
                stop=None,
                temperature=0.5,
                timeout=5,
                frequency_penalty=0,
                presence_penalty=0
            )
            good_key.append(key[:-1])
            logging.info('find a good key! ' + key[:-1])
        except Exception as e:
            continue

# 重置历史对话
def reset(update: Update, msg: CallbackContext):
    global user_conversations
    user_id = update.effective_chat.id
    reply = ""
    if user_id in user_conversations:
        del user_conversations[user_id]
        reply = "已经重置了历史对话, 开启新一轮对话吧!"
    else:
        reply = "似乎没有历史对话捏, 无需重置"

    update.message.reply_text(reply)


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("recommend", recommend))
    dispatcher.add_handler(CommandHandler("get", get))

    # add up functions
    dispatcher.add_handler(CommandHandler('ask', ask))
    dispatcher.add_handler(CommandHandler('reset', reset))

    # initialize key
    # start new thread to filter key list every hour
    find_a_working_key()
    t = threading.Timer(3600.0, find_a_working_key)
    t.start()

    dispatcher.add_handler(CallbackQueryHandler(button_callback))

    # Start the bot
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()