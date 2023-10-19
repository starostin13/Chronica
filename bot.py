#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fileencoding=utf-8
import telebot
import credentials
from yaHelper import getPhoto
from stringHelper import numberToMonthNameRu

bot_token = credentials.bot_token

bot = telebot.TeleBot(bot_token)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    print(message)
    photo = getPhoto()
    
    try:
        print("Sending " + photo.name)
        photo_path_splited = photo.path.split("/")
        if photo.photoslice_time is None:
            comment = "Это " + photo_path_splited[len(photo_path_splited) - 2]
        else:
            comment = "Это %s. Дело было в %s %s года" % (photo_path_splited[len(photo_path_splited) - 2], numberToMonthNameRu(photo.photoslice_time.month), photo.photoslice_time.year)
        bot.send_photo(credentials.chat_id, photo.file, caption = comment)
        
    except Exception as exc:
        bot.send_message(credentials.chat_id, f"Unexpected {exc=}")
    
#@bot.message_handler(func=lambda msg: True)
#def echo_all(message):
#    print(message)
#    bot.reply_to(message, message.text)
#    bot.send_message(credentials.chat_id, 'Where is Bluntman?')
    
bot.infinity_polling()