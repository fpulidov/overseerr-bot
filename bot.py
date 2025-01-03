import os
import requests
import re
import logging


from dotenv import load_dotenv
from telegram import InputMediaPhoto, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_bot.log"),
        logging.StreamHandler()
    ]
)

# Define states for the conversation
CHOOSING, ANSWERING, PICKING, SELECTING_SEASONS = range(4)

load_dotenv(override=True)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MEDIA_LIBRARY_TOKEN = os.getenv('MEDIA_LIBRARY_MANAGER_TOKEN')
MERIA_LIBRARY_URL = os.getenv('MERIA_LIBRARY_URL')

WHITELISTED_USERS = os.getenv('WHITELISTED_USERS')

# Logging helper

def log_user_action(update, action):
    user = update.effective_user
    username = user.username if user.username else "Unknown"
    logging.info(f"USER: {username} (ID: {user.id}) - ACTION: {action}")

# Start command handler
async def start(update: Update, context):
    user_id = update.message.from_user.id
    username = update.message.from_user.username

    log_user_action(update, "Issued /start command")

    if str(user_id) not in WHITELISTED_USERS:
        await update.message.reply_text("You are not authorized to use this bot.")
        logging.warning(f"Unauthorized access attempt by USER: {username} (ID: {user_id})")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("TV Shows", callback_data="tv")],
        [InlineKeyboardButton("Movies", callback_data="movie")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Shows or movies:", reply_markup=reply_markup)
    return CHOOSING

# CallbackQueryHandler to handle button clicks
async def handle_choice(update: Update, context):
    query = update.callback_query
    await query.answer()
    choice = query.data

    log_user_action(update, f"Selected choice: {choice}")

    if choice not in ["tv", "movie"]:
        await query.edit_message_text("Invalid choice. Please start over.")
        return ConversationHandler.END

    context.user_data['choice'] = choice
    await query.edit_message_text(text="What title are you looking for?")
    return ANSWERING

# MessageHandler to capture the user's answer
async def handle_answer(update: Update, context):
    choice = context.user_data.get('choice')
    answer = sanitize_input(update.message.text)

    log_user_action(update, f"Searched for: {answer} in {choice}")

    if not answer:
        await update.message.reply_text("Invalid input. Please try again.")
        return ANSWERING

    media_found = get_media(answer, choice)
    context.user_data['media_found'] = media_found
    context.user_data['current_index'] = 0

    if len(media_found) > 1:
        await update.message.reply_text(f"Found {len(media_found)} results")

    if media_found:
        await send_media_poster(update, context)
        return PICKING
    else:
        await update.message.reply_text("No results found.")
        return ConversationHandler.END

# Function to send a media poster
async def send_media_poster(update: Update, context):
    media_found = context.user_data.get('media_found', [])
    current_index = context.user_data.get('current_index', 0)

    if current_index < len(media_found):
        media = media_found[current_index]
        mediaTitle = media.get("title", media.get("name", "Unknown"))
        mediaPoster = (
            open("./images/posternotfound.jpg", 'rb')
            if media.get("posterPath") is None
            else 'https://image.tmdb.org/t/p/w600_and_h900_bestv2' + media["posterPath"]
        )

        log_user_action(update, f"Viewing media: {mediaTitle}")

        keyboard = [
            [InlineKeyboardButton("✅ Correct", callback_data="correct")],
            [InlineKeyboardButton("❌ Incorrect", callback_data="incorrect")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            query = update.callback_query
            context.user_data['currentMedia'] = media
            await query.edit_message_media(
                media=InputMediaPhoto(
                    media=mediaPoster,
                    caption=f"Is this the media you requested? ({mediaTitle})"
                ),
                reply_markup=reply_markup
            )
        else:
            context.user_data['currentMedia'] = media
            await update.message.reply_photo(
                photo=mediaPoster,
                caption=f"Is this the media you requested? ({mediaTitle})",
                reply_markup=reply_markup
            )
        return PICKING
    else:
        notfound = open("./images/404.jpeg", 'rb')
        query = update.callback_query  
        await query.edit_message_media(
                media=InputMediaPhoto(
                    media=notfound,
                    caption=f"No more results to be shown"))
        await query.answer()
        context.user_data.clear() 
        return ConversationHandler.END

# CallbackQueryHandler to process user choice on posters
async def handle_picking(update: Update, context):
    query = update.callback_query
    await query.answer()
    mediaType = context.user_data.get('choice')
    currentMedia = context.user_data.get('currentMedia')

    choice = query.data
    log_user_action(update, f"User picked: {choice} for media {currentMedia}")

    if choice == "correct":
        if mediaType == "tv":
            await query.edit_message_caption(
                "Great! Please enter the seasons you want to download:\n"
                "- Enter `0` to download all seasons.\n"
                "- Enter a comma-separated list like `1,2,3` for specific seasons."
            )
            return SELECTING_SEASONS
        else:
            request_to_media_manager(currentMedia)
            await query.edit_message_caption("Movie requested successfully. ✅")
            context.user_data.clear()
            return ConversationHandler.END
    elif choice == "incorrect":
        context.user_data['current_index'] += 1
        return await send_media_poster(update, context)

# Cancel command handler
async def cancel(update: Update, context):
    log_user_action(update, "Cancelled the conversation")
    await update.message.reply_text("Conversation cancelled.")
    return ConversationHandler.END

async def handle_season_selection(update: Update, context):
    user_input = sanitize_input(update.message.text)
    currentMedia = context.user_data.get('currentMedia')

    log_user_action(update, f"Selected seasons: {user_input}")

    try:
        if user_input.strip() == "0":
            seasons = []
            numberOfSeasons = get_series_seasons(currentMedia["id"])
            seasons = list(range(1, numberOfSeasons + 1))
        else:
            seasons = [int(s.strip()) for s in user_input.split(",")]

        success = request_to_media_manager(currentMedia, seasons)
        if success:
            await update.message.reply_text("Request successfully sent. ✅")
        else:
            await update.message.reply_text("Failed to send the request. Please try again.")

    except (ValueError, IndexError):
        await update.message.reply_text(
            "Invalid input. Please enter `0` for all seasons or a comma-separated list like `1,2,3`."
        )
        return SELECTING_SEASONS

    context.user_data.clear()
    return ConversationHandler.END

# Helper function to fetch media
def get_media(name, media_type):
    url = MERIA_LIBRARY_URL + f'/api/v1/search?query={name}&page=1&language=en'
    headers = {'Accept': 'application/json', 'X-Api-Key': MEDIA_LIBRARY_TOKEN}
    logging.info(f"API call to: {url} with headers: {headers}")

    returned_media = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            raw_data = response.json()
            for result in raw_data['results']:
                if result["mediaType"] == media_type:
                    returned_media.append(result)
        else:
            logging.error(f"Failed API call with status code: {response.status_code}")
    except requests.RequestException as e:
        logging.error(f"Error during API call: {e}")

    return returned_media

# Helper function to sanitize user input
def sanitize_input(user_input):
    return re.sub(r'[^a-zA-Z0-9, ]', '', user_input.strip())

# Helper function to request media from Media Manager
def request_to_media_manager(media, seasons=None):
    payload = {
        "mediaId": media["id"],
        "mediaType": media["mediaType"],
        "seasons": seasons if seasons else []
    }
    headers = {'Content-Type': 'application/json', 'X-Api-Key': MEDIA_LIBRARY_TOKEN}
    url = MERIA_LIBRARY_URL + '/api/v1/request'

    logging.info(f"Requesting media with payload: {payload}")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 201:
            logging.info("Media request successful.")
            return True
        else:
            logging.error(f"Media request failed with status code: {response.status_code}")
    except requests.RequestException as e:
        logging.error(f"Error during media request: {e}")

    return False

# Helper function to fetch number of seasons for a series
def get_series_seasons(series_id):
    url = MERIA_LIBRARY_URL + f'/api/v1/tv/{series_id}'
    headers = {'Accept': 'application/json', 'X-Api-Key': MEDIA_LIBRARY_TOKEN}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            series_data = response.json()
            return series_data.get("numberOfSeasons", 0)
        else:
            logging.error(f"Failed to fetch seasons with status code: {response.status_code}")
    except requests.RequestException as e:
        logging.error(f"Error during fetching seasons: {e}")

    return 0

# Main function to initialize the bot
def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [CallbackQueryHandler(handle_choice)],
            ANSWERING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            PICKING: [CallbackQueryHandler(handle_picking)],
            SELECTING_SEASONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_season_selection)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
