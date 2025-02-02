# wallet.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from config import (
    logger,
    user_data_store,
    get_text,
    create_sol_wallet,
    load_user_wallet,
    delete_user_wallet
)

# Define states for the wallet conversation
WALLET_MENU, NAME_WALLET = range(20, 22)  # offset so they don't overlap with start.py states

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /wallet command: show wallet menu inline keyboard."""
    user_id = update.effective_user.id
    kb = [
        [InlineKeyboardButton(get_text(user_id, "btn_refresh"), callback_data='wallet_refresh')],
        [
            InlineKeyboardButton(get_text(user_id, "btn_sol"), callback_data='wallet_sol'),
            InlineKeyboardButton(get_text(user_id, "btn_btc"), callback_data='wallet_btc')
        ],
        [InlineKeyboardButton(get_text(user_id, "btn_show_address"), callback_data='wallet_show')],
        [
            InlineKeyboardButton(get_text(user_id, "btn_create_wallet"), callback_data='wallet_create'),
            InlineKeyboardButton(get_text(user_id, "btn_delete_wallet"), callback_data='wallet_delete')
        ],
    ]
    await update.message.reply_text(
        get_text(user_id, "menu_wallet_title"),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.HTML
    )
    return WALLET_MENU

async def wallet_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user selection from wallet menu."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    data = query.data

    # Refresh wallet balance
    if data == 'wallet_refresh':
        user_wallet = load_user_wallet(user_id)
        if user_wallet:
            msg = get_text(user_id, "wallet_refreshed").format(
                name=user_wallet["name"],
                pub=user_wallet["public_key"],
                bal=user_wallet.get("balance_sol", 0)
            )
            await query.edit_message_text(msg, parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text(get_text(user_id, "wallet_no_exists"), parse_mode=ParseMode.HTML)
        return WALLET_MENU

    elif data == 'wallet_sol':
        # Placeholder for switching chain or default
        await query.edit_message_text("Selected SOL wallet type (placeholder).", parse_mode=ParseMode.HTML)
        return WALLET_MENU

    elif data == 'wallet_btc':
        # Placeholder for BTC logic
        await query.edit_message_text("Selected BTC wallet type (placeholder).", parse_mode=ParseMode.HTML)
        return WALLET_MENU

    elif data == 'wallet_show':
        user_wallet = user_data_store[user_id].get("wallet")
        if user_wallet:
            msg = get_text(user_id, "wallet_exists").format(
                name=user_wallet["name"],
                pub=user_wallet["public_key"],
                bal=user_wallet.get("balance_sol", 0)
            )
            await query.edit_message_text(msg, parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text(get_text(user_id, "wallet_no_exists"), parse_mode=ParseMode.HTML)
        return WALLET_MENU

    elif data == 'wallet_create':
        await query.edit_message_text(get_text(user_id, "wallet_name_prompt"), parse_mode=ParseMode.HTML)
        return NAME_WALLET

    elif data == 'wallet_delete':
        success = delete_user_wallet(user_id)
        if success:
            await query.edit_message_text(get_text(user_id, "wallet_deleted"), parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text(get_text(user_id, "wallet_not_deleted"), parse_mode=ParseMode.HTML)
        return WALLET_MENU

    else:
        await query.edit_message_text(get_text(user_id, "invalid_choice"))
        return ConversationHandler.END

async def wallet_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user input for new wallet name."""
    user_id = update.effective_user.id
    wallet_name = update.message.text.strip()
    if not wallet_name:
        await update.message.reply_text(get_text(user_id, "wallet_name_empty"), parse_mode=ParseMode.HTML)
        return NAME_WALLET

    wallet_details = create_sol_wallet(wallet_name)
    if wallet_details:
        user_data_store[user_id]["wallet"] = wallet_details
        msg = (
            f"{get_text(user_id, 'wallet_create_ok')}"
            f"<b>Name:</b> {wallet_details['name']}\n"
            f"<b>Public Key:</b> {wallet_details['public_key']}\n"
            f"<b>Secret Key:</b> {wallet_details['secret_key']}\n"
            f"<b>Balance:</b> {wallet_details['balance_sol']} SOL"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(get_text(user_id, "wallet_create_err"), parse_mode=ParseMode.HTML)

    return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the wallet conversation."""
    user_id = update.effective_user.id
    from telegram import ReplyKeyboardRemove
    await update.message.reply_text(get_text(user_id, "cancel_msg"), reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def get_wallet_conv_handler():
    """Build and return the ConversationHandler for /wallet command."""
    return ConversationHandler(
        entry_points=[CommandHandler('wallet', wallet_command)],
        states={
            WALLET_MENU: [
                CallbackQueryHandler(wallet_menu_callback, pattern='^(wallet_refresh|wallet_sol|wallet_btc|wallet_show|wallet_create|wallet_delete)$')
            ],
            NAME_WALLET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_name_handler)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)],
        allow_reentry=True
    )
