from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CallbackQueryHandler, ChatJoinRequestHandler

# Replace with your bot token
BOT_TOKEN = "7261504651:AAFomshxREz_pJRb5QFwOIe4JVIw-kfiHtk"

# Replace with your channel ID (use -100 prefix for private channels)
CHANNEL_ID = "+2kFG9E_8Zi8xNzZi"

# Instagram link
INSTAGRAM_LINK = "https://www.instagram.com/david.behlarian?igsh=MTJhdDlkMXRrNTZpdw=="

# 1. Handle join requests
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Yes", callback_data=f"accept_{user.id}_{update.chat_join_request.chat.id}")],
        [InlineKeyboardButton("No", callback_data=f"reject_{user.id}_{update.chat_join_request.chat.id}")]
    ])

    await context.bot.send_message(
        chat_id=user.id,
        text="Hello! Are you an applicant to the Faculty of Dentistry?",
        reply_markup=keyboard
    )

# 2. Handle button responses
async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    action, user_id, chat_id = data[0], int(data[1]), int(data[2])

    if int(query.from_user.id) != user_id:
        await query.edit_message_text("You're not allowed to answer for someone else.")
        return

    if action == "accept":
        try:
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Welcome to the chat! If you have any questions about studies or anything related, "
                     f"feel free to message me on Instagram: {INSTAGRAM_LINK}"
            )
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"Could not approve: {e}")

    elif action == "reject":
        try:
            await context.bot.decline_chat_join_request(chat_id=chat_id, user_id=user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Unfortunately, your join request has been denied. If you think this was a mistake, "
                     f"contact me on Instagram: {INSTAGRAM_LINK}"
            )
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"Could not reject: {e}")

    await query.edit_message_reply_markup(reply_markup=None)

# 3. Main function to start the bot
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(CallbackQueryHandler(handle_response))

    print("Bot is running...")
    await app.run_polling()

# Start the bot
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())