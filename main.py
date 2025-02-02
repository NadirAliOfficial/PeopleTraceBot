# main.py
import nest_asyncio
from telegram.ext import ApplicationBuilder
from config import logger
from start import (
    get_start_conv_handler,
    END,  # If you want to reference the END state from start.py
)
from wallet import get_wallet_conv_handler
from settings import get_settings_conv_handler

nest_asyncio.apply()

async def error_handler(update, context):
    logger.error("Exception:", exc_info=context.error)
    if update and update.effective_message:
        # Optional: you can custom-handle errors here
        await update.effective_message.reply_text("An error occurred. Please try again.")

def main():
    TOKEN = "7333467475:AAE-S2Hom4XZI_sfyCbrFrLkmXy6aQpL_GI"
    if not TOKEN:
        logger.error("No BOT TOKEN found.")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # Add conversation handlers from separate modules
    start_conv = get_start_conv_handler()
    wallet_conv = get_wallet_conv_handler()
    settings_conv = get_settings_conv_handler()

    application.add_handler(start_conv)
    application.add_handler(wallet_conv)
    application.add_handler(settings_conv)

    # Add a global error handler
    application.add_error_handler(error_handler)

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
