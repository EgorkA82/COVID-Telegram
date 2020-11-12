import sqlite3
import requests
from config import *

def command_list_keywords(command_name):
    from config import command_list
    return command_list[command_name]

def bold(text):
    return "*" + str(text) + "*"

def get_user_language(message):
    with sqlite3.connect('db.sqlite') as db:
        db_cursor = db.cursor()
        return db_cursor.execute('SELECT language FROM user_data WHERE id=?', (message.from_user.id,)).fetchone()[0]
    
def get_last_query(message):
    with sqlite3.connect('db.sqlite') as db:
        db_cursor = db.cursor()
        return db_cursor.execute('SELECT last_query FROM user_data WHERE id=?', (message.from_user.id,)).fetchone()[0]

def translate(message, text):
    if get_user_language(message) == "ru":
        return rus_text[text]
    return text

def get_covid_data(message):
    from bot import bot, covid_show
    if message.text not in country_code.keys():
        bot.send_message(message.from_user.id, translate(message, "Incorrect name"))
        bot.register_next_step_handler(message, get_covid_data(message))
    else:
        data = requests.request("GET", "https://covid19-api.org/api/diff/" + country_code(message.text)).json()
        covid_show(message, data)

def not_command(message):
    for name in command_list.keys():
        for command in command_list[name]:
            if message.text == command:
                return False
    return True
