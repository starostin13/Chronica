#!/usr/bin/python3.11
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fileencoding=utf-8
from datetime import datetime, timedelta
import os
from random import randrange
import sched
import time
from threading import Thread
import requests
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import credentials
from yaHelper import createFolder, downloadFile, getLastUpdatedFolder, getPhoto, saveFileTo
from stringHelper import numberToMonthNameRu
import shutil

bot_token = credentials.bot_tokenq
bot = telebot.TeleBot(bot_token)
dst = '/temp/'
schedule = sched.scheduler(time.time, time.sleep)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    print("Answer from inline is " + call.data)
    if call.data == "new":
        newFolderName = createFolder()
    for entry in os.listdir(dst):
        if os.path.isfile(os.path.join(dst, entry)):
            if call.data == "new":
                saveFileTo(os.path.join(dst, entry), newFolderName + "/" + entry)
            elif call.data != "decline":
                saveFileTo(os.path.join(dst, entry), call.data + "/" + entry)
            os.remove(os.path.join(dst, entry))


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
                downloadFile(photo.file, photo.name)
                bot.send_video(credentials.chat_id, open(dst + photo.name, 'rb'), caption = comment)
                os.remove(dst + photo.name)
            else:
                bot.send_video(credentials.chat_id, photo.file, caption = comment)

    except Exception as exc:
        bot.send_message(credentials.chat_id, "Try to send from " + photo_path_splited[len(photo_path_splited) - 2] + " .Unexpected " + exc.description)


@bot.message_handler(content_types=['video'])
def echo_video(message):
    try:
        file = bot.get_file_url(message.video.file_id)
        recievingFile(file, message)
        
    except Exception as exc:
        bot.reply_to(message, "Не вышло: " + exc.description)

@bot.message_handler(content_types=['image', 'photo'])
def echo_photo(message):
    try:
        file = bot.get_file_url(message.photo[-1].file_id)
        recievingFile(file, message)

    except Exception as exc:
        bot.reply_to(message, "Не вышло: " + exc.description)

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


def main_loop():
    scheduledThread = Thread(target=schedule_random_photo)
    scheduledThread.start()
    
    bot.infinity_polling()


def recievingFile(file, message):    
    uploadedFileName = message.caption if message.caption != None else file.split('/')[-1]
    
    print("Saving file " + uploadedFileName + " locally")
        # writing to a custom file
    with requests.get(file, stream=True) as r:
        with open(dst + uploadedFileName, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
            
    bot.reply_to(message, "Мне это сохранить что ли?")

    lastUpdatedFolder = getLastUpdatedFolder()

    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton(lastUpdatedFolder, callback_data=lastUpdatedFolder),
                                InlineKeyboardButton("Не нада", callback_data="decline"),
                                InlineKeyboardButton("Новое", callback_data="new"))

    bot.reply_to(message, text="Куда сохранять-то?", reply_markup=markup)

    for entry in os.listdir(dst):
        if os.path.isfile(os.path.join(dst, entry)):
            print(entry)
    

def dump_prin():
    send_welcome("dump message")
    now = datetime.now()
    skip_time = randrange(1,24)
    next_in = now + timedelta(minutes=skip_time)
    print("Sending random photo. Next will be send at " + next_in.strftime("%d/%m/%Y %H:%M:%S") + "after " + str(skip_time) + " hours")
    schedule.enter(skip_time * 3600,1, dump_prin, ())


def schedule_random_photo():
    now = datetime.now()
    skip_time = randrange(1,24)
    next_in = now + timedelta(minutes=skip_time)
    print("Schedulling. Next will be send at " + next_in.strftime("%d/%m/%Y %H:%M:%S") + "after " + str(skip_time) + " hours")
    schedule.enter(skip_time * 3600,1, dump_prin, ())
    schedule.run()


main_loop()