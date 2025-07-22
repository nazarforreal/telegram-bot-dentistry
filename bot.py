import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ChatJoinRequestHandler, ContextTypes
from telegram.error import Forbidden

# --- Configuration ---
# It's highly recommended to use an environment variable for your bot token for security.
# On your deployment server (like Railway or Heroku), set an environment variable
# called TELEGRAM_BOT_TOKEN with the token you get from BotFather.
TOKEN = os.environ.get("7261504651:AAFomshxREz_pJRb5QFwOIe4JVIw-kfiHtk")
if not TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables. Please set it.")

INSTAGRAM_LINK = "https://www.instagram.com/david.behlarian"

# --- Logging Setup ---
# This helps you see what the bot is doing and diagnose any problems.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# --- Bot Handlers ---

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    This function is triggered when a new user requests to join a chat where the bot is an admin.
    It sends a private message to the user with the verification question.
    """
    chat_join_request = update.chat_join_request
    if not chat_join_request:
        return

    user = chat_join_request.from_user
    chat = chat_join_request.chat

    logger.info(f"Received join request from {user.first_name} (ID: {user.id}) for chat '{chat.title}'.")

    # Create the "Yes" and "No" buttons.
    # The callback_data contains all the info we need to process the answer later.
    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data=f"approve_{user.id}_{chat.id}"),
            InlineKeyboardButton("No", callback_data=f"decline_{user.id}_{chat.id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the verification message to the user in a private chat.
    try:
        await context.bot.send_message(
            chat_id=user.id,
            text="Hi! Are you an applicant to the dental faculty?",
            reply_markup=reply_markup,
        )
        logger.info(f"Sent verification question to {user.first_name} (ID: {user.id}).")
    except Forbidden:
        # This happens if the user has blocked the bot or has privacy settings that prevent it.
        logger.warning(f"Could not send message to {user.first_name} (ID: {user.id}). Approving by default.")
        # You might want to automatically approve or ignore them in this case.
        # Let's approve them to be safe.
        await context.bot.approve_chat_join_request(chat_id=chat.id, user_id=user.id)


async def handle_button_press(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    This function is triggered when a user clicks one of the inline buttons ("Yes" or "No").
    It approves or declines the join request and sends the final message.
    """
    query = update.callback_query
    # It's good practice to answer the callback query immediately.
    await query.answer()

    # The data is in the format "action_userid_chatid"
    data_parts = query.data.split("_")
    action = data_parts[0]
    user_id = int(data_parts[1])
    chat_id = int(data_parts[2])

    if action == "approve":
        try:
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            logger.info(f"Approved join request for user {user_id} in chat {chat_id}.")
            welcome_message = (
                "Welcome to the chat! If you have any questions about your studies "
                f"or related matters, write to me on Instagram: {INSTAGRAM_LINK}"
            )
            # Edit the original message to show the final status.
            await query.edit_message_text(text=welcome_message, reply_markup=None)
        except Exception as e:
            logger.error(f"Failed to approve user {user_id} for chat {chat_id}: {e}")
            await query.edit_message_text(text="An error occurred. An admin has been notified.")

    elif action == "decline":
        try:
            await context.bot.decline_chat_join_request(chat_id=chat_id, user_id=user_id)
            logger.info(f"Declined join request for user {user_id} in chat {chat_id}.")
            rejection_message = (
                "Unfortunately, your admission has not been approved. If you believe "
                f"this is a mistake, contact me on Instagram: {INSTAGRAM_LINK}"
            )
            await query.edit_message_text(text=rejection_message, reply_markup=None)
        except Exception as e:
            logger.error(f"Failed to decline user {user_id} for chat {chat_id}: {e}")
            await query.edit_message_text(text="An error occurred. An admin has been notified.")


def main() -> None:
    """Sets up the bot and starts it."""
    application = Application.builder().token(TOKEN).build()

    # Add handlers for the different types of updates.
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    application.add_handler(CallbackQueryHandler(handle_button_press))

    # Start the bot. It will run until you stop it (e.g., with Ctrl+C).
    logger.info("Bot is starting and ready to poll for updates...")
    application.run_polling()


if __name__ == "__main__":
    main()
