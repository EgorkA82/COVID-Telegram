import datetime
import socket
import sqlite3
import requests

import telebot
from telebot import types

from config import *
from functions import *


bot = telebot.TeleBot(TOKEN)
bot.send_message(DEBUGGER_TELEGRAM_ID,
                 "\n".join(
                     [
                        "Bot launched: " + socket.gethostbyname(socket.gethostname()),
                        'UTC: ' + bold(datetime.datetime.utcnow().strftime("%H:%M %d.%m.%Y")),
                        'Local: ' + bold(datetime.datetime.now().strftime("%H:%M %d.%m.%Y"))
                     ]
                 ), parse_mode='Markdown', disable_notification=True
                )


def start(message): # add/update user data | sending message to cmd
    with sqlite3.connect('db.sqlite') as db:
        db_cursor = db.cursor()
        if db_cursor.execute('SELECT id FROM user_data WHERE id=?', (message.from_user.id,)).fetchone() == None:
            db_cursor.execute('INSERT INTO user_data(id) VALUES(?)', (str(message.from_user.id),))
        try:
            db_cursor.execute('UPDATE user_data SET first_name = ?, last_name = ? WHERE id=?', (str(message.from_user.first_name), str(message.from_user.last_name), str(message.from_user.id)))
            db.commit()
        except: pass
        
        db_cursor.execute('UPDATE user_data SET username = ? WHERE id=?', 
                            (str(message.from_user.username), str(message.from_user.id))
                            )
        db.commit()
        
        db.commit()
        db_cursor.close()
    print('Recieved message from:', str(message.from_user.first_name), str(message.from_user.last_name))
    print("User URL:", "https://t.me/" + str(message.from_user.username))    
    print("Date:", datetime.datetime.now().strftime("%H:%M %d.%m.%Y")) ## HH:MM DD.MM.YYYY
    print('Message text:', message.text)
    print()

@bot.message_handler(commands=command_list_keywords('help'))
def help(message):
    start(message)
    if get_user_language(message) == "en": 
        text = "\n".join(["/" + key + " - " + val for key, val in eng_text_commands.items()])
    else: 
        text = "\n".join(["/" + key + " - " + rus_text[eng_text_commands[key]] for key in eng_text_commands.keys()])
    bot.send_message(str(message.from_user.id), text, parse_mode="HTML")

@bot.message_handler(commands=command_list_keywords('set_language'))
def change_language(message):
    start(message)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text=translate(message, "Russian🇷🇺"), callback_data="ru"),
                 types.InlineKeyboardButton(text=translate(message, "English🇺🇸"), callback_data="en"))
    bot.send_message(str(message.from_user.id), translate(message, "Which language you want to use?"), reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "ru" or call.data == "en")
def set_language(message):
    bot.answer_callback_query(message.id)
    with sqlite3.connect('db.sqlite') as db:
        db_cursor = db.cursor()
        try:
            db_cursor.execute('UPDATE user_data SET language=? WHERE id=?', (message.data, str(message.from_user.id)))
            db.commit()
            bot.send_message(str(message.from_user.id), translate(message, "Success! /profile"))
        except:
            bot.send_message(str(message.from_user.id), translate(message, "Failure( /help"))

@bot.message_handler(commands=command_list_keywords('profile'))
def profile(message):
    start(message)
    text = [translate(message, "Account ID") + ": " + bold(str(message.from_user.id))]
    if message.from_user.first_name != None:
        text.append(translate(message, "First name") + ": " + bold(str(message.from_user.first_name)))
    else: text.append(translate(message, "First name") + ": " + bold(translate(message, "No information")))
    if message.from_user.username != None:
        text.append(translate(message, "Username") + ": " + bold(str(message.from_user.username)))
    else: text.append(translate(message, "Username") + ": " + bold(translate(message, "No information")))
    if message.from_user.last_name != None:
        text.append(translate(message, "Last name") + ": " + bold(str(message.from_user.last_name)))
    else: text.append(translate(message, "Last name") + ": " + bold(translate(message, "No information")))
    if get_user_language(message) == "ru":
        text.append(translate(message, "Language") + ": " + bold(translate(message, "Russian🇷🇺")))
    else:
        text.append(translate(message, "Language") + ": " + bold(translate(message, "English🇺🇸")))
    with sqlite3.connect('db.sqlite') as db:
        db_cursor = db.cursor()
        last_query = db_cursor.execute('SELECT last_query FROM user_data WHERE id=?', (message.from_user.id,)).fetchone()[0]
    if last_query != None:
        text.append(translate(message, "Last query") + ": " + bold(last_query))
    else:
        text.append(translate(message, "Last query") + ": " + bold(translate(message, "No information")))
    bot.send_message(message.from_user.id, "\n".join(text), parse_mode="Markdown")

@bot.message_handler(commands=command_list_keywords('covid'))
def covid(message):
    start(message)
    if get_last_query(message) == None:
        bot.send_message(message.from_user.id, translate(message, 'Write long english name of country you want to check'))
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton(text=country_name[get_last_query(message)], callback_data=get_last_query(message)))
        bot.send_message(message.from_user.id, translate(message, "Write long english name of country you want to check"), reply_markup=keyboard)
    bot.register_next_step_handler(message, get_covid_data)

@bot.callback_query_handler(func=lambda call: call.data.upper() in country_code.values())
def get_covid_data_sys(message):
    data = requests.request("GET", "https://covid19-api.org/api/diff/" + message.data.upper()).json()
    bot.answer_callback_query(message.id)
    if "error" in data.keys():
        bot.send_message(message.from_user.id, translate(message, "Incorrect name"))
        bot.register_next_step_handler(message, get_covid_data)
    else:
        covid_show(message, data)

@bot.message_handler(func=lambda message: not_command(message))
def get_covid_data(message):
    if str(message.text).replace("/", "") in command_list_keywords('covid'):
        covid(message)
        pass
    start(message)
    if str(message.text)[0] != "/":
        if str(message.text).lower() not in country_code_titles_short.keys():
            bot.send_message(message.from_user.id, translate(message, "Incorrect name"))
            bot.register_next_step_handler(message, get_covid_data)
        else:
            data = requests.request("GET", "https://covid19-api.org/api/diff/" + country_code_titles_short[message.text.lower()]).json()
            
            if "error" in list(data.keys()):
                bot.send_message(message.from_user.id, translate(message, "Incorrect name"))
                bot.register_next_step_handler(message, get_covid_data)
            else:
                covid_show(message, data)

def covid_show(message, data):
    text = "\n".join([
        translate(message, "Country") + ": " + bold(country_name[data["country"]]),
        translate(message, "Last update") + ": " + bold(data["last_update"]),
        translate(message, "New cases") + ": " + bold(data["new_cases"]),
        translate(message, "Recovered") + ": " + bold(data["new_recovered"]),
        translate(message, "Deaths") + ": " + bold(data["new_deaths"])
    ])
    keyboard = types.InlineKeyboardMarkup()
    update = types.InlineKeyboardButton(text=translate(message, "Update🔁"), callback_data="update/"+data["country"])
    keyboard.add(update)
    more_info = types.InlineKeyboardButton(text=translate(message, "More information"), url="https://coronavirus-monitor.ru/")
    keyboard.add(more_info)
    bot.send_message(message.from_user.id, text=text, reply_markup=keyboard, parse_mode="Markdown")
    with sqlite3.connect('db.sqlite') as db:
        db_cursor = db.cursor()
        db_cursor.execute('UPDATE user_data SET last_query=? WHERE id=?', (data["country"], message.from_user.id))

@bot.callback_query_handler(func=lambda message: str(message.data).startswith("update"))
def update_covid_show(callback):
    data = requests.request("GET", "https://covid19-api.org/api/diff/" + str(callback.data).split("/")[-1]).json()
    if "error" not in list(data.keys()):
        keyboard = types.InlineKeyboardMarkup()
        update = types.InlineKeyboardButton(text=translate(callback, "Update🔁"), callback_data="update/"+data["country"])
        keyboard.add(update)
        more_info = types.InlineKeyboardButton(text=translate(callback, "More information"), url="https://coronavirus-monitor.ru/")
        keyboard.add(more_info)
        try:
            bot.edit_message_text(text = "\n".join([
                    translate(callback, "Country") + ": " + bold(country_name[data["country"]]),
                    translate(callback, "Last update") + ": " + bold(data["last_update"]),
                    translate(callback, "New cases") + ": " + bold(data["new_cases"]),
                    translate(callback, "Recovered") + ": " + bold(data["new_recovered"]),
                    translate(callback, "Deaths") + ": " + bold(data["new_deaths"])
                    ]
                ), message_id=callback.message.message_id, parse_mode="Markdown", chat_id=callback.message.chat.id, reply_markup=keyboard)
        except: pass
    bot.answer_callback_query(callback.id)

bot.polling() # LongPoll activating
