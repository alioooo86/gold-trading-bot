#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import requests
import time
from datetime import datetime, timedelta
import threading
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def install_dependencies():
    deps = ['requests', 'pyTelegramBotAPI', 'gspread', 'google-auth']
    for dep in deps:
        try:
            __import__(dep.replace('-', '_').lower())
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
    return True

install_dependencies()

import telebot
from telebot import types
import gspread
from google.oauth2.service_account import Credentials

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOLDAPI_KEY = os.getenv("GOLDAPI_KEY")

GOOGLE_CREDENTIALS = {
    "type": "service_account",
    "project_id": os.getenv("GOOGLE_PROJECT_ID"),
    "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("GOOGLE_PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('GOOGLE_CLIENT_EMAIL').replace('@', '%40')}"
}

TROY_OUNCE_TO_GRAMS = 31.1035
USD_TO_AED_RATE = 3.674

PURITY_MULTIPLIERS = {
    999: 0.118122, 995: 0.117649, 916: 0.108308, 875: 0.103460, 
    750: 0.088680, 990: 0.117058, "custom": 0.118122
}

DEALERS = {
    "2268": {"name": "Ahmadreza", "level": "admin", "active": True, "permissions": ["buy", "sell", "admin"]},
    "2269": {"name": "Nima", "level": "senior", "active": True, "permissions": ["buy", "sell"]},
    "2270": {"name": "Peiman", "level": "standard", "active": True, "permissions": ["buy"]},
    "9999": {"name": "System Admin", "level": "admin", "active": True, "permissions": ["buy", "sell", "admin"]},
    "7777": {"name": "Junior Dealer", "level": "junior", "active": True, "permissions": ["buy"]}
}

CUSTOMERS = ["Noori", "ASK", "AGM", "Keshavarz", "WSG", "Exness", "MyMaa", "Binance", "Kraken", "Custom"]

user_sessions = {}
market_data = {"gold_usd_oz": 2650.0, "last_update": "00:00:00", "trend": "stable", "change_24h": 0.0}

def safe_float(value, default=0.0):
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def format_money(amount, currency="$"):
    try:
        amount = safe_float(amount)
        return f"{currency}{amount:,.2f}" if amount >= 0 else f"-{currency}{abs(amount):,.2f}"
    except:
        return f"{currency}0.00"

def format_money_aed(amount_usd):
    try:
        amount_aed = safe_float(amount_usd) * USD_TO_AED_RATE
        return f"AED {amount_aed:,.2f}" if amount_aed >= 0 else f"-AED {abs(amount_aed):,.2f}"
    except:
        return "AED 0.00"

def fetch_gold_rate():
    try:
        headers = {'x-access-token': GOLDAPI_KEY}
        response = requests.get('https://www.goldapi.io/api/XAU/USD', headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            new_rate = safe_float(data.get('price', 2650))
            if 1000 <= new_rate <= 10000:
                old_rate = market_data['gold_usd_oz']
                change = new_rate - old_rate
                market_data.update({
                    "gold_usd_oz": round(new_rate, 2),
                    "last_update": datetime.now().strftime('%H:%M:%S'),
                    "trend": "up" if change > 0 else "down" if change < 0 else "stable",
                    "change_24h": round(change, 2)
                })
                logger.info(f"Gold rate updated: ${new_rate:.2f}/oz")
                return True
    except Exception as e:
        logger.error(f"Rate fetch error: {e}")
    return False

def start_rate_updater():
    def update_loop():
        while True:
            try:
                fetch_gold_rate()
                time.sleep(900)
            except Exception as e:
                logger.error(f"Rate updater error: {e}")
                time.sleep(600)
    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()
    logger.info("Background rate updater started")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start_command(message):
    try:
        user_id = message.from_user.id
        if user_id in user_sessions:
            del user_sessions[user_id]
        
        fetch_gold_rate()
        markup = types.InlineKeyboardMarkup()
        level_emojis = {"admin": "👑", "senior": "⭐", "standard": "🔹", "junior": "🔸"}
        
        for dealer_id, dealer in DEALERS.items():
            if dealer.get('active', True):
                emoji = level_emojis.get(dealer['level'], "👤")
                markup.add(types.InlineKeyboardButton(
                    f"{emoji} {dealer['name']} ({dealer['level'].title()})",
                    callback_data=f"login_{dealer_id}"
                ))
        
        markup.add(types.InlineKeyboardButton("💰 Live Gold Rate", callback_data="show_rate"))
        
        welcome_text = f"""🥇 GOLD TRADING BOT v4.1 - RAILWAY CLOUD! ✨
🚀 Running 24/7 on Cloud Platform!

💰 Gold Rate: {format_money(market_data['gold_usd_oz'])} USD/oz
💱 AED Rate: {format_money_aed(market_data['gold_usd_oz'])}/oz
📈 Trend: {market_data['trend'].title()}
☁️ Cloud: Always Online

🔒 SELECT DEALER TO LOGIN:"""
        
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
        logger.info(f"User {user_id} started bot")
        
    except Exception as e:
        logger.error(f"Start error: {e}")
        bot.send_message(message.chat.id, "❌ Error occurred. Please try again.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    try:
        user_id = call.from_user.id
        data = call.data
        
        if data.startswith('login_'):
            dealer_id = data.replace("login_", "")
            dealer = DEALERS.get(dealer_id)
            
            if dealer:
                user_sessions[user_id] = {"step": "awaiting_pin", "temp_dealer_id": dealer_id, "temp_dealer": dealer}
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="start"))
                
                bot.edit_message_text(
                    f"""🔒 DEALER AUTHENTICATION
Selected: {dealer['name']} ({dealer['level'].title()})
🔐 PIN: {dealer_id}
💬 Send this PIN as a message""",
                    call.message.chat.id, call.message.message_id, reply_markup=markup
                )
        
        elif data == 'show_rate':
            rate_text = f"""💰 LIVE GOLD RATE
🥇 Current: {format_money(market_data['gold_usd_oz'])} USD/oz
💱 AED: {format_money_aed(market_data['gold_usd_oz'])}/oz
📈 Trend: {market_data['trend'].title()}
⏰ Updated: {market_data['last_update']}"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="show_rate"))
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="start"))
            
            bot.edit_message_text(rate_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Callback error: {e}")
        bot.answer_callback_query(call.id, f"Error: {str(e)}")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    try:
        user_id = message.from_user.id
        text = message.text.strip()
        
        if user_id not in user_sessions:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🚀 START", callback_data="start"))
            bot.send_message(message.chat.id, "Please use /start", reply_markup=markup)
            return
        
        session_data = user_sessions[user_id]
        
        if session_data.get("step") == "awaiting_pin":
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except:
                pass
            
            if text == session_data["temp_dealer_id"]:
                dealer = session_data["temp_dealer"]
                user_sessions[user_id] = {"step": "authenticated", "dealer": dealer}
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("💰 Live Rate", callback_data="show_rate"))
                
                bot.send_message(user_id, f"""✅ Welcome {dealer['name']}!
Gold Trading Bot v4.1 - Ready!
💰 Current Rate: {format_money(market_data['gold_usd_oz'])} USD/oz""", reply_markup=markup)
                logger.info(f"Login: {dealer['name']}")
            else:
                bot.send_message(user_id, "❌ Wrong PIN")
        
    except Exception as e:
        logger.error(f"Text error: {e}")

def main():
    try:
        logger.info("🥇 GOLD TRADING BOT v4.1 - RAILWAY CLOUD STARTING")
        fetch_gold_rate()
        start_rate_updater()
        logger.info(f"✅ Bot ready - Gold: {format_money(market_data['gold_usd_oz'])}")
        logger.info("🚀 Starting 24/7 operation...")
        
        while True:
            try:
                bot.infinity_polling(timeout=30, long_polling_timeout=30)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(10)
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        time.sleep(5)
        main()

if __name__ == '__main__':
    main()