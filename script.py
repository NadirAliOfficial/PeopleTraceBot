import logging
import os
import math
import pycountry
import json
from solders.keypair import Keypair
from solana.rpc.api import Client
from solders.pubkey import Pubkey
import base58
import geonamescache
import nest_asyncio
from telegram import (
    Update,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

nest_asyncio.apply()

SOLANA_NETWORK = "https://api.devnet.solana.com"
client = Client(SOLANA_NETWORK)
WALLETS_DIR = 'wallets'

LANG_DATA = {
    "en": {
        "lang_choice": "English",
        "lang_button": "English",
        "start_msg": "Hello! Welcome to People Finder Bot.\nPlease select your language:",
        "choose_country": "Please enter your country name (partial name allowed):",
        "country_not_found": "No matching countries found. Please try again:",
        "country_multi": "Multiple countries found (Page {page} of {total}):",
        "country_selected": "You have selected",
        "disclaimer_title": "<b>Disclaimer</b>\n\n",
        "disclaimer_text": (
            "1. All bounties are held in escrow.\n"
            "2. AI-generated fake content is prohibited.\n"
            "3. For lawful, ethical use only.\n"
            "4. Report to authorities first when locating someone.\n"
            "5. We are not liable for misuse.\n"
            "6. Community-driven approach; verify carefully.\n"
            "7. We do not handle reward disputes.\n\n"
            "By using this bot, you agree to these terms."
        ),
        "agree_btn": "I Agree ✅",
        "disagree_btn": "I Disagree ❌",
        "disagree_end": "You did not agree. Conversation ended.",
        "enter_city": "Please enter your city name (partial name allowed):",
        "city_not_found": "No matching cities found. Please try again:",
        "city_multi": "Multiple cities found (Page {page} of {total}):",
        "city_selected": "City recorded:",
        "choose_action": "Would you like to Advertise or Find People?",
        "advertise_btn": "Advertise 📢",
        "find_btn": "Find People 👥",
        "find_dev": "Find People is under development.",
        "choose_wallet": "Please choose the type of wallet:",
        "sol_wallet": "Solana (SOL)",
        "btc_wallet": "Bitcoin (BTC)",
        "btc_dev": "BTC wallet creation is under development.",
        "wallet_name_prompt": "You've chosen Solana wallet.\nPlease enter a name for your wallet:",
        "wallet_name_empty": "Wallet name cannot be empty. Please try again:",
        "wallet_create_ok": "✅ Wallet Created Successfully!\n\n",
        "wallet_create_err": "❌ Error creating wallet.",
        "cancel_msg": "Operation cancelled. Use /start to begin again.",
        "invalid_choice": "Invalid choice. Conversation ended.",
    },
    "zh": {
        "lang_choice": "中文",
        "lang_button": "中文",
        "start_msg": "你好！欢迎使用 People Finder 机器人。\n请选择语言：",
        "choose_country": "请输入您的国家名称（支持模糊搜索）：",
        "country_not_found": "未找到匹配的国家。请重试：",
        "country_multi": "找到多个国家 (第 {page} 页，共 {total} 页)：",
        "country_selected": "您已选择",
        "disclaimer_title": "<b>免责声明</b>\n\n",
        "disclaimer_text": (
            "1. 所有悬赏由平台托管。\n"
            "2. 严禁使用 AI 虚假内容。\n"
            "3. 仅限合法合规使用。\n"
            "4. 寻人应先向当地警方或政府部门报备。\n"
            "5. 平台对任何滥用不承担责任。\n"
            "6. 社区互助，需自行核实。\n"
            "7. 平台不介入赏金纠纷。\n\n"
            "使用本机器人即表示您同意上述条款。"
        ),
        "agree_btn": "同意 ✅",
        "disagree_btn": "不同意 ❌",
        "disagree_end": "您不同意，结束对话。",
        "enter_city": "请输入您的城市名称（支持模糊搜索）：",
        "city_not_found": "未找到匹配的城市。请重试：",
        "city_multi": "找到多个城市 (第 {page} 页，共 {total} 页)：",
        "city_selected": "已记录城市：",
        "choose_action": "请选择：发布悬赏或寻找信息？",
        "advertise_btn": "发布悬赏 📢",
        "find_btn": "寻找信息 👥",
        "find_dev": "寻找信息功能正在开发中。",
        "choose_wallet": "请选择要创建的钱包类型：",
        "sol_wallet": "Solana (SOL)",
        "btc_wallet": "比特币 (BTC)",
        "btc_dev": "BTC 钱包功能正在开发中。",
        "wallet_name_prompt": "您选择了 Solana 钱包。\n请输入钱包名称：",
        "wallet_name_empty": "钱包名称不能为空，请重新输入：",
        "wallet_create_ok": "✅ 成功创建钱包！\n\n",
        "wallet_create_err": "❌ 创建钱包时出错。",
        "cancel_msg": "操作已取消。输入 /start 重新开始。",
        "invalid_choice": "无效选择，结束对话。",
    }
}

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
user_data_store = {}
ITEMS_PER_PAGE = 10

def create_sol_wallet(wallet_name):
    try:
        # Generate keypair
        keypair = Keypair()
        public_key = str(keypair.pubkey())
        secret_key = base58.b58encode(bytes(keypair.to_bytes_array())).decode('utf-8')

        # Prepare wallet data
        wallet = {
            "name": wallet_name,
            "public_key": public_key,
            "secret_key": secret_key
        }

        # Ensure wallets folder exists
        if not os.path.exists(WALLETS_DIR):
            os.makedirs(WALLETS_DIR)

        # Save wallet file
        wallet_filename = os.path.join(WALLETS_DIR, f"{public_key}.json")
        with open(wallet_filename, "w") as f:
            json.dump(wallet, f, indent=4)

        # Fetch balance from devnet/mainnet
        balance_response = client.get_balance(Pubkey.from_string(public_key))
        balance_lamports = balance_response.value  # <--- Use the .value attribute
        balance_sol = balance_lamports / 1e9

        # Return final wallet details
        wallet["balance_sol"] = balance_sol
        return wallet

    except Exception as e:
        logger.error(f"Error saving wallet: {e}", exc_info=True)
        return None


def get_text(user_id, key):
    lang = user_data_store.get(user_id, {}).get("lang", "en")
    return LANG_DATA[lang].get(key, "")

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

def paginate_list(items, page, items_per_page=ITEMS_PER_PAGE):
    total_pages = math.ceil(len(items) / items_per_page) if items else 1
    page = max(1, min(page, total_pages))
    start = (page - 1) * items_per_page
    end = start + items_per_page
    return items[start:end], total_pages

def generate_pagination_buttons(current_page, total_pages, prefix):
    btns = []
    if current_page > 1:
        btns.append(InlineKeyboardButton("⬅️", callback_data=f"{prefix}_page_{current_page - 1}"))
    if current_page < total_pages:
        btns.append(InlineKeyboardButton("➡️", callback_data=f"{prefix}_page_{current_page + 1}"))
    return btns

def generate_country_buttons(countries, current_page, total_pages):
    rows = [[InlineKeyboardButton(c, callback_data=f"country_select_{c}")] for c in countries]
    pagination = generate_pagination_buttons(current_page, total_pages, "country")
    if pagination:
        rows.append(pagination)
    return InlineKeyboardMarkup(rows)

def generate_city_buttons(cities, current_page, total_pages):
    rows = [[InlineKeyboardButton(c, callback_data=f"city_select_{c}")] for c in cities]
    pagination = generate_pagination_buttons(current_page, total_pages, "city")
    if pagination:
        rows.append(pagination)
    return InlineKeyboardMarkup(rows)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    btns = [
        [
            InlineKeyboardButton(LANG_DATA["en"]["lang_button"], callback_data='lang_en'),
            InlineKeyboardButton(LANG_DATA["zh"]["lang_button"], callback_data='lang_zh')
        ]
    ]
    await update.message.reply_text(
        f"{LANG_DATA['en']['start_msg']}\n\n"
        f"{LANG_DATA['zh']['start_msg']}",
        reply_markup=InlineKeyboardMarkup(btns),
        parse_mode=ParseMode.HTML
    )
    return SELECT_LANG

async def select_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
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
        await update.message.reply_text(get_text(user_id, "country_not_found"), parse_mode=ParseMode.HTML)
        return CHOOSE_COUNTRY
    if len(matches) == 1:
        user_data_store[user_id]["country"] = matches[0]
        await show_disclaimer(update, context)
        return SHOW_DISCLAIMER
    else:
        user_data_store[user_id]["country_matches"] = matches
        user_data_store[user_id]["country_page"] = 1
        paginated, total = paginate_list(matches, 1)
        kb = generate_country_buttons(paginated, 1, total)
        await update.message.reply_text(
            get_text(user_id, "country_multi").format(page=1, total=total),
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )
        return CHOOSE_COUNTRY

async def country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    if data.startswith("country_select_"):
        country = data.replace("country_select_", "")
        user_data_store[user_id]["country"] = country
        await query.edit_message_text(
            f"{get_text(user_id, 'country_selected')} {country}.",
            parse_mode=ParseMode.HTML
        )
        await show_disclaimer(update, context)
        return SHOW_DISCLAIMER
    elif data.startswith("country_page_"):
        page_num = int(data.replace("country_page_", ""))
        matches = user_data_store[user_id].get("country_matches", [])
        paginated, total = paginate_list(matches, page_num)
        kb = generate_country_buttons(paginated, page_num, total)
        await query.edit_message_text(
            get_text(user_id, "country_multi").format(page=page_num, total=total),
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )
        user_data_store[user_id]["country_page"] = page_num
        return CHOOSE_COUNTRY
    else:
        await query.edit_message_text(get_text(user_id, "invalid_choice"), parse_mode=ParseMode.HTML)
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
    await query.answer()
    user_id = query.from_user.id
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
        await update.message.reply_text(
            get_text(user_id, "invalid_choice"),
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END
    matches = get_city_matches(country, city_input)
    if not matches:
        await update.message.reply_text(get_text(user_id, "city_not_found"), parse_mode=ParseMode.HTML)
        return CHOOSE_CITY
    if len(matches) == 1:
        user_data_store[user_id]["city"] = matches[0]
        await update.message.reply_text(
            f"{get_text(user_id, 'city_selected')} {matches[0]}",
            parse_mode=ParseMode.HTML
        )
        await choose_action(update, context)
        return CHOOSE_ACTION
    else:
        user_data_store[user_id]["city_matches"] = matches
        user_data_store[user_id]["city_page"] = 1
        paginated, total = paginate_list(matches, 1)
        kb = generate_city_buttons(paginated, 1, total)
        await update.message.reply_text(
            get_text(user_id, "city_multi").format(page=1, total=total),
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )
        return CHOOSE_CITY

async def city_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    if data.startswith("city_select_"):
        city = data.replace("city_select_", "")
        user_data_store[user_id]["city"] = city
        await query.edit_message_text(
            f"{get_text(user_id, 'city_selected')} {city}",
            parse_mode=ParseMode.HTML
        )
        await choose_action(update, context)
        return CHOOSE_ACTION
    elif data.startswith("city_page_"):
        page_num = int(data.replace("city_page_", ""))
        matches = user_data_store[user_id].get("city_matches", [])
        paginated, total = paginate_list(matches, page_num)
        kb = generate_city_buttons(paginated, page_num, total)
        await query.edit_message_text(
            get_text(user_id, "city_multi").format(page=page_num, total=total),
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )
        user_data_store[user_id]["city_page"] = page_num
        return CHOOSE_CITY
    else:
        await query.edit_message_text(get_text(user_id, "invalid_choice"), parse_mode=ParseMode.HTML)
        return ConversationHandler.END

async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(get_text(user_id, "advertise_btn"), callback_data='advertise'),
        InlineKeyboardButton(get_text(user_id, "find_btn"), callback_data='find_people')
    ]])
    if update.callback_query:
        await update.callback_query.message.reply_text(get_text(user_id, "choose_action"), reply_markup=kb)
    else:
        await update.message.reply_text(get_text(user_id, "choose_action"), reply_markup=kb)
    return CHOOSE_ACTION

async def action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    choice = query.data
    if choice == 'advertise':
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(get_text(user_id, "sol_wallet"), callback_data='SOL'),
            InlineKeyboardButton(get_text(user_id, "btc_wallet"), callback_data='BTC')
        ]])
        await query.edit_message_text(get_text(user_id, "choose_wallet"), reply_markup=kb)
        return CHOOSE_WALLET_TYPE
    elif choice == 'find_people':
        await query.edit_message_text(get_text(user_id, "find_dev"), parse_mode=ParseMode.HTML)
        return END
    else:
        await query.edit_message_text(get_text(user_id, "invalid_choice"), parse_mode=ParseMode.HTML)
        return ConversationHandler.END

async def wallet_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == 'SOL':
        await query.edit_message_text(get_text(user_id, "wallet_name_prompt"), parse_mode=ParseMode.HTML)
        return NAME_WALLET
    elif query.data == 'BTC':
        await query.edit_message_text(get_text(user_id, "btc_dev"), parse_mode=ParseMode.HTML)
        return END
    else:
        await query.edit_message_text(get_text(user_id, "invalid_choice"), parse_mode=ParseMode.HTML)
        return ConversationHandler.END

async def wallet_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    wallet_name = update.message.text.strip()
    if not wallet_name:
        await update.message.reply_text(get_text(user_id, "wallet_name_empty"), parse_mode=ParseMode.HTML)
        return NAME_WALLET
    wallet_details = create_sol_wallet(wallet_name)
    if wallet_details:
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
    return END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, "cancel_msg"), reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        user_id = update.effective_user.id
        await update.effective_message.reply_text(get_text(user_id, "invalid_choice"))

def main():
    TOKEN = "7333467475:AAE-S2Hom4XZI_sfyCbrFrLkmXy6aQpL_GI"
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found.")
        return
    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
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
            CHOOSE_WALLET_TYPE: [
                CallbackQueryHandler(wallet_type_callback, pattern='^(SOL|BTC)$')
            ],
            NAME_WALLET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_name_handler)
            ],
            END: [
                CommandHandler('start', start)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
