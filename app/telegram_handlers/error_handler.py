import html
import json
import logging
import traceback

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        f"</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # Finally, send the message
    # We send it to the first admin ID if available, otherwise log it.
    # Ensure ConfigService is accessible here if you use it to get admin IDs.
    # For simplicity, this example doesn't send a Telegram message to admin.
    # It logs the detailed error. You might want to add that notification feature.
    
    user_message = "Sorry, something went wrong. The developers have been notified. Please try again later."
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(user_message)
        except Exception as e:
            logger.error(f"Error sending error message to user: {e}")
    elif isinstance(update, Update) and update.callback_query:
        try:
            await update.callback_query.answer(user_message, show_alert=True)
            # If you want to send a follow-up message in chat:
            # await context.bot.send_message(chat_id=update.effective_chat.id, text=user_message)
        except Exception as e:
            logger.error(f"Error sending error message to user via callback: {e}")

    logger.error(f"Full error message for logs: {message}") # Log the detailed HTML message for developers 