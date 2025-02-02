# start.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
import math
import pycountry
import geonamescache

from config import logger, user_data_store, LANG_DATA, get_text

# === Define states for start flow ===
(
    SELECT_LANG,
    CHOOSE_COUNTRY,
    SHOW_DISCLAIMER,
    CHOOSE_CITY,
    CHOOSE_ACTION,
    CHOOSE_WALLET_TYPE,
    NAME_WALLET,
    END,
) = range(8)

gc = geonamescache.GeonamesCache()

def get_country_matches(query):
    query = query.lower()
    return [c.name for c in pycountry.countries if query in c.name.lower()]

def get_cities_by_country(country_name):
    country = pycountry.countries.get(name=country_name)
    if not country:
        return []
    country_code = country.alpha_2
    all_cities = gc.get_cities().values()
    filtered = [city for city in all_cities if city['countrycode'] == country_code]
    if not filtered:
        return []
    sorted_cities = sorted(filtered, key=lambda x: x['population'], reverse=True)
    return [city['name'] for city in sorted_cities[:50]]

def get_city_matches(country_name, query):
    return [c for c in get_cities_by_country(country_name) if query.lower() in c.lower()]

def paginate_list(items, page, items_per_page=10):
    total_pages = max(1, math.ceil(len(items) / items_per_page)) if items else 1
    page = max(1, min(page, total_pages))
    start = (page - 1) * items_per_page
    end = start + items_per_page
    return items[start:end], total_pages

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for the /start command."""
    buttons = [
        [
            InlineKeyboardButton(LANG_DATA["en"]["lang_button"], callback_data='lang_en'),
            InlineKeyboardButton(LANG_DATA["zh"]["lang_button"], callback_data='lang_zh'),
        ]
    ]
    await update.message.reply_text(
        f"{LANG_DATA['en']['start_msg']}\n\n{LANG_DATA['zh']['start_msg']}",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )
    return SELECT_LANG

async def select_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection from the inline keyboard."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_id = update.effective_user.id
    # Auto-initialize if needed
    if user_id not in user_data_store:
        user_data_store[user_id] = {}
    data = query.data

    if data == 'lang_en':
        user_data_store[user_id] = {"lang": "en"}
    elif data == 'lang_zh':
        user_data_store[user_id] = {"lang": "zh"}
    else:
        user_data_store[user_id] = {"lang": "en"}

    await query.edit_message_text(get_text(user_id, "choose_country"), parse_mode=ParseMode.HTML)
    return CHOOSE_COUNTRY

async def choose_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    txt = update.message.text.strip()
    matches = get_country_matches(txt)

    if not matches:
        await update.message.reply_text(get_text(user_id, "country_not_found"))
        return CHOOSE_COUNTRY

    if len(matches) == 1:
        user_data_store[user_id]["country"] = matches[0]
        await show_disclaimer(update, context)
        return SHOW_DISCLAIMER
    else:
        user_data_store[user_id]["country_matches"] = matches
        user_data_store[user_id]["country_page"] = 1
        paginated, total = paginate_list(matches, 1)
        kb = []
        for c in paginated:
            kb.append([InlineKeyboardButton(c, callback_data=f"country_select_{c}")])
        # Add pagination if more than one page
        if total > 1:
            kb.append([
                InlineKeyboardButton("⬅️", callback_data="country_page_0"),
                InlineKeyboardButton("➡️", callback_data="country_page_2")
            ])

        await update.message.reply_text(
            f"Multiple countries found (1/{total}):",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )
        return CHOOSE_COUNTRY

async def country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    data = query.data

    if data.startswith("country_select_"):
        country = data.replace("country_select_", "")
        user_data_store[user_id]["country"] = country
        await query.edit_message_text(f"You have selected {country}.", parse_mode=ParseMode.HTML)
        await show_disclaimer(update, context)
        return SHOW_DISCLAIMER

    elif data.startswith("country_page_"):
        page_str = data.replace("country_page_", "")
        try:
            page_num = int(page_str)
            if page_num < 1:
                page_num = 1
        except ValueError:
            page_num = 1

        matches = user_data_store[user_id].get("country_matches", [])
        paginated, total = paginate_list(matches, page_num)
        kb = []
        for c in paginated:
            kb.append([InlineKeyboardButton(c, callback_data=f"country_select_{c}")])

        nav_row = []
        if page_num > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"country_page_{page_num - 1}"))
        if page_num < total:
            nav_row.append(InlineKeyboardButton("➡️", callback_data=f"country_page_{page_num + 1}"))
        if nav_row:
            kb.append(nav_row)

        await query.edit_message_text(
            f"Multiple countries found ({page_num}/{total}):",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )
        user_data_store[user_id]["country_page"] = page_num
        return CHOOSE_COUNTRY

    else:
        await query.edit_message_text(get_text(user_id, "invalid_choice"))
        return ConversationHandler.END

async def show_disclaimer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    text = f"{get_text(user_id, 'disclaimer_title')}{get_text(user_id, 'disclaimer_text')}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(get_text(user_id, "agree_btn"), callback_data='agree')],
        [InlineKeyboardButton(get_text(user_id, "disagree_btn"), callback_data='disagree')]
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return SHOW_DISCLAIMER

async def disclaimer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'agree':
        await query.edit_message_text(get_text(user_id, "enter_city"), parse_mode=ParseMode.HTML)
        return CHOOSE_CITY
    else:
        await query.edit_message_text(get_text(user_id, "disagree_end"), parse_mode=ParseMode.HTML)
        return ConversationHandler.END

async def choose_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    city_input = update.message.text.strip()
    country = user_data_store[user_id].get("country")
    if not country:
        await update.message.reply_text(get_text(user_id, "invalid_choice"))
        return ConversationHandler.END

    matches = get_city_matches(country, city_input)
    if not matches:
        await update.message.reply_text(get_text(user_id, "city_not_found"))
        return CHOOSE_CITY

    if len(matches) == 1:
        user_data_store[user_id]["city"] = matches[0]
        await update.message.reply_text(f"{get_text(user_id, 'city_selected')} {matches[0]}")
        await choose_action(update, context)
        return CHOOSE_ACTION
    else:
        user_data_store[user_id]["city_matches"] = matches
        user_data_store[user_id]["city_page"] = 1
        paginated, total = paginate_list(matches, 1)
        kb = []
        for c in paginated:
            kb.append([InlineKeyboardButton(c, callback_data=f"city_select_{c}")])
        if total > 1:
            kb.append([
                InlineKeyboardButton("⬅️", callback_data="city_page_0"),
                InlineKeyboardButton("➡️", callback_data="city_page_2")
            ])
        await update.message.reply_text(
            f"Multiple cities found (1/{total}):",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )
        return CHOOSE_CITY

async def city_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    data = query.data

    if data.startswith("city_select_"):
        city = data.replace("city_select_", "")
        user_data_store[user_id]["city"] = city
        await query.edit_message_text(f"{get_text(user_id, 'city_selected')} {city}")
        await choose_action(update, context)
        return CHOOSE_ACTION

    elif data.startswith("city_page_"):
        page_str = data.replace("city_page_", "")
        try:
            page_num = int(page_str)
            if page_num < 1:
                page_num = 1
        except ValueError:
            page_num = 1

        matches = user_data_store[user_id].get("city_matches", [])
        paginated, total = paginate_list(matches, page_num)
        kb = []
        for c in paginated:
            kb.append([InlineKeyboardButton(c, callback_data=f"city_select_{c}")])
        nav_row = []
        if page_num > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"city_page_{page_num - 1}"))
        if page_num < total:
            nav_row.append(InlineKeyboardButton("➡️", callback_data=f"city_page_{page_num + 1}"))
        if nav_row:
            kb.append(nav_row)

        await query.edit_message_text(
            f"Multiple cities found ({page_num}/{total}):",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )
        user_data_store[user_id]["city_page"] = page_num
        return CHOOSE_CITY
    else:
        await query.edit_message_text(get_text(user_id, "invalid_choice"))
        return ConversationHandler.END

async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(get_text(user_id, "advertise_btn"), callback_data='advertise'),
            InlineKeyboardButton(get_text(user_id, "find_btn"), callback_data='find_people')
        ]
    ])
    if update.callback_query:
        await update.callback_query.message.reply_text(get_text(user_id, "choose_action"), reply_markup=kb)
    else:
        await update.message.reply_text(get_text(user_id, "choose_action"), reply_markup=kb)
    return CHOOSE_ACTION

async def action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    choice = query.data

    if choice == 'advertise':
        # Suppose we move to CHOOSE_WALLET_TYPE in the same conversation
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(get_text(user_id, "sol_wallet"), callback_data='SOL'),
                InlineKeyboardButton(get_text(user_id, "btc_wallet"), callback_data='BTC')
            ]
        ])
        await query.edit_message_text(get_text(user_id, "choose_wallet"), reply_markup=kb)
        return CHOOSE_WALLET_TYPE

    elif choice == 'find_people':
        await query.edit_message_text(get_text(user_id, "find_dev"), parse_mode=ParseMode.HTML)
        return END
    else:
        await query.edit_message_text(get_text(user_id, "invalid_choice"))
        return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    user_id = update.effective_user.id
    from telegram import ReplyKeyboardRemove
    await update.message.reply_text(get_text(user_id, "cancel_msg"), reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def get_start_conv_handler():
    """Build and return the ConversationHandler for the /start flow."""
    return ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            SELECT_LANG: [
                CallbackQueryHandler(select_lang_callback, pattern='^lang_')
            ],
            CHOOSE_COUNTRY: [
                CallbackQueryHandler(country_callback, pattern='^(country_select_|country_page_)'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_country)
            ],
            SHOW_DISCLAIMER: [
                CallbackQueryHandler(disclaimer_callback, pattern='^(agree|disagree)$')
            ],
            CHOOSE_CITY: [
                CallbackQueryHandler(city_callback, pattern='^(city_select_|city_page_)'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_city)
            ],
            CHOOSE_ACTION: [
                CallbackQueryHandler(action_callback, pattern='^(advertise|find_people)$')
            ],
            # CHOOSE_WALLET_TYPE, NAME_WALLET handled possibly in the same conversation, or you can do it in wallet.py
        },
        fallbacks=[CommandHandler('cancel', cancel_command)],
        allow_reentry=True
    )
