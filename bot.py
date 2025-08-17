import logging
import itertools
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler
)

# ---------------- LOGGING ----------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- CONFIG ----------------
TOKEN = "8371436620:AAEg1dglVdi8-5zIR2PyifF1RnRgY7W5DHo"

RAPIDAPI_KEYS = [
    "curl --request GET 
	--url 'https://social-media-video-downloader.p.rapidapi.com/smvd/get/youtube?url=https%3A%2F%2Fyoutu.be%2F9kH_p8FhBZI' 
	--header 'x-rapidapi-host: social-media-video-downloader.p.rapidapi.com' 
	--header 'x-rapidapi-key: 1d55df928amshfb061b3133ea350p136696jsn06a0379bd261", 
    "YOUR_SECOND_RAPIDAPI_KEY",
    " YOUR_THIRD_RAPIDAPI_KEY"
]
key_cycle = itertools.cycle(RAPIDAPI_KEYS)

# ---------------- GLOBAL ----------------
user_state = {}
active_chats = set()

def get_api_key():
    return next(key_cycle)

# ---------------- REPLY KEYBOARDS ----------------
def main_keyboard():
    return ReplyKeyboardMarkup([["📥 Download Video"]], resize_keyboard=True)

def another_keyboard():
    return ReplyKeyboardMarkup([["📼 Download Another Video"]], resize_keyboard=True)

# ---------------- INLINE MENU ----------------
def inline_help_menu():
    keyboard = [
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------------- START ----------------
def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    active_chats.add(chat_id)

    welcome_message = (
        f"👋 Hello {user.first_name}!\n\n"
        "Welcome to Facebook Video Downloader Bot\n\n"
        "Get high-quality downloads from Facebook videos instantly!"
    )

    update.message.reply_text(welcome_message, reply_markup=main_keyboard())

# ---------------- HELP ----------------
def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "📌 How to download Facebook videos:\n\n"
        "1. Click 'Download Video' button\n"
        "2. Paste the Facebook video link\n"
        "3. Wait a few seconds while we process\n"
        "4. Choose your preferred quality\n\n"
        "⚠️ Important Notes:\n"
        "- Works with public videos only\n"
        "- Supports most Facebook video formats\n"
        "- No watermarks on downloaded videos"
    )
    if update.callback_query:
        update.callback_query.edit_message_text(help_text, reply_markup=inline_help_menu())
    else:
        update.message.reply_text(help_text, reply_markup=inline_help_menu())

# ---------------- FETCH VIDEO ----------------
def fetch_video_info(url: str) -> dict:
    api_url = "https://social-media-video-downloader.p.rapidapi.com/smvd/get/facebook"
    headers = {
        "x-rapidapi-key": get_api_key(),
        "x-rapidapi-host": "social-media-video-downloader.p.rapidapi.com"
    }
    params = {"url": url}

    try:
        response = requests.get(api_url, headers=headers, params=params, timeout=15)
        return response.json()
    except Exception as e:
        logger.error(f"API Error: {e}")
        return {"success": False, "message": "API request failed"}

# ---------------- MESSAGE HANDLER ----------------
def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text == "📥 Download Video":
        user_state[user_id] = 'waiting_for_url'
        update.message.reply_text("📥 Enter your Facebook video URL", reply_markup=ReplyKeyboardRemove())

    elif text == "📼 Download Another Video":
        user_state[user_id] = 'waiting_for_url'
        update.message.reply_text("📼 Enter another Facebook video URL", reply_markup=ReplyKeyboardRemove())

    elif user_state.get(user_id) == 'waiting_for_url':
        process_video_url(update, context, text)

    else:
        update.message.reply_text("Please use the menu below.", reply_markup=main_keyboard())

# ---------------- PROCESS VIDEO URL ----------------
def process_video_url(update: Update, context: CallbackContext, url: str) -> None:
    user_id = update.effective_user.id

    if not ("facebook.com" in url or "fb.watch" in url):
        update.message.reply_text("❌ Invalid URL. Please send a valid Facebook video link.")
        return

    loading_msg = update.message.reply_text("⏳ Processing your video... Please wait")

    data = fetch_video_info(url)
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)

    if not data.get('success'):
        update.message.reply_text("❌ Failed to download. Please check:\n- The video is public\n- The link is correct\n- Try again later",
                                  reply_markup=main_keyboard())
        return

    title = data.get('title', 'Facebook Video')
    thumbnail = data.get('picture')
    links = data.get('links', [])

    hd_link = next((link['link'] for link in links if 'hd' in link.get('quality', '').lower()), None)
    sd_link = next((link['link'] for link in links if 'sd' in link.get('quality', '').lower()), None)

    buttons = []
    if hd_link:
        buttons.append([InlineKeyboardButton("⬇️ HD Download", url=hd_link)])
    if sd_link:
        buttons.append([InlineKeyboardButton("⬇️ SD Download", url=sd_link)])

    if not buttons:
        update.message.reply_text("⚠️ No downloadable links found for this video", reply_markup=main_keyboard())
        return

    reply_markup = InlineKeyboardMarkup(buttons)
    caption = f"🎬 {title}\n\nSelect your preferred download quality:"

    try:
        if thumbnail:
            update.message.reply_photo(photo=thumbnail, caption=caption, reply_markup=reply_markup)
        else:
            update.message.reply_text(caption, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error sending response: {e}")
        update.message.reply_text(caption, reply_markup=reply_markup)

    # Change bottom menu to "Download Another Video"
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="You can download another video now.",
                             reply_markup=another_keyboard())

# ---------------- ERROR HANDLER ----------------
def error_handler(update: Update, context: CallbackContext) -> None:
    logger.error("Error:", exc_info=context.error)
    if update and update.message:
        update.message.reply_text('⚠️ An error occurred. Please try again.')

# ---------------- MAIN ----------------
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_error_handler(error_handler)

    updater.start_polling()
    logger.info("Bot started and polling...")
    updater.idle()

if __name__ == '__main__':
    main()