# settings.py
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.constants import ParseMode
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from config import logger, user_data_store, get_text

# Define states
SETTINGS_MENU, WAITING_FOR_MOBILE = range(30, 32)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /settings command - shows an inline menu."""
    user_id = update.effective_user.id
    kb = [
        [InlineKeyboardButton("Change Language", callback_data='settings_language')],
        [InlineKeyboardButton("Mobile Number", callback_data='settings_mobile')],
        [InlineKeyboardButton("Close Menu", callback_data='settings_close')]
    ]
    await update.message.reply_text(
        get_text(user_id, "menu_settings_title"),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.HTML
    )
    return SETTINGS_MENU

async def settings_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline menu for settings."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    data = query.data

    if data == 'settings_language':
        kb = [
            [
                InlineKeyboardButton("English", callback_data='setlang_en'),
                InlineKeyboardButton("中文", callback_data='setlang_zh')
            ]
        ]
        await query.edit_message_text("Choose your preferred language:", reply_markup=InlineKeyboardMarkup(kb))
        return SETTINGS_MENU

    elif data.startswith("setlang_"):
        new_lang = data.replace("setlang_", "")
        user_data_store[user_id]["lang"] = new_lang
        await query.edit_message_text(get_text(user_id, "lang_updated"), parse_mode=ParseMode.HTML)
        return SETTINGS_MENU

    elif data == 'settings_mobile':
        await query.edit_message_text(get_text(user_id, "enter_mobile"), parse_mode=ParseMode.HTML)
        return WAITING_FOR_MOBILE

    elif data == 'settings_close':
        await query.edit_message_text(get_text(user_id, "btn_close_menu"), parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    else:
        await query.edit_message_text(get_text(user_id, "invalid_choice"), parse_mode=ParseMode.HTML)
        return ConversationHandler.END

async def mobile_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the user's mobile number and store it."""
    user_id = update.effective_user.id
    mobile = update.message.text.strip()
    user_data_store[user_id]["mobile_number"] = mobile
    msg = get_text(user_id, "mobile_saved").format(number=mobile)
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    from telegram import ReplyKeyboardRemove
    await update.message.reply_text(get_text(user_id, "cancel_msg"), reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def get_settings_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('settings', settings_command)],
        states={
            SETTINGS_MENU: [
                CallbackQueryHandler(settings_menu_callback, pattern='^(settings_language|settings_mobile|settings_close|setlang_)')
            ],
            WAITING_FOR_MOBILE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, mobile_number_handler)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_command)],
        allow_reentry=True
    )
