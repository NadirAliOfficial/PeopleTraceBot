# PeopleTrace Bot

A Telegram bot to help locate missing persons by collecting and sharing information across communities.

## Description
PeopleTrace Bot is a Telegram bot that allows users to report and search for missing persons, submit photos and details, and lets admins review and verify the information. It manages user interactions through conversation handlers for start, wallet management, and settings.

## Features
- Report and search missing persons
- Photo and detail submissions via Telegram
- Admin review and verification

## Requirements
```
python-telegram-bot>=20.0
```
You can also install the additional dependencies listed in `requiremtns.txt`:
```
pip install -r requiremtns.txt
```

## Setup
```python
BOT_TOKEN = "your_telegram_bot_token"
```

## Usage
```bash
python main.py
```

## Project Structure
```
LICENSE
README.md
config.py
main.py
requiremtns.txt
script.py
settings.py
start.py
wallet.py
wallets/
```

## License
MIT
<!-- updated: 2025-12-07-r01 -->
