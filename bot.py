from curses import ERR
import telebot
import credentials
from yaHelper import getPhoto

bot_token = credentials.bot_token

bot = telebot.TeleBot(bot_token)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    print(message)
    #bot.reply_to(message, "Howdy, how are you doing?")
    photo = getPhoto()
    
    try:
        bot.send_photo(credentials.chat_id, photo.file)
    except Exception as exc:
        bot.send_message(credentials.chat_id, f"Unexpected {exc=}")
    
@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    print(message)
    bot.reply_to(message, message.text)
    bot.send_message(credentials.chat_id, 'Where is Bluntman?')
    
bot.infinity_polling()