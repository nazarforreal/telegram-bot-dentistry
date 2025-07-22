import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ChatJoinRequestHandler, ContextTypes, CommandHandler
from telegram.error import Forbidden

# --- Configuration ---
# It's highly recommended to use environment variables for your bot token and chat ID for security.
# On your deployment server (like Railway), set these environment variables.
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables. Please set it.")

# You MUST set this to the ID of the channel you want to manage.
# To get the ID, add a bot like @userinfobot to your channel; it will show the chat ID.
# The ID will be a negative number, e.g., -1001234567890
TARGET_CHAT_ID = os.environ.get("TARGET_CHAT_ID")
if not TARGET_CHAT_ID:
    raise ValueError("No TARGET_CHAT_ID found in environment variables. Please set it.")


INSTAGRAM_LINK = "https://www.instagram.com/david.behlarian"

# --- Logging Setup ---
# This helps you see what the bot is doing and diagnose any problems.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# --- Helper Functions ---

async def send_verification_message(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int) -> None:
    """Sends the verification message with Yes/No buttons."""
    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data=f"approve_{user_id}_{chat_id}"),
            InlineKeyboardButton("No", callback_data=f"decline_{user_id}_{chat_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=user_id,
        text="Hi! Are you an applicant to the dental faculty?",
        reply_markup=reply_markup,
    )
    logger.info(f"Sent verification question to user {user_id} for chat {chat_id}.")


# --- Bot Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /start command. Sends the verification prompt in a private message.
    """
    user = update.effective_user
    if not user or update.message.chat.type != 'private':
        return

    logger.info(f"Received /start command from {user.first_name} (ID: {user.id}).")
    try:
        # Use the configured TARGET_CHAT_ID for the /start command
        await send_verification_message(context, user.id, int(TARGET_CHAT_ID))
    except Forbidden:
        logger.warning(f"Could not send message to {user.first_name} (ID: {user.id}). User has likely blocked the bot.")
    except Exception as e:
        logger.error(f"Error handling /start for {user.first_name} (ID: {user.id}): {e}")


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

    try:
        await send_verification_message(context, user.id, chat.id)
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
            # For the /start command flow, the bot needs to be able to invite users.
            # This requires the "Invite Users via Link" permission.
            # For a join request, this just approves the existing request.
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
            # This will decline an existing request. If triggered via /start, it does nothing,
            # which is fine since there's no active request to decline.
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
    application.add_handler(CommandHandler("start", start))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    application.add_handler(CallbackQueryHandler(handle_button_press))

    # Start the bot. It will run until you stop it (e.g., with Ctrl+C).
    logger.info("Bot is starting and ready to poll for updates...")
    application.run_polling()


if __name__ == "__main__":
    main()
