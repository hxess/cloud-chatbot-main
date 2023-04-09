import random, requests, openai, threading, logging, os, re, datetime, signal
import mysql.connector

from mysql.connector import errorcode
from datetime import timedelta, datetime
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


## sql connector
config = {
    'user': os.environ['user'],
    'password': os.environ['pwd'],
    'host': os.environ['sqlhost'],
    'database': os.environ['db']
}
global cnx, cursor

class TimeoutException(Exception):
    pass

def timer(timeout_event, timeout):
    timeout_event.wait(timeout)
    if not timeout_event.is_set():
        timeout_event.set()
        raise TimeoutException('Execution timed out')

def mysql_connection():
    global cnx, cursor
    try:
        cnx = mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            logging.info("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            logging.info("Database does not exist")
        else:
            logging.info(err)
    else:
        logging.info("MySQL connection successful")
        cursor = cnx.cursor(buffered=True)

def pingsql():
    timeout_event = threading.Event()
    timeout_thread = threading.Thread(target=timer, args=(timeout_event, 3))
    try:
        timeout_thread.start()
        cursor.execute("SELECT * from User_info_test_1 where 1;")
        timeout_event.set()
        logging.info('good connection')
    except:
        mysql_connection()
        logging.info('reconnected')
    finally:
        timeout_thread.join()
        if timeout_event.is_set():
            logging.info('Execution completed within timeout')

# handle functions
def error(update, context):
    logging.warning('Update "%s" caused error "%s"', update, context.error)

def start(update, context):
    user_id = update.message.from_user.id
    user_nickname = update.message.from_user.username
    sql_update_user_info(user_id, user_nickname)

    reply_keyboard = [
        [KeyboardButton('/start')],
        [KeyboardButton('/genres')],
        [KeyboardButton('/get')],
        [KeyboardButton('/ask')],
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    message = "Welcome to the movie recommendation chatbot.！\n" \
              "You can use the following commands：\n" \
              "/genres - display the genres entrance\n " \
              "/get - Randomly pick one of your favorite movies.\n" \
              "/ask - ask GPT assistant to help you to pick a movie from your favorites."

    context.bot.send_message(chat_id=user_id, text=message, reply_markup=markup)

## movie functions
# function to handle /start command
def genres(update, context):
    keyboard = [[InlineKeyboardButton("Action",
                                      # callback_data=str({"with": "action", "without": "Comedy|Drama|Horror"})
                                      callback_data='action'
                                      ),
                 InlineKeyboardButton("Comedy",
                                      # callback_data=str({"with": "Comedy", "without": "Action|Drama|Horror"})
                                      callback_data='comedy'
                                      )],
                [InlineKeyboardButton("Drama",
                                      # callback_data=str({"with": "Drama", "without": "Comedy|Action|Horror"})
                                      callback_data='drama'
                                      ),
                 InlineKeyboardButton("Horror",
                                      # callback_data=str({"with": "Horror", "without": "Comedy|Drama|Action"})
                                      callback_data='horror'
                                      )]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose a genre:', reply_markup=reply_markup)

# function to handle button click
def button(update, context):
    query = update.callback_query

    # genre = json.loads(query.data)['with']
    genre = query.data
    # without = json.loads(query.data)['without']
    without = ['action', 'drama', 'horror', 'comedy']
    without_genres = ''
    for ele in without:
        if ele == genre:
            continue
        else:
            without_genres += ele


    page = random.choice([i for i in range(1, 51)])

    response = requests.get(f'https://api.themoviedb.org/3/discover/movie?api_key=bfa1c4b7acab32a4eb75aa244f15754f&with_genres={genre}&page={page}&without_genres={without_genres}')

    movies = response.json()['results']

    buttons = [InlineKeyboardButton(movie['title'], callback_data=movie['id']) for movie in movies]

    # reply_markup = InlineKeyboardMarkup([buttons])
    reply_markup = InlineKeyboardMarkup([[button] for button in buttons])

    query.message.reply_text('Please choose a movie:', reply_markup=reply_markup)

# function to handle movie button click
def movie_button(update, context):
    query = update.callback_query
    movie_id = query.data
    logging.info("movie_query: ")
    try:
        response = requests.get(f'https://api.themoviedb.org/3/movie/{movie_id}?api_key=bfa1c4b7acab32a4eb75aa244f15754f&append_to_response=credits')

        title = response.json()['title']
        duration = response.json()['runtime']
        director = response.json()['credits']['crew'][0]['name']
        cast = [actor['name'] for actor in response.json()['credits']['cast']]
        poster_url = f"https://image.tmdb.org/t/p/w500{response.json()['poster_path']}"

        message = f"<b>Title:</b> {title}\n<b>Duration:</b> {duration}\n<b>Director:</b> {director}\n<b>Cast:</b> {', '.join(cast[:10])}"


        keyboard = [
                    # [InlineKeyboardButton(director, callback_data=f'director_{director}')],
                    [InlineKeyboardButton("Add to favorite", callback_data=f'fav_{movie_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # send message with movie poster
        query.message.reply_photo(photo=poster_url, caption=message, parse_mode="HTML", reply_markup=reply_markup)
        logging.info("movie replied")
    except Exception as e:
        query.message.reply_text("This movie was not supported by TMDB API")

def director_query(update, context):
    query = update.callback_query
    director = query.data.split('_')[1]

    response = requests.get(f'https://api.themoviedb.org/3/search/person?api_key=bfa1c4b7acab32a4eb75aa244f15754f&query={director}')

    director_id = response.json()['results'][0]['id']
    name = response.json()['results'][0]['name']
    bio = response.json()['results'][0]['biography']
    profile_url = f"https://image.tmdb.org/t/p/w500{response.json()['results'][0]['profile_path']}"

    # send message with director details
    message = f"<b>Name:</b> {name}\n<b>Biography:</b> {bio}"

    keyboard = [[InlineKeyboardButton("Top 3 Movies", callback_data=f'top_movies_{director_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # send message with director profile picture
    query.message.reply_photo(photo=profile_url, caption=message, parse_mode="HTML", reply_markup=reply_markup)


## User profile management
def sql_update_user_info(user_id, user_nickname):
    pingsql()
    now = datetime.now()
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    query = "INSERT INTO User_info_test_1 (user_id, user_nickname, user_last_active) " \
            "VALUES (%s, %s, %s) " \
            "ON DUPLICATE KEY UPDATE " \
            "user_nickname = VALUES(user_nickname), " \
            "user_last_active = VALUES(user_last_active)"
    values = (user_id, user_nickname, timestamp)
    cursor.execute(query, values)
    cnx.commit()

def sql_add_user_fav(user_id, movie_id):
    sql_query = "INSERT INTO User_favorite_test_1 (user_id, movie_id) " \
                "VALUES (%s, %s) " \
                "ON DUPLICATE KEY UPDATE user_id = user_id"
    values = (user_id, movie_id)
    pingsql()
    cursor.execute(sql_query, values)
    cnx.commit()

def sql_get_user_fav(user_id):
    pingsql()
    query = "SELECT movie_id FROM User_favorite_test_1 WHERE user_id = %s ORDER BY RAND() LIMIT 3"
    values = (user_id,)
    pingsql()
    cursor.execute(query, values)
    result = cursor.fetchall()
    return result

def add_to_fav(update, context):
    query = update.callback_query
    movie_id = query.data.split('_')[1]
    logging.info(movie_id)

    sql_add_user_fav(update.effective_user.id, movie_id)
    query.message.reply_text("added to favorite successfully")

def get_from_fav(update, context):
    query = update.callback_query
    logging.info("get_from_fav" )
    results = sql_get_user_fav(update.effective_user.id)

    if not results:
        context.bot.send_message(chat_id=update.effective_user.id, text="You haven't favorite any movies yet.")

    else:
        try:
            result = random.choice(results)[0]
            print("bingo" + str(result))

            # get movie details from API based on selected movie id
            response = requests.get(
                f'https://api.themoviedb.org/3/movie/{result}?api_key=bfa1c4b7acab32a4eb75aa244f15754f&append_to_response=credits')

            title = response.json()['title']
            duration = response.json()['runtime']
            director = response.json()['credits']['crew'][0]['name']
            cast = [actor['name'] for actor in response.json()['credits']['cast']]
            poster_url = f"https://image.tmdb.org/t/p/w500{response.json()['poster_path']}"

            message = f"<b>Title:</b> {title}\n<b>Duration:</b> {duration}\n<b>Director:</b> {director}\n<b>Cast:</b> {', '.join(cast)}"
            context.bot.send_photo(chat_id=update.effective_user.id, photo=poster_url, caption=message, parse_mode="HTML")
        except Exception as e:
            context.bot.send_message(chat_id=update.effective_user.id, test="We got unexpected problem")

## GPT features
# local vars for GPT
user_conversations = {}
good_key = []

def find_a_working_key():
    global good_key
    url = "https://freeopenai.xyz/api.txt"
    response = requests.get(url)
    lines = response.text.split("\r\n")

    for key in lines:
        openai.api_key = key
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
            good_key.append(key)
            logging.info('find a good key! ' + key)
        except Exception as e:
            continue

    logging.info('done finding keys')

def ask_neko_of_movies(update, context):
    query = update.callback_query
    logging.info("ask_neko_of_movies")

    context.bot.send_message(chat_id=update.effective_user.id, text="Working hard to select a movie for you, please wait...")

    results = sql_get_user_fav(update.effective_user.id)

    ids = []
    text = []

    if not results:
        context.bot.send_message(chat_id=update.effective_user.id, text="You haven't favorited any movies yet！")

    else:
        # context.bot.send_photo(chat_id=update.effective_user.id, photo=poster_url, caption=message, parse_mode="HTML")
        for ele in results:
            ids.append(ele[0])

        for id in ids:
            # get movie details from API based on selected movie id
            response = requests.get(
                f'https://api.themoviedb.org/3/movie/{id}?api_key=bfa1c4b7acab32a4eb75aa244f15754f&append_to_response=credits')
            title = response.json()['title']
            duration = response.json()['runtime']
            overview = response.json()['overview']
            director = response.json()['credits']['crew'][0]['name']
            cast = [actor['name'] for actor in response.json()['credits']['cast']]
            poster_url = f"https://image.tmdb.org/t/p/w500{response.json()['poster_path']}"

            message = f"<b>Title:</b> {title}\n<b>Director:</b> {director}\n<b>Cast:</b> Overview:</b> {overview} "
            text.append(message)

        if len(text) > 10:
            text = random.sample(text, 5)

        prompt = "Please select a movie form the next information I provided, you need to look into the duration and overview of them\n "
        for ele in text:
            prompt += ele

        user_id = update.effective_chat.id

        initial_prompt = """
                Now you are a assistant.
            """

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

        user_conversations[user_id]['history'].append({'role': 'user', 'content': prompt})

        # if len(good_key) < 1:
        #     context.bot.send_message(chat_id=update.effective_user.id, text='Oops! we encountered a problem with GPT key, maybe try me later.')


        try:
            openai.api_key = good_key[-1]
            # openAi python sdk
            result = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=user_conversations[user_id]['history']
            )
            reply = result['choices'][0]['message']['content']
            user_conversations[user_id]['history'].append({'role': 'assistant', 'content': reply})
            logging.info("GPT: " + reply)
            # update.message.reply_text(reply)
            context.bot.send_message(text=reply, chat_id=update.effective_user.id)
            logging.info("ask_neko_of_movies replied: " + reply)
        except Exception as e:
            context.bot.send_message(text="Oops! we got a problem with GPT Api", chat_id=update.effective_user.id)
            logging.info("ask_neko_of_movies replied: Oops! we got a problem with GPT Api")


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    updater = Updater(token=os.environ['ACCESS_TOKEN'], use_context=True)
    # get dispatcher to register handlers
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('genres', genres))
    dp.add_handler(CommandHandler('get', get_from_fav))
    dp.add_handler(CommandHandler('ask', ask_neko_of_movies))
    dp.add_handler(CallbackQueryHandler(button, pattern=re.compile(r'^(action|comedy|drama|horror)$')))
    # dp.add_handler(CallbackQueryHandler(director_query, pattern=re.compile(r'^director_(.+)$')))
    dp.add_handler(CallbackQueryHandler(add_to_fav, pattern=re.compile(r'^fav_(\d+)$')))
    dp.add_handler(
        CallbackQueryHandler(movie_button, pattern=re.compile(r'^(?!action|comedy|drama|horror|fav_\d+$).*')))

    # log all errors
    # dp.add_error_handler(error)

    # start finding key
    find_a_working_key()
    t = threading.Timer(1200, find_a_working_key)
    t.start()

    # # sql
    # s = threading.Timer(600, pingsql)
    # s.start()

    mysql_connection()

    # start the bot
    updater.start_polling()

    # run the bot until Ctrl-C is pressed
    updater.idle()


if __name__ == '__main__':
    main()
