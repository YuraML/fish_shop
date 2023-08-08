import logging
import os
import redis

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, CallbackContext

from services import get_access_token, get_products, get_product, get_product_image_url

_database = None

logging.basicConfig(
    format='%(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


def fetch_products(access_token):
    products = get_products(access_token)['data']
    keyboard = [[]]
    for product in products:
        fish_name = product['attributes']['name']
        fish_id = product['id']
        fish_button = InlineKeyboardButton(fish_name, callback_data=fish_id)
        keyboard[0].append(fish_button)

    return InlineKeyboardMarkup(keyboard)


def start(update: Update, context: CallbackContext, access_token):
    reply_markup = fetch_products(access_token)
    update.message.reply_text('Choose an available fish:', reply_markup=reply_markup)
    return 'HANDLE_MENU'


def handle_menu(update: Update, context: CallbackContext, access_token):
    query = update.callback_query
    product_id = query.data
    product = get_product(access_token, product_id)['data']
    product_name = product['attributes']['name']
    product_description = product['attributes']['description']

    text = f"{product_name}\n\n{product_description}"
    keyboard = [[InlineKeyboardButton('Back', callback_data='back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    image_id = product['relationships']['main_image']['data']['id']
    image_url = get_product_image_url(access_token, image_id)
    context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url, caption=text, reply_markup=reply_markup)

    context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
    return 'HANDLE_DESCRIPTION'


def handle_description(update: Update, context: CallbackContext, access_token):
    if update.callback_query.data == 'back':
        reply_markup = fetch_products(access_token)
        query = update.callback_query
        context.bot.send_message(chat_id=query.message.chat_id, text='Choose an available fish:',
                                 reply_markup=reply_markup)

        return 'HANDLE_MENU'


def handle_users_reply(update: Update, context: CallbackContext):
    client_id = os.getenv('EP_CLIENT_ID')
    client_secret = os.getenv('EP_CLIENT_SECRET')
    access_token = get_access_token(client_id, client_secret)
    db = get_database_connection()

    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode('utf-8')

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(update, context, access_token)
        db.set(chat_id, next_state)
    except Exception as err:
        logger.error(f"Error while processing update: {err}", exc_info=True)


def get_database_connection():
    global _database
    if _database is None:
        database_password = os.getenv('DATABASE_PASSWORD')
        database_host = os.getenv('DATABASE_HOST')
        database_port = os.getenv('DATABASE_PORT')
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


if __name__ == '__main__':
    load_dotenv()
    tg_token = os.getenv('TELEGRAM_TOKEN')
    updater = Updater(tg_token)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))

    updater.start_polling()
