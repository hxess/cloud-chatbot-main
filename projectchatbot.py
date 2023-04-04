import random

import mysql.connector
from mysql.connector import errorcode
import requests
import json
import time
import os
import datetime
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

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
    # movie_director = movie["director"]
    # movie_cast = movie["cast"]
    # movie_duration = movie["duration"]
    movie_poster_url = movie["poster_url"]

    message += "<b>" + movie_title + "</b>\n"

    context.user_data[movie_id] = {
        "title": movie_title,
        "poster_url": movie_poster_url
    }
    context.user_data['recommended'] = movie_id

    # context.user_data['last_viewed'] =

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
    #
    # elif query_data == "next":
    #     movies = context.user_data["last_recommendation_movies"]
    #     current_index = movies.index(context.user_data["current_movie"])
    #     if current_index == len(movies) - 1:
    #         context.bot.answer_callback_query(query.id, text="已经到达最后一部电影！")
    #     else:
    #         movie = movies[current_index + 1]
    #         movie_id = movie["id"]
    #         movie_title = movie["title"]
    #         movie_director = movie["director"]
    #         movie_cast = movie["cast"]
    #         movie_duration = movie["duration"]
    #         movie_poster_url = movie["poster_url"]
    #         message = "<b>" + movie_title + "</b>\n" \
    #                   "导演：" + movie_director + "\n" \
    #                   "演员：" + movie_cast + "\n" \
    #                   "时长：" + str(movie_duration) + "分钟\n"
    #         context.user_data[movie_id] = {
    #             "title": movie_title,
    #             "director": movie_director,
    #             "cast": movie_cast,
    #             "duration": movie_duration,
    #             "poster_url": movie_poster_url
    #         }
    #         context.user_data["current_movie"] = movie_id
    #         context.bot.edit_message_media(chat_id=user_id, message_id=message_id, media=InputMediaPhoto(media=movie_poster_url, caption=message, parse_mode="HTML"), reply_markup=inline_keyboard)
    #         context.bot.answer_callback_query(query.id)
    else:
        context.bot.answer_callback_query(
            query.id,
            text='备选按钮'
        )

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


def main():
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("recommend", recommend))
    dispatcher.add_handler(CommandHandler("get", get))

    dispatcher.add_handler(CallbackQueryHandler(button_callback))

    # Start the bot
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
