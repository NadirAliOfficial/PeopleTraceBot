# config.py
import logging
import os
import json
import base58

# If you have them installed:
try:
    from solders.keypair import Keypair
    from solana.rpc.api import Client
    from solders.pubkey import Pubkey

    # Example using Solana Devnet
    SOLANA_NETWORK = "https://api.devnet.solana.com"
    client = Client(SOLANA_NETWORK)
except ImportError:
    client = None  # fallback if solana libs aren't installed

# ========== LOGGER SETUP ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== GLOBAL DATA ==========
user_data_store = {}
WALLETS_DIR = 'wallets'

# ========== LANGUAGE DATA ==========
LANG_DATA = {
    "en": {
        "lang_button": "English",
        "start_msg": "Hello! Welcome to the Bot.\nPlease select your language:",
        "lang_updated": "Language updated.",
        "wallet_name_prompt": "Enter a name for your new Solana wallet:",
        "wallet_name_empty": "Wallet name cannot be empty. Try again:",
        "wallet_create_ok": "✅ Wallet Created Successfully!\n\n",
        "wallet_create_err": "❌ Error creating wallet.",
        "invalid_choice": "Invalid choice or command.",
        "cancel_msg": "Operation cancelled. Use /start to begin again.",
        "choose_lang": "Please choose your language:",
        "btn_refresh": "🔄 Refresh",
        "btn_sol": "Create SOL",
        "btn_btc": "Create BTC",
        "btn_show_address": "Show Address",
        "btn_delete_wallet": "Delete Wallet",
        "menu_wallet_title": "Wallet Menu",
        "wallet_no_exists": "No wallet found. Please create a wallet first.",
        "wallet_deleted": "✅ Wallet deleted successfully.",
        "wallet_not_deleted": "No wallet to delete.",
        "wallet_refreshed": "Balance updated:\nName: {name}\nPublic Key: {pub}\nBalance: {bal} SOL",
        "wallet_exists": "Your wallet:\nName: {name}\nPublic Key: {pub}\nBalance: {bal} SOL",
        "sol_wallet_created": (
            "<b>Name:</b> {name}\n"
            "<b>Public Key:</b> {pub}\n"
            "<b>Secret Key:</b> {secret}\n"
            "<b>Balance:</b> {bal} SOL\n"
            "<b>User ID:</b> {user_id}\n"
        ),
    },
    "zh": {
        "lang_button": "中文",
        "start_msg": "你好！歡迎使用機器人。\n請選擇您的語言：",
        "lang_updated": "語言已更新。",
        "wallet_name_prompt": "請輸入新的 Solana 錢包名稱：",
        "wallet_name_empty": "錢包名稱不能為空，請重試：",
        "wallet_create_ok": "✅ 錢包創建成功！\n\n",
        "wallet_create_err": "❌ 創建錢包時出錯。",
        "invalid_choice": "無效的選擇或命令。",
        "cancel_msg": "操作已取消。如需重新開始，請使用 /start。",
        "choose_lang": "請選擇您的語言：",
        "btn_refresh": "🔄 刷新餘額",
        "btn_sol": "創建 SOL",
        "btn_btc": "創建 BTC",
        "btn_show_address": "顯示地址",
        "btn_delete_wallet": "刪除錢包",
        "menu_wallet_title": "錢包菜單",
        "wallet_no_exists": "尚未創建錢包。",
        "wallet_deleted": "✅ 已成功刪除錢包。",
        "wallet_not_deleted": "沒有錢包可刪除。",
        "wallet_refreshed": "餘額已更新:\n名稱: {name}\n公鑰: {pub}\n餘額: {bal} SOL",
        "wallet_exists": "您的錢包:\n名稱: {name}\n公鑰: {pub}\n餘額: {bal} SOL",
        "sol_wallet_created": (
            "<b>名稱:</b> {name}\n"
            "<b>公鑰:</b> {pub}\n"
            "<b>私鑰:</b> {secret}\n"
            "<b>餘額:</b> {bal} SOL\n"
            "<b>用戶ID:</b> {user_id}\n"
        ),
    }
}

# ========== HELPER FUNCTIONS ==========
def get_text(user_id, key):
    """
    Safely get localized text from LANG_DATA for a given user and key.
    If the user isn't in user_data_store or no 'lang', fallback to 'en'.
    """
    if user_id not in user_data_store:
        user_data_store[user_id] = {}  # auto-init to avoid KeyError
    user_lang = user_data_store[user_id].get("lang", "en")
    return LANG_DATA.get(user_lang, LANG_DATA["en"]).get(key, f"[Missing text for '{key}']")

def create_sol_wallet(user_id, wallet_name):
    """
    Create a Solana wallet, store in a JSON file, and return the dict.
    Adds 'user_id' in the wallet JSON.
    """
    if not client:
        return None  # if solana libs not installed
    from pathlib import Path
    Path(WALLETS_DIR).mkdir(exist_ok=True)

    try:
        keypair = Keypair()
        public_key = str(keypair.pubkey())
        secret_key = base58.b58encode(bytes(keypair.to_bytes_array())).decode('utf-8')

        # Get initial balance (0 if new)
        balance_resp = client.get_balance(Pubkey.from_string(public_key))
        lamports = balance_resp.value if balance_resp else 0
        balance_sol = lamports / 1e9

        wallet = {
            "user_id": user_id,          # store user_id
            "name": wallet_name,
            "public_key": public_key,
            "secret_key": secret_key,
            "balance_sol": balance_sol
        }

        # Save to disk
        filename = os.path.join(WALLETS_DIR, f"{public_key}.json")
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(wallet, f, ensure_ascii=False, indent=4)

        return wallet
    except Exception as e:
        logger.error("Error creating wallet: %s", e, exc_info=True)
        return None

def load_user_wallet(user_id):
    """
    Return the user's wallet from memory (refresh balance if possible).
    """
    if user_id not in user_data_store:
        user_data_store[user_id] = {}
        return None
    w = user_data_store[user_id].get("wallet")
    if not w:
        return None
    # Refresh balance if we can
    if client and w.get("public_key"):
        resp = client.get_balance(Pubkey.from_string(w["public_key"]))
        lamports = resp.value if resp else 0
        w["balance_sol"] = lamports / 1e9
    return w

def delete_user_wallet(user_id):
    """
    Delete the user's wallet from memory and remove .json file if present.
    """
    if user_id not in user_data_store or "wallet" not in user_data_store[user_id]:
        return False
    wallet = user_data_store[user_id]["wallet"]
    if not wallet:
        return False

    pubkey = wallet.get("public_key")
    if pubkey:
        filename = os.path.join(WALLETS_DIR, f"{pubkey}.json")
        if os.path.exists(filename):
            os.remove(filename)

    user_data_store[user_id]["wallet"] = None
    return True
