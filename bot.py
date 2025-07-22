import logging
import os
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ChatJoinRequestHandler, ContextTypes, CommandHandler
from telegram.error import Forbidden, BadRequest

# --- Configuration ---
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables. Please set it.")

TARGET_CHAT_ID = os.environ.get("TARGET_CHAT_ID")
if not TARGET_CHAT_ID:
    raise ValueError("No TARGET_CHAT_ID found in environment variables. Please set it.")

INSTAGRAM_LINK = "https://www.instagram.com/david.behlarian"

# --- Logging Setup ---
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
    """Handles the /start command. Sends the verification prompt in a private message."""
    user = update.effective_user
    if not user or update.message.chat.type != 'private':
        return

    logger.info(f"Received /start command from {user.first_name} (ID: {user.id}).")
    try:
        await send_verification_message(context, user.id, int(TARGET_CHAT_ID))
    except Forbidden:
        logger.warning(f"Could not send message to {user.first_name} (ID: {user.id}).")
    except Exception as e:
        logger.error(f"Error handling /start for {user.first_name} (ID: {user.id}): {e}")


async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles new chat join requests."""
    chat_join_request = update.chat_join_request
    if not chat_join_request:
        return

    user = chat_join_request.from_user
    chat = chat_join_request.chat
    logger.info(f"Received join request from {user.first_name} (ID: {user.id}) for chat '{chat.title}'.")

    try:
        await send_verification_message(context, user.id, chat.id)
    except Forbidden:
        logger.warning(f"Could not send message to {user.first_name} (ID: {user.id}). Approving by default.")
        await context.bot.approve_chat_join_request(chat_id=chat.id, user_id=user.id)


async def handle_button_press(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and approves or declines the request."""
    query = update.callback_query
    await query.answer()

    data_parts = query.data.split("_")
    action, user_id, chat_id = data_parts[0], int(data_parts[1]), int(data_parts[2])

    if action == "approve":
        try:
            # First, try to approve a pending request. This works for the invite link flow.
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            logger.info(f"Approved existing join request for user {user_id} in chat {chat_id}.")
            welcome_message = (
                "Welcome to the chat! If you have any questions about your studies "
                f"or related matters, write to me on Instagram: {INSTAGRAM_LINK}"
            )
            await query.edit_message_text(text=welcome_message)
        except BadRequest as e:
            # This 'except' block handles the /start command flow.
            if "user is already a member" in e.message.lower() or "request not found" in e.message.lower():
                logger.info("No pending request found. Assuming /start flow. Creating new invite link.")
                try:
                    # Create a new, single-use invite link that expires in 1 hour.
                    expire_date = datetime.datetime.now() + datetime.timedelta(hours=1)
                    link = await context.bot.create_chat_invite_link(
                        chat_id=chat_id, member_limit=1, expire_date=expire_date
                    )
                    invite_message = (
                        f"Welcome! Please use this special, one-time link to join the channel: {link.invite_link}\n\n"
                        "If you have any questions, contact me on Instagram: "
                        f"{INSTAGRAM_LINK}"
                    )
                    await query.edit_message_text(text=invite_message)
                except Exception as inner_e:
                    logger.error(f"Failed to create invite link for user {user_id}: {inner_e}")
                    await query.edit_message_text(text="Could not create an invite link. Please ensure the bot has permission to invite users.")
            else:
                # Handle other unexpected API errors
                logger.error(f"Failed to approve user {user_id} for chat {chat_id}: {e}")
                await query.edit_message_text(text="An error occurred. An admin has been notified.")
        except Exception as e:
            logger.error(f"An unexpected error occurred while approving user {user_id}: {e}")
            await query.edit_message_text(text="An unexpected error occurred. Please contact an admin.")


    elif action == "decline":
        try:
            await context.bot.decline_chat_join_request(chat_id=chat_id, user_id=user_id)
            logger.info(f"Declined join request for user {user_id} in chat {chat_id}.")
            rejection_message = (
                "Unfortunately, your admission has not been approved. If you believe "
                f"this is a mistake, contact me on Instagram: {INSTAGRAM_LINK}"
            )
            await query.edit_message_text(text=rejection_message)
        except Exception as e:
            logger.error(f"Failed to decline user {user_id} for chat {chat_id}: {e}")
            await query.edit_message_text(text="An error occurred while declining your request.")


def main() -> None:
    """Sets up the bot and starts it."""
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    application.add_handler(CallbackQueryHandler(handle_button_press))
    logger.info("Bot is starting and ready to poll for updates...")
    application.run_polling()


if __name__ == "__main__":
    main()
