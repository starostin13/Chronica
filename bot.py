#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fileencoding=utf-8
import os
import requests
import telebot
import credentials
from yaHelper import getPhoto
from stringHelper import numberToMonthNameRu
import shutil

bot_token = credentials.bot_token

bot = telebot.TeleBot(bot_token)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    photo = getPhoto()
    
    try:
        print("Sending " + photo.file)
        photo_path_splited = photo.path.split("/")
        if photo.photoslice_time is None:
            comment = "Это " + photo_path_splited[len(photo_path_splited) - 2]
        else:
            comment = "Это %s. Дело было в %s %s года" % (photo_path_splited[len(photo_path_splited) - 2], numberToMonthNameRu(photo.photoslice_time.month), photo.photoslice_time.year)
        
        if photo.media_type == "image":
            bot.send_photo(credentials.chat_id, photo.file, caption = comment)
        if photo.media_type == "video":
            if "gp3" in photo.name or "mp4" in photo.name:
                bot.send_animation(credentials.chat_id, photo.file, caption = comment)
            else:
                bot.send_video(credentials.chat_id, photo.file, caption = comment)
        
    except Exception as exc:
        bot.send_message(credentials.chat_id, f"Unexpected {exc=}")

@bot.message_handler(content_types=['image', 'photo'])
def echo_all(message):
    print("Saving photo " + message.caption + " locally")
    file = bot.get_file_url(message.photo[-1].file_id)
    dst = '/temp/'
    
    # writing to a custom file
    with requests.get(file, stream=True) as r:
        with open(dst + message.caption + ".jpg", 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    bot.reply_to(message, "Мне это сохранить что ли?")    
    
    #shutil.copy(src, dst)
    for entry in os.listdir(dst):
        if os.path.isfile(os.path.join(dst, entry)):
            print(entry)
    

@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    print(message.text)
    if "да" == message.text:
        bot.reply_to(message, "хуй на")
        
    if "300" == message.text:
        bot.reply_to(message, "Отсоси у тракториста")
        
    #bot.reply_to(message, message.text)

@bot.message_handler(commands=['test'])
def echo_test(message):
    print("TEST: " + message.text)
    #bot.send_animation()

bot.infinity_polling()