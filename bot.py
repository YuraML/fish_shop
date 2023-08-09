import logging
import os
import redis

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater, CallbackQueryHandler, CommandHandler, MessageHandler, CallbackContext

from services import get_access_token, get_products, get_product, get_product_image_url, add_product_to_cart, \
    get_cart_products, get_cart, remove_product_from_cart, add_client_email

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
    cart_button = InlineKeyboardButton('Cart', callback_data='cart')
    keyboard.append([cart_button])

    return InlineKeyboardMarkup(keyboard)


def show_cart(update: Update, context: CallbackContext, access_token, chat_id):
    products = get_cart_products(access_token, chat_id)
    products_buttons = []
    text_message = 'Your cart:\n'

    for product in products['data']:
        product_name = product['name']
        product_ordered_amount = product['quantity']
        product_description = product['description']
        product_price = product['meta']['display_price']['with_tax']['unit']['formatted']

        cart_item_id = product['id']
        cart_item_cost = product['meta']['display_price']['with_tax']['value']['formatted']

        text_message += f"""
        \n{product_name}
        \n{product_price} for kg
        \n{product_description}
        \n{product_ordered_amount} kg in cart for {cart_item_cost}
        """

        products_buttons.append(
            InlineKeyboardButton(
                f"Remove {product_name} from the cart", callback_data=cart_item_id
            )
        )

    back_to_menu_button = [InlineKeyboardButton('Back to Menu', callback_data='back_to_menu')]
    pay_button = [InlineKeyboardButton('Pay', callback_data='pay')]
    keyboard = [products_buttons, pay_button, back_to_menu_button]
    reply_markup = InlineKeyboardMarkup(keyboard)

    cart = get_cart(access_token, chat_id)
    cart_total_cost = cart['data']['meta']['display_price']['with_tax']['formatted']
    text_message += f'\nTotal: {cart_total_cost}'

    return text_message, reply_markup


def start(update: Update, context: CallbackContext, access_token):
    reply_markup = fetch_products(access_token)
    update.message.reply_text('Choose an available fish:', reply_markup=reply_markup)
    return 'HANDLE_MENU'


def handle_menu(update: Update, context: CallbackContext, access_token):
    query = update.callback_query
    product_id = query.data
    if product_id == 'cart':
        chat_id = query.from_user.id
        cart_text, reply_markup = show_cart(update, context, access_token, chat_id)
        context.bot.send_message(chat_id=query.message.chat_id, text=cart_text, reply_markup=reply_markup)

        context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        return 'HANDLE_CART'

    product = get_product(access_token, product_id)['data']
    product_name = product['attributes']['name']
    product_description = product['attributes']['description']
    text = f'{product_name}\n\n{product_description}'

    keyboard = [
        [InlineKeyboardButton('1 kg', callback_data=f'{product_id}_1'),
         InlineKeyboardButton('5 kg', callback_data=f'{product_id}_5'),
         InlineKeyboardButton('10 kg', callback_data=f'{product_id}_10')],
        [InlineKeyboardButton('Cart', callback_data='cart')],
        [InlineKeyboardButton('Back', callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    image_id = product['relationships']['main_image']['data']['id']
    image_url = get_product_image_url(access_token, image_id)
    context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url, caption=text, reply_markup=reply_markup)

    context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
    return 'HANDLE_DESCRIPTION'


def handle_description(update: Update, context: CallbackContext, access_token):
    query = update.callback_query
    if query.data == 'back':
        reply_markup = fetch_products(access_token)
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Choose an available fish:",
            reply_markup=reply_markup,
        )
        context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        return 'HANDLE_MENU'

    elif query.data == 'cart':
        chat_id = query.from_user.id
        text_message, reply_markup = show_cart(update, context, access_token, chat_id)
        context.bot.send_message(chat_id=query.message.chat_id, text=text_message, reply_markup=reply_markup)
        context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        return 'HANDLE_CART'

    product_id, quantity = query.data.split('_')
    product = get_product(access_token, product_id)
    product_name = product['data']['attributes']['name']
    chat_id = query.from_user.id
    add_product_to_cart(access_token, chat_id, product_id, int(quantity))

    keyboard = [
        [InlineKeyboardButton('Back to Menu', callback_data='back'),
         InlineKeyboardButton('Cart', callback_data='cart')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"Added {quantity} kg of {product_name} to your cart!",
        reply_markup=reply_markup,
    )

    context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
    return 'HANDLE_DESCRIPTION'


def handle_cart(update: Update, context: CallbackContext, access_token):
    query = update.callback_query
    chat_id = query.message.chat.id
    cart_item_id = query.data

    if cart_item_id == 'back_to_menu':
        reply_markup = fetch_products(access_token)
        context.bot.send_message(chat_id=chat_id, text='Choose an available fish:', reply_markup=reply_markup)
        context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        return 'HANDLE_MENU'

    elif cart_item_id == 'pay':
        context.bot.send_message(chat_id=chat_id, text='Please provide your email address:')
        context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        return 'WAITING_EMAIL'

    remove_product_from_cart(access_token, chat_id, cart_item_id)
    text_message, reply_markup = show_cart(update, context, access_token, chat_id)
    query.message.edit_text(text_message, reply_markup=reply_markup)

    return 'HANDLE_CART'


def handle_email(update: Update, context: CallbackContext, access_token):
    chat_id = update.message.chat_id
    email = update.message.text
    add_client_email(access_token, chat_id, email)
    context.bot.send_message(chat_id=chat_id, text=f'You provided the email address: {email}. Thank you!')

    reply_markup = fetch_products(access_token)
    context.bot.send_message(chat_id=chat_id, text='Choose an available fish:', reply_markup=reply_markup)

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
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': handle_email
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(update, context, access_token)
        db.set(chat_id, next_state)
    except Exception as err:
        logger.error(f'Error while processing update: {err}', exc_info=True)


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
