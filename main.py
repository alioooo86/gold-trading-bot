#!/usr/bin/env python3
"""
🥇 GOLD TRADING BOT v4.9 - COMPLETE WITH TELEGRAM NOTIFICATIONS
✨ COMPLETE: All functions included - ready to run
✨ NEW: Telegram notification system
✨ NEW: Real-time approval alerts via Telegram
✨ WORKING: All handlers and functions included
🎨 Professional notification workflow with Telegram only
🚀 Ready to run on Railway with instant notifications!
"""

import os
import sys
import subprocess
import json
import requests
import time
import random
from datetime import datetime, timedelta, timezone
import threading
import logging

# Configure logging for cloud environment
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CLOUD-SAFE DEPENDENCY INSTALLER
# ============================================================================

def install_dependencies():
    """Install required dependencies for cloud deployment"""
    deps = ['requests', 'pyTelegramBotAPI', 'gspread', 'google-auth']
    
    logger.info("📦 Installing dependencies for cloud deployment...")
    for dep in deps:
        try:
            __import__(dep.replace('-', '_').lower())
            logger.info(f"✅ {dep:15} - Already available")
        except ImportError:
            logger.info(f"📦 {dep:15} - Installing...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep], 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info(f"✅ {dep:15} - Installed successfully")
            except Exception as e:
                logger.error(f"❌ {dep:15} - Installation failed: {e}")
                return False
    return True

if not install_dependencies():
    logger.error("❌ Dependency installation failed")
    sys.exit(1)

# Import after installation
try:
    import telebot
    from telebot import types
    import gspread
    from google.oauth2.service_account import Credentials
    logger.info("✅ All imports successful for cloud deployment!")
except ImportError as e:
    logger.error(f"❌ Import failed: {e}")
    sys.exit(1)

# ============================================================================
# ENVIRONMENT VARIABLES CONFIGURATION
# ============================================================================

def get_env_var(var_name, default=None, required=True):
    """Safely get environment variable"""
    value = os.getenv(var_name, default)
    if required and not value:
        logger.error(f"❌ Required environment variable {var_name} not found!")
        sys.exit(1)
    return value

# Get configuration from environment variables
TELEGRAM_BOT_TOKEN = get_env_var("TELEGRAM_BOT_TOKEN")
GOOGLE_SHEET_ID = get_env_var("GOOGLE_SHEET_ID")
GOLDAPI_KEY = get_env_var("GOLDAPI_KEY")

# TELEGRAM NOTIFICATION CONFIGURATION
APPROVER_TELEGRAM_IDS = {
    "1001": None,  # Abhay - Head Accountant
    "1002": None,  # Mushtaq - Level 2
    "1003": None   # Ahmadreza - Manager
}

# Google credentials from environment
GOOGLE_CREDENTIALS = {
    "type": "service_account",
    "project_id": get_env_var("GOOGLE_PROJECT_ID"),
    "private_key_id": get_env_var("GOOGLE_PRIVATE_KEY_ID"),
    "private_key": get_env_var("GOOGLE_PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": get_env_var("GOOGLE_CLIENT_EMAIL"),
    "client_id": get_env_var("GOOGLE_CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{get_env_var('GOOGLE_CLIENT_EMAIL').replace('@', '%40')}"
}

logger.info("✅ Environment variables loaded successfully")

# ============================================================================
# UAE TIMEZONE + CONSTANTS
# ============================================================================

# UAE Timezone (UTC+4)
UAE_TZ = timezone(timedelta(hours=4))

def get_uae_time():
    """Get current time in UAE timezone"""
    return datetime.now(UAE_TZ)

TROY_OUNCE_TO_GRAMS = 31.1035
USD_TO_AED_RATE = 3.674

# VERIFIED MULTIPLIERS (USD/Oz → AED/gram)
PURITY_MULTIPLIERS = {
    999: 0.118122, 995: 0.117649, 916: 0.108308,
    875: 0.103460, 750: 0.088680, 990: 0.117058,
    "custom": 0.118122
}

# ============================================================================
# ENHANCED DEALER SYSTEM
# ============================================================================

DEALERS = {
    "2268": {"name": "Ahmadreza", "level": "manager", "active": True, "permissions": ["buy", "sell", "admin", "approve_level_3"]},
    "2269": {"name": "Nima", "level": "senior", "active": True, "permissions": ["buy", "sell"]},
    "2270": {"name": "Peiman", "level": "standard", "active": True, "permissions": ["buy", "sell"]},
    "9999": {"name": "System Admin", "level": "admin", "active": True, "permissions": ["buy", "sell", "admin", "approve_level_3"]},
    "7777": {"name": "Junior Dealer", "level": "junior", "active": True, "permissions": ["buy", "sell"]},
    
    # ACCOUNTING APPROVAL HIERARCHY WITH TELEGRAM NOTIFICATIONS
    "1001": {"name": "Abhay", "level": "head_accountant", "active": True, "permissions": ["approve_level_1", "view_pending"], "title": "Head Accountant"},
    "1002": {"name": "Mushtaq", "level": "approver_2", "active": True, "permissions": ["approve_level_2", "view_pending"], "title": "Level 2 Approver"},
    "1003": {"name": "Ahmadreza", "level": "manager", "active": True, "permissions": ["approve_level_3", "view_pending", "admin", "buy", "sell"], "title": "Manager"}
}

CUSTOMERS = ["Noori", "ASK", "AGM", "Keshavarz", "WSG", "Exness", "MyMaa", "Binance", "Kraken", "Custom"]

# PROFESSIONAL BAR TYPES
GOLD_TYPES = [
    {"name": "Kilo Bar", "code": "KB", "weight_grams": 1000.0},
    {"name": "TT Bar (10 Tola)", "code": "TT", "weight_grams": 116.6380},
    {"name": "100g Bar", "code": "100g", "weight_grams": 100.0},
    {"name": "Tola", "code": "TOLA", "weight_grams": 11.6638},
    {"name": "1g Bar", "code": "1g", "weight_grams": 1.0},
    {"name": "Custom", "code": "CUSTOM", "weight_grams": None}
]

# VERIFIED PURITY OPTIONS
GOLD_PURITIES = [
    {"name": "999 (99.9% Pure Gold)", "value": 999, "multiplier": 0.118122},
    {"name": "995 (99.5% Pure Gold)", "value": 995, "multiplier": 0.117649},
    {"name": "916 (22K Jewelry)", "value": 916, "multiplier": 0.108308},
    {"name": "875 (21K Jewelry)", "value": 875, "multiplier": 0.103460},
    {"name": "750 (18K Jewelry)", "value": 750, "multiplier": 0.088680},
    {"name": "990 (99.0% Pure Gold)", "value": 990, "multiplier": 0.117058},
    {"name": "Custom", "value": "custom", "multiplier": 0.118122}
]

VOLUME_PRESETS = [0.1, 0.5, 1, 2, 3, 5, 10, 15, 20, 25, 30, 50, 75, 100]
PREMIUM_AMOUNTS = [0, 1, 2, 3, 4, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200]
DISCOUNT_AMOUNTS = [0, 1, 2, 3, 4, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200]

# ============================================================================
# APPROVAL WORKFLOW SYSTEM
# ============================================================================

APPROVAL_STATUS = {
    "PENDING": {"color": {"red": 1.0, "green": 0.8, "blue": 0.8}, "text_color": {"red": 0.8, "green": 0.0, "blue": 0.0}, "level": 0},
    "LEVEL_1_APPROVED": {"color": {"red": 1.0, "green": 1.0, "blue": 0.8}, "text_color": {"red": 0.8, "green": 0.6, "blue": 0.0}, "level": 1},
    "LEVEL_2_APPROVED": {"color": {"red": 1.0, "green": 0.9, "blue": 0.6}, "text_color": {"red": 0.8, "green": 0.4, "blue": 0.0}, "level": 2},
    "FINAL_APPROVED": {"color": {"red": 0.8, "green": 1.0, "blue": 0.8}, "text_color": {"red": 0.0, "green": 0.6, "blue": 0.0}, "level": 3},
    "REJECTED": {"color": {"red": 0.9, "green": 0.6, "blue": 0.6}, "text_color": {"red": 0.6, "green": 0.0, "blue": 0.0}, "level": -1}
}

# Global state
user_sessions = {}
market_data = {
    "gold_usd_oz": 2650.0, 
    "last_update": "00:00:00", 
    "trend": "stable", 
    "change_24h": 0.0,
    "source": "initial"
}
fallback_trades = []

# ============================================================================
# TELEGRAM NOTIFICATION FUNCTIONS
# ============================================================================

def register_approver_telegram_id(approver_id, telegram_id):
    """Register approver's Telegram ID when they first login"""
    global APPROVER_TELEGRAM_IDS
    APPROVER_TELEGRAM_IDS[approver_id] = telegram_id
    approver_name = DEALERS.get(approver_id, {}).get('name', 'Unknown')
    logger.info(f"✅ Registered Telegram ID for {approver_name}: {telegram_id}")

def send_telegram_notification(telegram_id, message):
    """Send Telegram notification to specific user"""
    try:
        if telegram_id and bot:
            bot.send_message(telegram_id, message, parse_mode='HTML')
            return True
    except Exception as e:
        logger.error(f"❌ Telegram notification failed: {e}")
    return False

def notify_new_trade_approval_needed(trade_info, approver_id):
    """Notify specific approver that a trade needs their approval"""
    try:
        telegram_id = APPROVER_TELEGRAM_IDS.get(approver_id)
        if not telegram_id:
            logger.warning(f"⚠️ No Telegram ID registered for approver {approver_id}")
            return False
        
        approver_name = DEALERS.get(approver_id, {}).get('name', 'Unknown')
        approver_title = DEALERS.get(approver_id, {}).get('title', 'Approver')
        
        message = f"""🔔 <b>NEW TRADE APPROVAL REQUIRED</b>

👤 Hello <b>{approver_name}</b> ({approver_title}),

📊 <b>TRADE DETAILS:</b>
• <b>Operation:</b> {trade_info.get('operation', 'N/A')}
• <b>Customer:</b> {trade_info.get('customer', 'N/A')}
• <b>Gold Type:</b> {trade_info.get('gold_type', 'N/A')}
• <b>Volume:</b> {trade_info.get('volume_kg', 'N/A')}
• <b>Amount:</b> {trade_info.get('price_aed', 'N/A')}
• <b>Dealer:</b> {trade_info.get('dealer', 'N/A')}

⏰ <b>Time:</b> {get_uae_time().strftime('%Y-%m-%d %H:%M:%S')} UAE

🎯 <b>ACTION NEEDED:</b> Please review and approve this trade in the Gold Trading Bot.

💡 Use /start to access the Approval Dashboard."""
        
        success = send_telegram_notification(telegram_id, message)
        if success:
            logger.info(f"✅ Notified {approver_name} about new trade")
        return success
        
    except Exception as e:
        logger.error(f"❌ New trade notification error: {e}")
        return False

def notify_approval_completed(trade_info, approver_name, next_approver_id=None):
    """Notify next approver when previous approval is completed"""
    try:
        if not next_approver_id:
            return
            
        telegram_id = APPROVER_TELEGRAM_IDS.get(next_approver_id)
        if not telegram_id:
            logger.warning(f"⚠️ No Telegram ID for next approver {next_approver_id}")
            return False
        
        next_approver_name = DEALERS.get(next_approver_id, {}).get('name', 'Unknown')
        next_approver_title = DEALERS.get(next_approver_id, {}).get('title', 'Approver')
        
        message = f"""✅ <b>TRADE APPROVED - YOUR TURN</b>

👤 Hello <b>{next_approver_name}</b> ({next_approver_title}),

🎉 <b>{approver_name}</b> has approved a trade. It now requires <b>your approval</b>:

📊 <b>TRADE DETAILS:</b>
• <b>Operation:</b> {trade_info.get('operation', 'N/A')}
• <b>Customer:</b> {trade_info.get('customer', 'N/A')}
• <b>Amount:</b> {trade_info.get('price_aed', 'N/A')}
• <b>Previous Approver:</b> {approver_name} ✅

⏰ <b>Time:</b> {get_uae_time().strftime('%Y-%m-%d %H:%M:%S')} UAE

🎯 <b>ACTION NEEDED:</b> Please review and approve this trade.

💡 Use /start to access the Approval Dashboard."""
        
        success = send_telegram_notification(telegram_id, message)
        if success:
            logger.info(f"✅ Notified {next_approver_name} after {approver_name} approval")
        return success
        
    except Exception as e:
        logger.error(f"❌ Approval completion notification error: {e}")
        return False

def notify_final_approval(trade_info):
    """Notify all stakeholders when trade receives final approval"""
    try:
        message = f"""🎉 <b>TRADE FINAL APPROVAL COMPLETED</b>

✅ A trade has been <b>FINALLY APPROVED</b> and is ready for execution:

📊 <b>TRADE DETAILS:</b>
• <b>Operation:</b> {trade_info.get('operation', 'N/A')}
• <b>Customer:</b> {trade_info.get('customer', 'N/A')}
• <b>Amount:</b> {trade_info.get('price_aed', 'N/A')}
• <b>Status:</b> ✅ <b>FINAL APPROVED</b>

🎯 Trade is now complete and ready for execution.

⏰ <b>Time:</b> {get_uae_time().strftime('%Y-%m-%d %H:%M:%S')} UAE

🚀 Gold Trading System"""
        
        # Notify all registered approvers
        notifications_sent = 0
        for approver_id, telegram_id in APPROVER_TELEGRAM_IDS.items():
            if telegram_id:
                if send_telegram_notification(telegram_id, message):
                    notifications_sent += 1
        
        logger.info(f"✅ Final approval notification sent to {notifications_sent} approvers")
        return notifications_sent > 0
        
    except Exception as e:
        logger.error(f"❌ Final approval notification error: {e}")
        return False

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def safe_float(value, default=0.0):
    """Safely convert value to float"""
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def format_money(amount, currency="$"):
    """Format currency with error handling"""
    try:
        amount = safe_float(amount)
        return f"{currency}{amount:,.2f}" if amount >= 0 else f"-{currency}{abs(amount):,.2f}"
    except Exception:
        return f"{currency}0.00"

def format_money_aed(amount_usd):
    """Convert USD to AED with proper formatting"""
    try:
        amount_usd = safe_float(amount_usd)
        amount_aed = amount_usd * USD_TO_AED_RATE
        return f"AED {amount_aed:,.2f}" if amount_aed >= 0 else f"-AED {abs(amount_aed):,.2f}"
    except Exception:
        return "AED 0.00"

def format_weight_combined(kg):
    """Format weight showing both KG and grams"""
    try:
        kg = safe_float(kg)
        grams = kg * 1000
        return f"{kg:,.3f} KG ({grams:,.0f} grams)"
    except Exception:
        return "0.000 KG (0 grams)"

def kg_to_grams(kg):
    """Convert kg to grams"""
    return safe_float(kg) * 1000

def grams_to_oz(grams):
    """Convert grams to troy ounces"""
    grams = safe_float(grams)
    if grams == 0:
        return 0
    return grams / TROY_OUNCE_TO_GRAMS

def get_purity_multiplier(purity_value):
    """Get the verified multiplier for a given purity"""
    if purity_value == "custom":
        return PURITY_MULTIPLIERS["custom"]
    return PURITY_MULTIPLIERS.get(purity_value, PURITY_MULTIPLIERS["custom"])

# ============================================================================
# CALCULATION FUNCTIONS
# ============================================================================

def calculate_professional_gold_trade(weight_grams, purity_value, final_rate_usd_per_oz, rate_source="direct"):
    """MATHEMATICALLY VERIFIED PROFESSIONAL GOLD TRADING CALCULATION"""
    try:
        weight_grams = safe_float(weight_grams)
        final_rate_usd_per_oz = safe_float(final_rate_usd_per_oz)
        
        if weight_grams <= 0 or final_rate_usd_per_oz <= 0:
            return {
                'weight_grams': 0, 'purity_value': 999, 'multiplier': 0.118122,
                'final_rate_usd_per_oz': 0, 'rate_source': rate_source,
                'aed_per_gram': 0, 'total_aed': 0, 'total_usd': 0,
                'pure_gold_grams': 0, 'pure_gold_oz': 0
            }
        
        if purity_value == "custom":
            multiplier = PURITY_MULTIPLIERS["custom"]
            purity_factor = 999
        else:
            purity_factor = safe_float(purity_value)
            multiplier = get_purity_multiplier(purity_value)
        
        aed_per_gram = final_rate_usd_per_oz * multiplier
        total_aed = aed_per_gram * weight_grams
        total_usd = total_aed / USD_TO_AED_RATE
        pure_gold_grams = weight_grams * (purity_factor / 1000)
        pure_gold_oz = pure_gold_grams / TROY_OUNCE_TO_GRAMS if pure_gold_grams > 0 else 0
        
        return {
            'weight_grams': weight_grams,
            'purity_value': purity_factor,
            'multiplier': multiplier,
            'final_rate_usd_per_oz': final_rate_usd_per_oz,
            'rate_source': rate_source,
            'aed_per_gram': aed_per_gram,
            'total_aed': total_aed,
            'total_usd': total_usd,
            'pure_gold_grams': pure_gold_grams,
            'pure_gold_oz': pure_gold_oz
        }
    except Exception as e:
        logger.error(f"❌ Calculation error: {e}")
        return {
            'weight_grams': 0, 'purity_value': 999, 'multiplier': 0.118122,
            'final_rate_usd_per_oz': 0, 'rate_source': rate_source,
            'aed_per_gram': 0, 'total_aed': 0, 'total_usd': 0,
            'pure_gold_grams': 0, 'pure_gold_oz': 0
        }

def calculate_trade_totals_with_override(volume_kg, purity_value, final_rate_usd, rate_source="direct"):
    """COMPLETE TRADE CALCULATION FUNCTION"""
    try:
        weight_grams = kg_to_grams(volume_kg)
        calc_results = calculate_professional_gold_trade(weight_grams, purity_value, final_rate_usd, rate_source)
        
        pure_gold_kg = calc_results['pure_gold_grams'] / 1000 if calc_results['pure_gold_grams'] > 0 else 0
        pure_gold_oz = calc_results['pure_gold_oz']
        total_price_usd = calc_results['total_usd']
        total_price_aed = calc_results['total_aed']
        final_rate_aed_per_oz = final_rate_usd * USD_TO_AED_RATE
        
        market_rate_usd = market_data['gold_usd_oz']
        market_rate_aed_per_oz = market_rate_usd * USD_TO_AED_RATE
        market_calc = calculate_professional_gold_trade(weight_grams, purity_value, market_rate_usd, "market")
        
        return {
            'pure_gold_kg': pure_gold_kg,
            'pure_gold_oz': pure_gold_oz,
            'total_price_usd': total_price_usd,
            'total_price_aed': total_price_aed,
            'final_rate_usd_per_oz': final_rate_usd,
            'final_rate_aed_per_oz': final_rate_aed_per_oz,
            'market_rate_usd_per_oz': market_rate_usd,
            'market_rate_aed_per_oz': market_rate_aed_per_oz,
            'market_total_usd': market_calc['total_usd'],
            'market_total_aed': market_calc['total_aed'],
            'rate_source': rate_source
        }
    except Exception as e:
        logger.error(f"❌ Trade calculation error: {e}")
        return {
            'pure_gold_kg': 0, 'pure_gold_oz': 0, 'total_price_usd': 0, 'total_price_aed': 0,
            'final_rate_usd_per_oz': 0, 'final_rate_aed_per_oz': 0,
            'market_rate_usd_per_oz': market_data['gold_usd_oz'], 'market_rate_aed_per_oz': 0,
            'market_total_usd': 0, 'market_total_aed': 0, 'rate_source': rate_source
        }

def calculate_trade_totals(volume_kg, purity_value, market_rate_usd, pd_type, pd_amount):
    """LEGACY FUNCTION - MAINTAINED FOR BACKWARD COMPATIBILITY"""
    try:
        market_rate_usd = safe_float(market_rate_usd)
        pd_amount = safe_float(pd_amount)
        
        if pd_type == "premium":
            final_rate = market_rate_usd + pd_amount
        else:  # discount
            final_rate = market_rate_usd - pd_amount
        
        return calculate_trade_totals_with_override(volume_kg, purity_value, final_rate, f"market_{pd_type}")
    except Exception as e:
        logger.error(f"❌ Legacy calculation error: {e}")
        return calculate_trade_totals_with_override(volume_kg, purity_value, 2650, "error")

# ============================================================================
# GOLD RATE FETCHING
# ============================================================================

def fetch_gold_rate():
    """Fetch current gold rate"""
    try:
        headers = {'x-access-token': GOLDAPI_KEY}
        response = requests.get('https://www.goldapi.io/api/XAU/USD', headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            new_rate = safe_float(data.get('price', 2650))
            
            if 1000 <= new_rate <= 10000:
                old_rate = market_data['gold_usd_oz']
                change = new_rate - old_rate
                
                uae_time = get_uae_time()
                market_data.update({
                    "gold_usd_oz": round(new_rate, 2),
                    "last_update": uae_time.strftime('%H:%M:%S'),
                    "trend": "up" if change > 0 else "down" if change < 0 else "stable",
                    "change_24h": round(change, 2),
                    "source": "goldapi.io"
                })
                
                logger.info(f"✅ Gold rate updated: ${new_rate:.2f}/oz (UAE time: {uae_time.strftime('%H:%M:%S')})")
                return True
        else:
            logger.warning(f"⚠️ Gold API responded with status {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Rate fetch error: {e}")
    return False

def start_rate_updater():
    """Start background rate updater"""
    def update_loop():
        while True:
            try:
                success = fetch_gold_rate()
                if success:
                    logger.info(f"🔄 Rate updated: ${market_data['gold_usd_oz']:.2f} (UAE: {market_data['last_update']})")
                else:
                    logger.warning("⚠️ Rate update failed, using cached value")
                time.sleep(120)  # 2 minutes
            except Exception as e:
                logger.error(f"❌ Rate updater error: {e}")
                time.sleep(60)
    
    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()
    logger.info("✅ Rate updater started - Updates every 2 minutes")

def get_sheets_client():
    """Get authenticated Google Sheets client"""
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        logger.error(f"❌ Sheets client error: {e}")
        return None

def test_sheets_connection():
    """Test Google Sheets connection"""
    try:
        client = get_sheets_client()
        if not client:
            return False, "Client creation failed"
            
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        worksheets = spreadsheet.worksheets()
        return True, f"Connected ({len(worksheets)} sheets)"
    except Exception as e:
        return False, f"Error: {str(e)[:100]}"

# ============================================================================
# TRADE SESSION CLASS
# ============================================================================

class TradeSession:
    def __init__(self, user_id, dealer):
        self.user_id = user_id
        self.dealer = dealer
        self.session_id = f"TRD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{user_id}"
        self.reset_trade()
    
    def reset_trade(self):
        self.step = "operation"
        self.operation = None
        self.gold_type = None
        self.gold_purity = None
        self.volume_kg = None
        self.volume_grams = None
        self.quantity = None
        self.customer = None
        self.price = None
        self.rate_per_oz = None
        self.rate_type = None
        self.final_rate_per_oz = None
        self.pd_type = None
        self.pd_amount = None
        self.total_aed = None
        self.notes = ""
    
    def validate_trade(self):
        """Validate trade"""
        try:
            required = [self.operation, self.gold_type, self.gold_purity, self.volume_kg, self.customer]
            
            if not all(x is not None for x in required):
                return False, "Missing basic trade information"
            
            if safe_float(self.volume_kg) <= 0:
                return False, "Volume must be greater than 0"
            
            if self.rate_type == "override":
                if not self.final_rate_per_oz or safe_float(self.final_rate_per_oz) <= 0:
                    return False, "Valid final rate required for override"
            elif self.rate_type in ["market", "custom"]:
                if self.pd_type is None or self.pd_amount is None:
                    return False, "Premium/discount information required"
                if self.rate_type == "custom" and (not self.rate_per_oz or safe_float(self.rate_per_oz) <= 0):
                    return False, "Valid custom rate required"
            
            return True, "Valid"
        except Exception as e:
            logger.error(f"❌ Validation error: {e}")
            return False, "Validation failed"

# ============================================================================
# ENHANCED SAVE TRADE WITH TELEGRAM NOTIFICATIONS
# ============================================================================

def save_trade_to_sheets_with_notifications(session):
    """Save trade to Google Sheets and send Telegram notifications"""
    try:
        client = get_sheets_client()
        if not client:
            return False, "Sheets client failed"
            
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        
        current_date = get_uae_time()
        sheet_name = f"Gold_Trades_{current_date.strftime('%Y_%m')}"
        
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=35)
            headers = [
                'Date', 'Time', 'Dealer', 'Operation', 'Customer', 'Gold Type', 
                'Volume KG', 'Volume Grams', 'Pure Gold KG', 'Pure Gold Grams', 'Price USD', 'Price AED', 
                'Input Rate USD', 'Input Rate AED', 'Final Rate USD', 'Final Rate AED', 
                'Market Rate USD', 'Market Rate AED', 'Purity', 'Rate Type', 'P/D Amount', 'Session ID', 
                'Status', 'Approved By', 'Approval Time', 'Approval Notes', 
                'Abhay (Head Accountant)', 'Mushtaq (Level 2)', 'Ahmadreza (Manager)', 'System Notes'
            ]
            worksheet.append_row(headers)
        
        # Calculate trade values
        if session.rate_type == "override":
            calc_results = calculate_trade_totals_with_override(
                session.volume_kg,
                session.gold_purity['value'],
                session.final_rate_per_oz,
                "override"
            )
            base_rate_usd = session.final_rate_per_oz
            rate_description = f"OVERRIDE: ${session.final_rate_per_oz:,.2f}/oz (FINAL)"
            pd_amount_display = "N/A (Override)"
        else:
            if session.rate_type == "market":
                base_rate_usd = market_data['gold_usd_oz']
            else:
                base_rate_usd = session.rate_per_oz
            
            calc_results = calculate_trade_totals(
                session.volume_kg,
                session.gold_purity['value'],
                base_rate_usd,
                session.pd_type,
                session.pd_amount
            )
            
            pd_sign = "+" if session.pd_type == "premium" else "-"
            rate_description = f"{session.rate_type.upper()}: ${base_rate_usd:,.2f} {pd_sign} ${session.pd_amount}/oz"
            pd_amount_display = f"{pd_sign}${session.pd_amount:.2f}"
        
        base_rate_aed = base_rate_usd * USD_TO_AED_RATE
        pure_gold_kg = calc_results['pure_gold_kg']
        total_price_usd = calc_results['total_price_usd']
        total_price_aed = calc_results['total_price_aed']
        final_rate_usd = calc_results.get('final_rate_usd_per_oz', 0)
        final_rate_aed = final_rate_usd * USD_TO_AED_RATE
        market_rate_usd = calc_results['market_rate_usd_per_oz']
        market_rate_aed = calc_results['market_rate_aed_per_oz']
        
        # Build gold type description
        gold_type_desc = session.gold_type['name']
        if hasattr(session, 'quantity') and session.quantity:
            gold_type_desc += f" (qty: {session.quantity})"
        
        # Save to sheets
        row_data = [
            current_date.strftime('%Y-%m-%d'),
            current_date.strftime('%H:%M:%S') + ' UAE',
            session.dealer['name'],
            session.operation.upper(),
            session.customer,
            gold_type_desc,
            f"{session.volume_kg:.3f} KG",
            f"{session.volume_kg * 1000:,.0f} grams",
            f"{pure_gold_kg:.3f} KG",
            f"{pure_gold_kg * 1000:,.0f} grams",
            f"${total_price_usd:,.2f}",
            f"AED {total_price_aed:,.2f}",
            f"${base_rate_usd:,.2f}",
            f"AED {base_rate_aed:,.2f}",
            f"${final_rate_usd:,.2f}",
            f"AED {final_rate_aed:,.2f}",
            f"${market_rate_usd:,.2f}",
            f"AED {market_rate_aed:,.2f}",
            session.gold_purity['name'],
            session.rate_type.upper(),
            pd_amount_display,
            session.session_id,
            "PENDING",
            "",
            "",
            "",
            "",
            "",
            "",
            f"v4.9 Telegram Notifications: {rate_description}"
        ]
        
        worksheet.append_row(row_data)
        
        # Apply PENDING (RED) formatting
        row_number = len(worksheet.get_all_values())
        try:
            status_info = APPROVAL_STATUS["PENDING"]
            pending_format = {
                "backgroundColor": status_info["color"],
                "textFormat": {
                    "foregroundColor": status_info["text_color"],
                    "bold": True
                }
            }
            worksheet.format(f"W{row_number}:W{row_number}", pending_format)
        except Exception as e:
            logger.warning(f"⚠️ Status formatting failed: {e}")
        
        # SEND TELEGRAM NOTIFICATION TO FIRST APPROVER (ABHAY)
        trade_info = {
            'operation': session.operation.upper(),
            'customer': session.customer,
            'gold_type': gold_type_desc,
            'volume_kg': f"{session.volume_kg:.3f} KG",
            'price_aed': f"AED {total_price_aed:,.2f}",
            'dealer': session.dealer['name'],
            'session_id': session.session_id
        }
        
        # Notify Abhay (Head Accountant) - Approver ID 1001
        notify_new_trade_approval_needed(trade_info, "1001")
        
        logger.info(f"✅ Trade saved with Telegram notification: {session.session_id}")
        return True, session.session_id
        
    except Exception as e:
        logger.error(f"❌ Save with notifications failed: {e}")
        return False, str(e)

def get_pending_trades(dealer):
    """Get pending trades that the dealer can approve"""
    try:
        client = get_sheets_client()
        if not client:
            return []
        
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        
        # Get current month sheet
        current_date = get_uae_time()
        sheet_name = f"Gold_Trades_{current_date.strftime('%Y_%m')}"
        
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except:
            return []
        
        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:
            return []
        
        pending_trades = []
        permissions = dealer.get('permissions', [])
        
        for i, row in enumerate(all_values[1:], 2):
            if len(row) > 22:
                status = row[22].strip()
                
                # Check if dealer can approve this status level
                can_approve = False
                if status == "PENDING" and "approve_level_1" in permissions:
                    can_approve = True
                elif status == "LEVEL_1_APPROVED" and "approve_level_2" in permissions:
                    can_approve = True
                elif status == "LEVEL_2_APPROVED" and "approve_level_3" in permissions:
                    can_approve = True
                
                if can_approve:
                    trade_info = {
                        'row': i,
                        'date': row[0] if len(row) > 0 else '',
                        'time': row[1] if len(row) > 1 else '',
                        'dealer': row[2] if len(row) > 2 else '',
                        'operation': row[3] if len(row) > 3 else '',
                        'customer': row[4] if len(row) > 4 else '',
                        'gold_type': row[5] if len(row) > 5 else '',
                        'volume_kg': row[6] if len(row) > 6 else '',
                        'price_usd': row[10] if len(row) > 10 else '',
                        'price_aed': row[11] if len(row) > 11 else '',
                        'status': status,
                        'session_id': row[21] if len(row) > 21 else ''
                    }
                    pending_trades.append(trade_info)
        
        return pending_trades
        
    except Exception as e:
        logger.error(f"Error getting pending trades: {e}")
        return []

def approve_trade_with_notifications(row_number, approver_name, approval_level, notes=""):
    """Approve trade and send Telegram notifications"""
    try:
        client = get_sheets_client()
        if not client:
            return False, "Sheets connection failed"
        
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        current_date = get_uae_time()
        sheet_name = f"Gold_Trades_{current_date.strftime('%Y_%m')}"
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Get trade info before updating
        all_values = worksheet.get_all_values()
        if row_number <= len(all_values):
            trade_row = all_values[row_number - 1]
            trade_info = {
                'operation': trade_row[3] if len(trade_row) > 3 else 'N/A',
                'customer': trade_row[4] if len(trade_row) > 4 else 'N/A', 
                'gold_type': trade_row[5] if len(trade_row) > 5 else 'N/A',
                'volume_kg': trade_row[6] if len(trade_row) > 6 else 'N/A',
                'price_aed': trade_row[11] if len(trade_row) > 11 else 'N/A',
                'dealer': trade_row[2] if len(trade_row) > 2 else 'N/A'
            }
        else:
            trade_info = {}
        
        # Determine new status and next approver
        if approval_level == 1:
            new_status = "LEVEL_1_APPROVED"
            level_title = "✅ ABHAY (HEAD ACCOUNTANT) APPROVED"
            next_approver_id = "1002"  # Mushtaq
        elif approval_level == 2:
            new_status = "LEVEL_2_APPROVED"
            level_title = "✅ MUSHTAQ APPROVED"
            next_approver_id = "1003"  # Ahmadreza
        elif approval_level == 3:
            new_status = "FINAL_APPROVED"
            level_title = "✅ AHMADREZA (MANAGER) FINAL APPROVED"
            next_approver_id = None
        else:
            return False, "Invalid approval level"
        
        # Update sheet
        uae_time = get_uae_time()
        approval_time = uae_time.strftime('%Y-%m-%d %H:%M:%S UAE')
        
        updates = [
            {'range': f'W{row_number}', 'values': [[new_status]]},
            {'range': f'X{row_number}', 'values': [[level_title]]},
            {'range': f'Y{row_number}', 'values': [[approval_time]]},
            {'range': f'Z{row_number}', 'values': [[f"{approver_name} - Level {approval_level}: {notes}" if notes else f"{approver_name} - Level {approval_level} approval completed"]]}
        ]
        
        # Update specific approver columns
        if approval_level == 1:
            updates.append({'range': f'AA{row_number}', 'values': [[f"ABHAY (HEAD ACCOUNTANT) - {approval_time}"]]})
        elif approval_level == 2:
            updates.append({'range': f'AB{row_number}', 'values': [[f"MUSHTAQ - {approval_time}"]]})
        elif approval_level == 3:
            updates.append({'range': f'AC{row_number}', 'values': [[f"AHMADREZA (MANAGER) - {approval_time}"]]})
        
        worksheet.batch_update(updates)
        
        # Apply status formatting
        status_info = APPROVAL_STATUS[new_status]
        status_format = {
            "backgroundColor": status_info["color"],
            "textFormat": {
                "foregroundColor": status_info["text_color"],
                "bold": True,
                "fontSize": 11
            }
        }
        worksheet.format(f"W{row_number}:W{row_number}", status_format)
        
        # SEND TELEGRAM NOTIFICATIONS
        if approval_level == 3:
            # Final approval - notify everyone
            notify_final_approval(trade_info)
        else:
            # Notify next approver
            notify_approval_completed(trade_info, approver_name, next_approver_id)
        
        logger.info(f"✅ Trade approved with notifications: Row {row_number} -> {new_status} by {approver_name}")
        return True, f"Trade approved to {new_status} by {approver_name}"
        
    except Exception as e:
        logger.error(f"❌ Approval with notifications error: {e}")
        return False, str(e)

# ============================================================================
# BOT SETUP WITH TELEGRAM NOTIFICATIONS
# ============================================================================

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start_command(message):
    """Start command with Telegram notification registration"""
    try:
        user_id = message.from_user.id
        
        if user_id in user_sessions:
            del user_sessions[user_id]
        
        fetch_gold_rate()
        
        markup = types.InlineKeyboardMarkup()
        level_emojis = {"admin": "👑", "senior": "⭐", "standard": "🔹", "junior": "🔸", "head_accountant": "📊", "approver_2": "🟠", "manager": "🟢"}
        
        for dealer_id, dealer in DEALERS.items():
            if dealer.get('active', True):
                emoji = level_emojis.get(dealer['level'], "👤")
                markup.add(types.InlineKeyboardButton(
                    f"{emoji} {dealer['name']} ({dealer['level'].replace('_', ' ').title()})",
                    callback_data=f"login_{dealer_id}"
                ))
        
        markup.add(types.InlineKeyboardButton("💰 Live Gold Rate", callback_data="show_rate"))
        
        welcome_text = f"""🥇 GOLD TRADING BOT v4.9 - TELEGRAM NOTIFICATIONS! ✨
🚀 Complete Trading System + Instant Telegram Alerts

📊 SYSTEM STATUS:
💰 Current Rate: {format_money(market_data['gold_usd_oz'])} USD/oz
💱 AED Rate: {format_money_aed(market_data['gold_usd_oz'])}/oz
📈 Trend: {market_data['trend'].title()}
🇦🇪 UAE Time: {market_data['last_update']}
🔄 Updates: Every 2 minutes
☁️ Cloud: Railway Platform (Always On)

🆕 TELEGRAM NOTIFICATIONS:
📲 **ABHAY** - Head Accountant (Gets notified first)
📲 **MUSHTAQ** - Level 2 (Auto-notified after Abhay)  
📲 **AHMADREZA** - Manager (Final approval alerts)

📋 NOTIFICATION FLOW:
🔴 Trade Created → 📲 Abhay Alert
🟡 Abhay Approves → 📲 Mushtaq Alert
🟠 Mushtaq Approves → 📲 Ahmadreza Alert
🟢 Final Approval → 📲 Everyone Notified

✅ Never miss a trade approval again!

🔒 SELECT DEALER/APPROVER TO LOGIN:"""
        
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='HTML')
        logger.info(f"👤 User {user_id} started TELEGRAM NOTIFICATION bot v4.9")
        
    except Exception as e:
        logger.error(f"❌ Start error: {e}")
        try:
            bot.send_message(message.chat.id, "❌ Error occurred. Please try again.")
        except:
            pass

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    """Handle all callbacks"""
    try:
        user_id = call.from_user.id
        data = call.data
        
        logger.info(f"📱 Callback: {user_id} -> {data}")
        
        if data.startswith('login_'):
            handle_login_with_telegram_registration(call)
        elif data == 'show_rate':
            handle_show_rate(call)
        elif data == 'dashboard':
            handle_dashboard(call)
        elif data == 'new_trade':
            handle_new_trade(call)
        elif data == 'approval_dashboard':
            handle_approval_dashboard(call)
        elif data == 'view_pending':
            handle_view_pending(call)
        elif data.startswith('approve_'):
            handle_approve_trade(call)
        elif data.startswith('operation_'):
            handle_operation(call)
        elif data.startswith('goldtype_'):
            handle_gold_type(call)
        elif data.startswith('purity_'):
            handle_purity(call)
        elif data.startswith('volume_'):
            handle_volume(call)
        elif data.startswith('customer_'):
            handle_customer(call)
        elif data.startswith('rate_'):
            handle_rate_choice(call)
        elif data.startswith('pd_'):
            handle_pd_type(call)
        elif data.startswith('premium_') or data.startswith('discount_'):
            handle_pd_amount(call)
        elif data == 'confirm_trade':
            handle_confirm_trade(call)
        elif data == 'cancel_trade':
            handle_cancel_trade(call)
        elif data == 'start':
            start_command(call.message)
        else:
            try:
                bot.edit_message_text(
                    "🚧 Feature under development...",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🔙 Back", callback_data="dashboard")
                    )
                )
            except:
                pass
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"❌ Callback error: {e}")
        try:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
        except:
            pass

def handle_login_with_telegram_registration(call):
    """Handle login and register Telegram ID for notifications"""
    try:
        dealer_id = call.data.replace("login_", "")
        dealer = DEALERS.get(dealer_id)
        
        if not dealer:
            bot.edit_message_text("❌ Dealer not found", call.message.chat.id, call.message.message_id)
            return
        
        user_id = call.from_user.id
        
        # Register Telegram ID for approvers
        if dealer_id in APPROVER_TELEGRAM_IDS:
            register_approver_telegram_id(dealer_id, user_id)
        
        user_sessions[user_id] = {
            "step": "awaiting_pin",
            "temp_dealer_id": dealer_id,
            "temp_dealer": dealer,
            "login_attempts": 0
        }
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="start"))
        
        role_description = dealer['level'].replace('_', ' ').title()
        permissions_list = dealer.get('permissions', ['buy'])
        
        # Add notification status for approvers
        notification_status = ""
        if dealer_id in APPROVER_TELEGRAM_IDS:
            notification_status = "\n📲 Telegram notifications: ✅ ENABLED for this role"
        
        bot.edit_message_text(
            f"""🔒 AUTHENTICATION

Selected: {dealer['name']} ({role_description})
Permissions: {', '.join(permissions_list).upper()}{notification_status}

🔐 PIN: {dealer_id}
💬 Send this PIN as a message

Type the PIN now:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Login error: {e}")

def handle_show_rate(call):
    """Show gold rate"""
    try:
        fetch_gold_rate()
        
        trend_emoji = {"up": "⬆️", "down": "⬇️", "stable": "➡️"}
        emoji = trend_emoji.get(market_data['trend'], "➡️")
        
        rate_text = f"""💰 LIVE GOLD RATE - UAE TIME! ⚡

🥇 Current: {format_money(market_data['gold_usd_oz'])} USD/oz
💱 AED: {format_money_aed(market_data['gold_usd_oz'])}/oz
{emoji} Trend: {market_data['trend'].title()}
⏰ UAE Time: {market_data['last_update']} 
🔄 Next Update: ~2 minutes

📏 Quick Conversions (999 Purity):
• 1 KG: {format_money(market_data['gold_usd_oz'] * 32.15 * 0.999)}
• 1 TT Bar: {format_money(market_data['gold_usd_oz'] * 3.75 * 0.999)}

🇦🇪 UAE Timezone - Railway Cloud 24/7!"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="show_rate"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="start"))
        
        bot.edit_message_text(rate_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"Show rate error: {e}")

def handle_dashboard(call):
    """Dashboard"""
    try:
        fetch_gold_rate()
        
        user_id = call.from_user.id
        session = user_sessions.get(user_id, {})
        dealer = session.get("dealer")
        
        if not dealer:
            bot.edit_message_text("❌ Please login again", call.message.chat.id, call.message.message_id)
            return
        
        permissions = dealer.get('permissions', ['buy'])
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📊 NEW TRADE", callback_data="new_trade"))
        markup.add(types.InlineKeyboardButton("💰 Live Rate", callback_data="show_rate"))
        
        # Add approval dashboard for users with approval permissions
        approval_perms = [p for p in permissions if p.startswith('approve_level') or p == 'view_pending']
        if approval_perms:
            pending_count = len(get_pending_trades(dealer))
            pending_text = f"🔍 Approval Dashboard ({pending_count})" if pending_count > 0 else "🔍 Approval Dashboard"
            markup.add(types.InlineKeyboardButton(pending_text, callback_data="approval_dashboard"))
        
        markup.add(types.InlineKeyboardButton("🔙 Logout", callback_data="start"))
        
        # Show approval permissions in dashboard
        approval_info = ""
        if approval_perms:
            levels = [p.replace('approve_level_', 'L') for p in approval_perms if p.startswith('approve_level')]
            if levels:
                approval_info = f"\n🔍 Approval Levels: {', '.join(levels)}"
        
        dashboard_text = f"""✅ DEALER DASHBOARD v4.9 - TELEGRAM NOTIFICATIONS! ✨

👤 Welcome {dealer['name'].upper()}!
🔒 Level: {dealer['level'].replace('_', ' ').title()}
🎯 Permissions: {', '.join(permissions).upper()}{approval_info}

💰 LIVE Rate: {format_money(market_data['gold_usd_oz'])} USD/oz ⚡
💱 AED: {format_money_aed(market_data['gold_usd_oz'])}/oz
⏰ UAE Time: {market_data['last_update']} (Updates every 2min)
📈 Change: {market_data['change_24h']:+.2f} USD

🎯 COMPLETE TRADING + NOTIFICATION SYSTEM:
✅ All Gold Types (Kilo, TT=116.64g, 100g, Tola=11.66g, Custom)
✅ All Purities (999, 995, 916, 875, 750, 990)
✅ Rate Options (Market, Custom, Override)
✅ DECIMAL Quantities (0.25, 2.5, etc.)
✅ Professional Sheet Integration
✅ TELEGRAM NOTIFICATIONS (Instant alerts)
✅ Visual Status Indicators (Red→Yellow→Orange→Green)
{chr(10) + f'✅ Pending Approvals: {len(get_pending_trades(dealer))}' if approval_perms else ''}

👆 SELECT ACTION:"""
        
        bot.edit_message_text(dashboard_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")

def handle_new_trade(call):
    """New trade"""
    try:
        fetch_gold_rate()
        
        user_id = call.from_user.id
        session_data = user_sessions.get(user_id, {})
        dealer = session_data.get("dealer")
        
        if not dealer:
            bot.edit_message_text("❌ Please login first", call.message.chat.id, call.message.message_id)
            return
        
        trade_session = TradeSession(user_id, dealer)
        user_sessions[user_id]["trade_session"] = trade_session
        
        permissions = dealer.get('permissions', ['buy'])
        markup = types.InlineKeyboardMarkup()
        
        if 'buy' in permissions:
            markup.add(types.InlineKeyboardButton("📈 BUY", callback_data="operation_buy"))
        if 'sell' in permissions:
            markup.add(types.InlineKeyboardButton("📉 SELL", callback_data="operation_sell"))
        
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="dashboard"))
        
        bot.edit_message_text(
            f"""📊 NEW TRADE - STEP 1/8 (OPERATION)

👤 Dealer: {dealer['name']}
🔐 Permissions: {', '.join(permissions).upper()}
💰 Current Rate: {format_money(market_data['gold_usd_oz'])} USD/oz
⏰ UAE Time: {market_data['last_update']}

🎯 SELECT OPERATION:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
        
        logger.info(f"📊 User {user_id} started new trade v4.9")
    except Exception as e:
        logger.error(f"New trade error: {e}")

def handle_operation(call):
    """Handle operation selection"""
    try:
        user_id = call.from_user.id
        operation = call.data.replace("operation_", "")
        
        session_data = user_sessions.get(user_id, {})
        trade_session = session_data.get("trade_session")
        
        if not trade_session:
            bot.edit_message_text("❌ Session error", call.message.chat.id, call.message.message_id)
            return
        
        trade_session.operation = operation
        trade_session.step = "gold_type"
        
        markup = types.InlineKeyboardMarkup()
        for gold_type in GOLD_TYPES:
            markup.add(types.InlineKeyboardButton(
                f"🥇 {gold_type['name']} ({gold_type['code']})",
                callback_data=f"goldtype_{gold_type['code']}"
            ))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
        
        bot.edit_message_text(
            f"""📊 NEW TRADE - STEP 2/8 (GOLD TYPE)

✅ Operation: {operation.upper()}

🥇 SELECT GOLD TYPE:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Operation error: {e}")

def handle_gold_type(call):
    """Handle gold type selection"""
    try:
        user_id = call.from_user.id
        type_code = call.data.replace("goldtype_", "")
        
        session_data = user_sessions.get(user_id, {})
        trade_session = session_data.get("trade_session")
        
        if not trade_session:
            bot.edit_message_text("❌ Session error", call.message.chat.id, call.message.message_id)
            return
        
        selected_type = next((gt for gt in GOLD_TYPES if gt['code'] == type_code), None)
        if not selected_type:
            bot.edit_message_text("❌ Invalid type", call.message.chat.id, call.message.message_id)
            return
        
        trade_session.gold_type = selected_type
        trade_session.step = "purity"
        
        markup = types.InlineKeyboardMarkup()
        for purity in GOLD_PURITIES:
            markup.add(types.InlineKeyboardButton(
                f"⚖️ {purity['name']}",
                callback_data=f"purity_{purity['value']}"
            ))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
        
        bot.edit_message_text(
            f"""📊 NEW TRADE - STEP 3/8 (PURITY)

✅ Operation: {trade_session.operation.upper()}
✅ Type: {selected_type['name']}

⚖️ SELECT PURITY:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Gold type error: {e}")

def handle_purity(call):
    """Handle purity selection"""
    try:
        user_id = call.from_user.id
        purity_value = call.data.replace("purity_", "")
        
        session_data = user_sessions.get(user_id, {})
        trade_session = session_data.get("trade_session")
        
        if not trade_session:
            bot.edit_message_text("❌ Session error", call.message.chat.id, call.message.message_id)
            return
        
        if purity_value == "custom":
            selected_purity = {"name": "Custom", "value": "custom"}
        else:
            try:
                purity_float = float(purity_value)
                selected_purity = next((p for p in GOLD_PURITIES if p['value'] == purity_float), None)
            except:
                bot.edit_message_text("❌ Invalid purity", call.message.chat.id, call.message.message_id)
                return
        
        if not selected_purity:
            bot.edit_message_text("❌ Purity not found", call.message.chat.id, call.message.message_id)
            return
        
        trade_session.gold_purity = selected_purity
        trade_session.step = "volume"
        
        markup = types.InlineKeyboardMarkup()
        row = []
        for i, volume in enumerate(VOLUME_PRESETS):
            row.append(types.InlineKeyboardButton(f"{volume}kg", callback_data=f"volume_{volume}"))
            if len(row) == 3:
                markup.add(*row)
                row = []
        if row:
            markup.add(*row)
        
        markup.add(types.InlineKeyboardButton("✏️ Custom", callback_data="volume_custom"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
        
        bot.edit_message_text(
            f"""📊 NEW TRADE - STEP 4/8 (VOLUME)

✅ Operation: {trade_session.operation.upper()}
✅ Type: {trade_session.gold_type['name']}
✅ Purity: {selected_purity['name']}

📏 SELECT VOLUME IN KG:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Purity error: {e}")

def handle_volume(call):
    """Handle volume selection"""
    try:
        user_id = call.from_user.id
        volume_data = call.data.replace("volume_", "")
        
        session_data = user_sessions.get(user_id, {})
        trade_session = session_data.get("trade_session")
        
        if not trade_session:
            bot.edit_message_text("❌ Session error", call.message.chat.id, call.message.message_id)
            return
        
        if volume_data == "custom":
            user_sessions[user_id]["awaiting_input"] = "volume"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
            
            bot.edit_message_text(
                """📏 CUSTOM VOLUME

💬 Send volume in KG (example: 25.5)
⚠️ Range: 0.001 - 1000 KG

Type volume now:""",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
            return
        
        try:
            volume_kg = float(volume_data)
        except:
            bot.edit_message_text("❌ Invalid volume", call.message.chat.id, call.message.message_id)
            return
        
        trade_session.volume_kg = volume_kg
        trade_session.volume_grams = kg_to_grams(volume_kg)
        trade_session.step = "customer"
        
        markup = types.InlineKeyboardMarkup()
        for customer in CUSTOMERS:
            markup.add(types.InlineKeyboardButton(
                f"👤 {customer}" if customer != "Custom" else f"✏️ {customer}",
                callback_data=f"customer_{customer}"
            ))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
        
        volume_oz = grams_to_oz(kg_to_grams(volume_kg))
        
        bot.edit_message_text(
            f"""📊 NEW TRADE - STEP 5/8 (CUSTOMER)

✅ Volume: {format_weight_combined(volume_kg)} = {volume_oz:.2f} troy oz

👤 SELECT CUSTOMER:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Volume error: {e}")

def handle_customer(call):
    """Handle customer selection"""
    try:
        user_id = call.from_user.id
        customer = call.data.replace("customer_", "")
        
        session_data = user_sessions.get(user_id, {})
        trade_session = session_data.get("trade_session")
        
        if not trade_session:
            bot.edit_message_text("❌ Session error", call.message.chat.id, call.message.message_id)
            return
        
        if customer == "Custom":
            user_sessions[user_id]["awaiting_input"] = "customer"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
            
            bot.edit_message_text(
                """👤 CUSTOM CUSTOMER

💬 Send customer name
⚠️ Max 50 characters

Type name now:""",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
            return
        
        trade_session.customer = customer
        trade_session.step = "rate_choice"
        
        current_spot = market_data['gold_usd_oz']
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📊 Use Market Rate", callback_data="rate_market"))
        markup.add(types.InlineKeyboardButton("⚡ Rate Override", callback_data="rate_override"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
        
        bot.edit_message_text(
            f"""📊 NEW TRADE - STEP 6/8 (RATE SELECTION)

✅ Customer: {customer}

💰 CURRENT MARKET: ${current_spot:,.2f} USD/oz

🎯 RATE OPTIONS:
• 📊 Market Rate: Live rate + premium/discount
• ⚡ Rate Override: Direct final rate

💎 SELECT RATE SOURCE:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Customer error: {e}")

def handle_rate_choice(call):
    """Handle rate choice"""
    try:
        fetch_gold_rate()
        
        user_id = call.from_user.id
        choice = call.data.replace("rate_", "")
        
        session_data = user_sessions.get(user_id, {})
        trade_session = session_data.get("trade_session")
        
        if not trade_session:
            bot.edit_message_text("❌ Session error", call.message.chat.id, call.message.message_id)
            return
        
        if choice == "market":
            trade_session.step = "pd_type"
            trade_session.rate_per_oz = market_data['gold_usd_oz']
            trade_session.rate_type = "market"
            
            current_spot = market_data['gold_usd_oz']
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("⬆️ PREMIUM", callback_data="pd_premium"))
            markup.add(types.InlineKeyboardButton("⬇️ DISCOUNT", callback_data="pd_discount"))
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
            
            bot.edit_message_text(
                f"""📊 NEW TRADE - STEP 7/8 (PREMIUM/DISCOUNT)

✅ Rate: Market Rate (${current_spot:,.2f}/oz)
⏰ UAE Time: {market_data['last_update']}

🎯 SELECT PREMIUM OR DISCOUNT:

💡 Premium = ADD to rate
💡 Discount = SUBTRACT from rate

💎 SELECT TYPE:""",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
            
        elif choice == "override":
            user_sessions[user_id]["awaiting_input"] = "override_rate"
            trade_session.rate_type = "override"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
            
            current_market = market_data['gold_usd_oz']
            
            bot.edit_message_text(
                f"""⚡ RATE OVERRIDE - ENTER FINAL RATE

💰 Current Market: ${current_market:,.2f} USD/oz (reference only)
⏰ UAE Time: {market_data['last_update']}

🎯 Enter the FINAL rate per ounce
📝 This will be used directly in calculations

Examples: 2675.00, 2580.25

⚠️ Range: $1,000 - $10,000 per ounce
✅ No premium/discount step needed

Type your FINAL rate per ounce now:""",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
    except Exception as e:
        logger.error(f"Rate choice error: {e}")

def handle_pd_type(call):
    """Handle premium/discount type"""
    try:
        user_id = call.from_user.id
        pd_type = call.data.replace("pd_", "")
        
        session_data = user_sessions.get(user_id, {})
        trade_session = session_data.get("trade_session")
        
        if not trade_session:
            bot.edit_message_text("❌ Session error", call.message.chat.id, call.message.message_id)
            return
        
        trade_session.pd_type = pd_type
        
        amounts = PREMIUM_AMOUNTS if pd_type == "premium" else DISCOUNT_AMOUNTS
        markup = types.InlineKeyboardMarkup()
        row = []
        
        for i, amount in enumerate(amounts):
            button_text = f"${amount}" if amount > 0 else "0"
            row.append(types.InlineKeyboardButton(button_text, callback_data=f"{pd_type}_{amount}"))
            if len(row) == 4:
                markup.add(*row)
                row = []
        if row:
            markup.add(*row)
        
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
        
        base_rate = getattr(trade_session, 'rate_per_oz', market_data['gold_usd_oz'])
        action_desc = "ADDED to" if pd_type == "premium" else "SUBTRACTED from"
        sign = "+" if pd_type == "premium" else "-"
        
        bot.edit_message_text(
            f"""📊 NEW TRADE - STEP 8/8 ({pd_type.upper()} AMOUNT)

💎 SELECT {pd_type.upper()} AMOUNT PER OUNCE:

💡 This amount will be {action_desc} your base rate:
• Base Rate: ${base_rate:,.2f}/oz

💰 EXAMPLE: ${base_rate:,.2f} {sign} $10 = ${base_rate + 10 if pd_type == 'premium' else base_rate - 10:,.2f}/oz

🎯 SELECT {pd_type.upper()} AMOUNT:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"P/D type error: {e}")

def handle_pd_amount(call):
    """Handle premium/discount amount"""
    try:
        user_id = call.from_user.id
        
        session_data = user_sessions.get(user_id, {})
        trade_session = session_data.get("trade_session")
        
        if not trade_session:
            bot.edit_message_text("❌ Session error", call.message.chat.id, call.message.message_id)
            return
        
        # Determine if this is premium or discount
        if call.data.startswith('premium_'):
            amount_data = call.data.replace("premium_", "")
            pd_type = "premium"
        else:
            amount_data = call.data.replace("discount_", "")
            pd_type = "discount"
        
        try:
            amount = float(amount_data)
        except:
            bot.edit_message_text("❌ Invalid amount", call.message.chat.id, call.message.message_id)
            return
        
        trade_session.pd_amount = amount
        
        # Calculate final rate
        base_rate = market_data['gold_usd_oz']
        
        if trade_session.pd_type == "premium":
            final_rate = base_rate + amount
        else:  # discount
            final_rate = base_rate - amount
        
        trade_session.final_rate_per_oz = final_rate
        
        # Show trade confirmation
        show_confirmation(call, trade_session)
    except Exception as e:
        logger.error(f"P/D amount error: {e}")

def show_confirmation(call, trade_session, user_id=None):
    """Show trade confirmation"""
    try:
        is_valid, msg = trade_session.validate_trade()
        if not is_valid:
            error_msg = f"❌ {msg}"
            if call:
                bot.edit_message_text(error_msg, call.message.chat.id, call.message.message_id)
            else:
                bot.send_message(user_id, error_msg)
            return
        
        # Calculate using appropriate method based on rate type
        if trade_session.rate_type == "override":
            calc_results = calculate_trade_totals_with_override(
                trade_session.volume_kg,
                trade_session.gold_purity['value'],
                trade_session.final_rate_per_oz,
                "override"
            )
            rate_description = f"OVERRIDE: ${trade_session.final_rate_per_oz:,.2f}/oz (FINAL)"
        else:
            base_rate = market_data['gold_usd_oz']
            
            calc_results = calculate_trade_totals(
                trade_session.volume_kg,
                trade_session.gold_purity['value'],
                base_rate,
                trade_session.pd_type,
                trade_session.pd_amount
            )
            
            pd_sign = "+" if trade_session.pd_type == "premium" else "-"
            rate_description = f"MARKET: ${base_rate:,.2f} {pd_sign} ${trade_session.pd_amount}/oz"
        
        # Update session with calculated values
        trade_session.price = calc_results['total_price_usd']
        if not hasattr(trade_session, 'final_rate_per_oz') or trade_session.final_rate_per_oz is None:
            trade_session.final_rate_per_oz = calc_results.get('final_rate_usd_per_oz', 0)
        
        final_rate_display = calc_results.get('final_rate_usd_per_oz', 0)
        final_rate_aed = final_rate_display * USD_TO_AED_RATE
        
        # Build type description
        type_desc = trade_session.gold_type['name']
        
        confirmation_text = f"""✅ TRADE CONFIRMATION - v4.9 WITH NOTIFICATIONS! ✨

🎯 TRADE DETAILS:
• Operation: {trade_session.operation.upper()}
• Type: {type_desc}
• Purity: {trade_session.gold_purity['name']}
• Total Weight: {format_weight_combined(trade_session.volume_kg)}
• Pure Gold: {format_weight_combined(calc_results['pure_gold_kg'])} ({calc_results['pure_gold_oz']:.3f} troy oz)
• Customer: {trade_session.customer}

💰 CALCULATION:
• {rate_description}
• Final Rate: ${final_rate_display:,.2f} USD/oz = AED {final_rate_aed:,.2f}/oz
• Total Price: ${calc_results['total_price_usd']:,.2f} USD
• Total Price: {format_money_aed(calc_results['total_price_usd'])}

👤 Dealer: {trade_session.dealer['name']}
⏰ Time: {get_uae_time().strftime('%H:%M:%S')} UAE

📲 NOTIFICATIONS READY:
✅ Abhay will be notified instantly when saved!

Ready to save with Telegram notifications!"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ CONFIRM & SAVE", callback_data="confirm_trade"))
        markup.add(types.InlineKeyboardButton("✏️ Edit", callback_data="new_trade"))
        markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_trade"))
        
        if call:
            bot.edit_message_text(confirmation_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            bot.send_message(user_id, confirmation_text, reply_markup=markup)
            
    except Exception as e:
        logger.error(f"❌ Confirmation error: {e}")
        error_msg = f"❌ Confirmation failed: {str(e)}"
        if call:
            bot.edit_message_text(error_msg, call.message.chat.id, call.message.message_id)
        else:
            bot.send_message(user_id, error_msg)

def handle_confirm_trade(call):
    """Confirm and save trade with notifications"""
    try:
        user_id = call.from_user.id
        session_data = user_sessions.get(user_id, {})
        trade_session = session_data.get("trade_session")
        
        if not trade_session:
            bot.edit_message_text("❌ Session error", call.message.chat.id, call.message.message_id)
            return
        
        bot.edit_message_text("💾 Saving trade and sending notifications...", call.message.chat.id, call.message.message_id)
        
        success, result = save_trade_to_sheets_with_notifications(trade_session)
        
        if success:
            # Calculate for success message
            if trade_session.rate_type == "override":
                calc_results = calculate_trade_totals_with_override(
                    trade_session.volume_kg,
                    trade_session.gold_purity['value'],
                    trade_session.final_rate_per_oz,
                    "override"
                )
            else:
                base_rate = market_data['gold_usd_oz']
                
                calc_results = calculate_trade_totals(
                    trade_session.volume_kg,
                    trade_session.gold_purity['value'],
                    base_rate,
                    trade_session.pd_type,
                    trade_session.pd_amount
                )
            
            # Build type description
            type_desc = trade_session.gold_type['name']
            
            success_text = f"""🎉 TRADE SAVED WITH NOTIFICATIONS! ✨

✅ Trade ID: {result}
📊 Saved to: Google Sheets
📲 Notification sent to: Abhay (Head Accountant)
⏰ Time: {get_uae_time().strftime('%H:%M:%S')} UAE

📋 TRADE SUMMARY:
• {trade_session.operation.upper()}: {type_desc}
• Total Weight: {format_weight_combined(trade_session.volume_kg)}
• Pure Gold: {format_weight_combined(calc_results['pure_gold_kg'])}
• Customer: {trade_session.customer}
• Dealer: {trade_session.dealer['name']}

💰 FINAL CALCULATION:
• Total: ${calc_results['total_price_usd']:,.2f} USD
• Total: {format_money_aed(calc_results['total_price_usd'])}

📲 NOTIFICATIONS:
✅ Abhay notified via Telegram!
⏳ Status: PENDING (Red) - awaiting approval

🏆 SUCCESS! Trade saved and notifications sent!"""
        else:
            success_text = f"❌ SAVE ERROR\n\n{result}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📊 NEW TRADE", callback_data="new_trade"))
        markup.add(types.InlineKeyboardButton("🏠 Dashboard", callback_data="dashboard"))
        
        bot.edit_message_text(success_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        
        if "trade_session" in user_sessions[user_id]:
            del user_sessions[user_id]["trade_session"]
    except Exception as e:
        logger.error(f"Confirm trade error: {e}")

def handle_cancel_trade(call):
    """Cancel trade"""
    try:
        user_id = call.from_user.id
        if user_id in user_sessions and "trade_session" in user_sessions[user_id]:
            del user_sessions[user_id]["trade_session"]
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🏠 Dashboard", callback_data="dashboard"))
        
        bot.edit_message_text("❌ Trade cancelled", call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"Cancel trade error: {e}")

def handle_approval_dashboard(call):
    """Handle approval dashboard"""
    try:
        user_id = call.from_user.id
        session = user_sessions.get(user_id, {})
        dealer = session.get("dealer")
        
        if not dealer:
            bot.edit_message_text("❌ Please login again", call.message.chat.id, call.message.message_id)
            return
        
        permissions = dealer.get('permissions', [])
        
        # Check if user has approval permissions
        approval_perms = [p for p in permissions if p.startswith('approve_level')]
        if not approval_perms and 'view_pending' not in permissions:
            bot.edit_message_text("❌ No approval permissions", call.message.chat.id, call.message.message_id)
            return
        
        # Get pending trades count
        pending_trades = get_pending_trades(dealer)
        
        markup = types.InlineKeyboardMarkup()
        if pending_trades:
            markup.add(types.InlineKeyboardButton(f"📋 View Pending ({len(pending_trades)})", callback_data="view_pending"))
        markup.add(types.InlineKeyboardButton("🔙 Dashboard", callback_data="dashboard"))
        
        # Determine approval level
        approval_level = "Unknown"
        if "approve_level_1" in permissions:
            approval_level = "📊 Head Accountant - ABHAY (First Review)"
        elif "approve_level_2" in permissions:
            approval_level = "🟠 Level 2 - MUSHTAQ (Secondary Review)"  
        elif "approve_level_3" in permissions:
            approval_level = "🟢 Manager - AHMADREZA (Final Approval)"
        
        dashboard_text = f"""🔍 APPROVAL DASHBOARD v4.9

👤 Approver: {dealer['name'].upper()}
🎯 Role: {approval_level}
🔑 Authority: {', '.join(approval_perms).replace('approve_level_', 'Level ').upper()}

📊 CURRENT STATUS:
• Pending for You: {len(pending_trades)}

📋 ACCOUNTING HIERARCHY:
🔴 PENDING 
   ↓
📊 **ABHAY** (Head Accountant)
   ↓  
🟠 **MUSHTAQ** (Level 2)
   ↓
🟢 **AHMADREZA** (Manager - Final)

📲 You'll get Telegram notifications for trades!

👆 SELECT ACTION:"""
        
        bot.edit_message_text(dashboard_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"Approval dashboard error: {e}")

def handle_view_pending(call):
    """Handle view pending trades"""
    try:
        user_id = call.from_user.id
        session = user_sessions.get(user_id, {})
        dealer = session.get("dealer")
        
        if not dealer:
            bot.edit_message_text("❌ Please login again", call.message.chat.id, call.message.message_id)
            return
        
        pending_trades = get_pending_trades(dealer)
        
        if not pending_trades:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="approval_dashboard"))
            
            bot.edit_message_text(
                "✅ No pending trades for your approval level!",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
            return
        
        # Show first few trades with approve buttons
        markup = types.InlineKeyboardMarkup()
        
        trades_text = f"""📋 PENDING TRADES ({len(pending_trades)})

Ready for your approval:

"""
        
        for i, trade in enumerate(pending_trades[:5]):
            status_emoji = {"PENDING": "🔴", "LEVEL_1_APPROVED": "🟡", "LEVEL_2_APPROVED": "🟠"}.get(trade['status'], "🔴")
            
            trades_text += f"""#{i+1} {status_emoji} Row {trade['row']}
• {trade['operation']} {trade['gold_type']} 
• Customer: {trade['customer']}
• Amount: {trade['price_aed']}
• Date: {trade['date']} {trade['time']}

"""
            
            # Add approve button for each trade
            markup.add(
                types.InlineKeyboardButton(f"✅ Approve #{i+1}", callback_data=f"approve_{trade['row']}")
            )
        
        if len(pending_trades) > 5:
            trades_text += f"... and {len(pending_trades) - 5} more trades"
        
        markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="view_pending"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="approval_dashboard"))
        
        bot.edit_message_text(trades_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        
    except Exception as e:
        logger.error(f"View pending error: {e}")

def handle_approve_trade(call):
    """Handle approve trade"""
    try:
        user_id = call.from_user.id
        session = user_sessions.get(user_id, {})
        dealer = session.get("dealer")
        
        if not dealer:
            bot.edit_message_text("❌ Please login again", call.message.chat.id, call.message.message_id)
            return
        
        row_number = int(call.data.replace("approve_", ""))
        permissions = dealer.get('permissions', [])
        
        # Determine approval level
        approval_level = 0
        if "approve_level_1" in permissions:
            approval_level = 1
        elif "approve_level_2" in permissions:
            approval_level = 2
        elif "approve_level_3" in permissions:
            approval_level = 3
        
        if approval_level == 0:
            bot.edit_message_text("❌ No approval permissions", call.message.chat.id, call.message.message_id)
            return
        
        bot.edit_message_text(f"✅ Approving trade at row {row_number}...", call.message.chat.id, call.message.message_id)
        
        success, message = approve_trade_with_notifications(row_number, dealer['name'], approval_level)
        
        if success:
            # Custom approval messages for each level
            if approval_level == 1:
                approval_msg = f"✅ **ABHAY** (HEAD ACCOUNTANT) APPROVED"
                next_step = "→ Mushtaq will be notified via Telegram"
            elif approval_level == 2:
                approval_msg = f"✅ **MUSHTAQ** APPROVED (Level 2)"
                next_step = "→ Ahmadreza will be notified via Telegram"
            else:  # Level 3
                approval_msg = f"🎉 **AHMADREZA** FINAL APPROVAL (Manager)"
                next_step = "→ Everyone notified of completion via Telegram"
            
            result_text = f"""✅ TRADE APPROVED WITH NOTIFICATIONS!

{approval_msg}
📊 Row: {row_number}
⏰ UAE Time: {get_uae_time().strftime('%H:%M:%S')}

📲 Next Step: {next_step}

💾 Recorded in accounting workflow tracking!"""
        else:
            result_text = f"❌ Approval failed: {message}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📋 View More Pending", callback_data="view_pending"))
        markup.add(types.InlineKeyboardButton("🔙 Dashboard", callback_data="approval_dashboard"))
        
        bot.edit_message_text(result_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        
    except Exception as e:
        logger.error(f"Approve trade error: {e}")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Handle text messages with Telegram notification support"""
    try:
        user_id = message.from_user.id
        text = message.text.strip()
        
        if user_id not in user_sessions:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🚀 START", callback_data="start"))
            bot.send_message(message.chat.id, "Please use /start", reply_markup=markup)
            return
        
        session_data = user_sessions[user_id]
        
        # PIN authentication
        if session_data.get("step") == "awaiting_pin":
            try:
                bot.delete_message(message.chat.id, message.message_id)
                logger.info("🗑️ PIN deleted for security")
            except:
                pass
            
            if text == session_data["temp_dealer_id"]:
                dealer = session_data["temp_dealer"]
                user_sessions[user_id] = {"step": "authenticated", "dealer": dealer}
                
                permissions = dealer.get('permissions', [])
                approval_perms = [p for p in permissions if p.startswith('approve_level')]
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("📊 NEW TRADE", callback_data="new_trade"))
                markup.add(types.InlineKeyboardButton("💰 Live Rate", callback_data="show_rate"))
                
                if approval_perms:
                    markup.add(types.InlineKeyboardButton("🔍 Approval Dashboard", callback_data="approval_dashboard"))
                
                # Custom role descriptions with notification info
                if dealer['name'] == "Abhay":
                    role_description = "📊 Head Accountant"
                    approval_info = "\n🎯 You review: PENDING trades → Head Accountant Approval\n📲 You get notified: When new trades are created"
                elif dealer['name'] == "Mushtaq":
                    role_description = "🟠 Level 2 Approver"
                    approval_info = "\n🎯 You review: Head Accountant → Level 2 Approval\n📲 You get notified: When Abhay approves trades"
                elif dealer['name'] == "Ahmadreza":
                    role_description = "🟢 Manager (Final Approver)"
                    approval_info = "\n🎯 You review: Level 2 → FINAL APPROVAL + Create Trades\n📲 You get notified: When Mushtaq approves trades"
                else:
                    role_description = dealer['level'].replace('_', ' ').title()
                    approval_info = f"\n🔍 Can approve: {', '.join([p.replace('approve_level_', 'Level ') for p in approval_perms])}" if approval_perms else ""
                
                bot.send_message(
                    user_id, 
                    f"""✅ Welcome {dealer['name'].upper()}! 

🥇 Gold Trading Bot v4.9 - TELEGRAM NOTIFICATIONS! ✨
🚀 All trading features + Instant Telegram Alerts
💰 Current Rate: {format_money(market_data['gold_usd_oz'])} USD/oz
🇦🇪 UAE Time: {market_data['last_update']} (Updates every 2min)

👤 Role: {role_description}{approval_info}

📲 Telegram notifications are now ACTIVE for your role!

Ready for professional gold trading with instant notifications!""", 
                    reply_markup=markup,
                    parse_mode='HTML'
                )
                logger.info(f"✅ Login with notifications: {dealer['name']} (TELEGRAM ENABLED v4.9)")
            else:
                bot.send_message(user_id, "❌ Wrong PIN. Please try again.")
        
        # Handle text inputs for trading
        elif session_data.get("awaiting_input"):
            try:
                bot.delete_message(message.chat.id, message.message_id)
                
                input_type = session_data["awaiting_input"]
                trade_session = session_data.get("trade_session")
                
                if input_type == "volume" and trade_session:
                    volume = safe_float(text)
                    if 0.001 <= volume <= 1000:
                        trade_session.volume_kg = volume
                        trade_session.volume_grams = kg_to_grams(volume)
                        
                        markup = types.InlineKeyboardMarkup()
                        for customer in CUSTOMERS:
                            markup.add(types.InlineKeyboardButton(
                                f"👤 {customer}" if customer != "Custom" else f"✏️ {customer}",
                                callback_data=f"customer_{customer}"
                            ))
                        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
                        
                        volume_oz = grams_to_oz(kg_to_grams(volume))
                        
                        bot.send_message(
                            user_id,
                            f"✅ Volume set: {format_weight_combined(volume)} = {volume_oz:.2f} troy oz\n\n📊 NEW TRADE - STEP 5/8 (CUSTOMER)\n\n👤 SELECT CUSTOMER:",
                            reply_markup=markup
                        )
                    else:
                        bot.send_message(user_id, "❌ Volume must be 0.001-1000 KG")
                
                elif input_type == "customer" and trade_session:
                    if len(text) <= 50:
                        trade_session.customer = text
                        trade_session.step = "rate_choice"
                        
                        current_rate = market_data['gold_usd_oz']
                        
                        markup = types.InlineKeyboardMarkup()
                        markup.add(types.InlineKeyboardButton("📊 Use Market Rate", callback_data="rate_market"))
                        markup.add(types.InlineKeyboardButton("⚡ Rate Override", callback_data="rate_override"))
                        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
                        
                        bot.send_message(
                            user_id,
                            f"""✅ Customer: {text}

📊 NEW TRADE - STEP 6/8 (RATE SELECTION)

💰 Current Market: ${current_rate:,.2f} USD/oz

🎯 RATE OPTIONS:
• 📊 Market Rate: Live rate + premium/discount
• ⚡ Rate Override: Direct final rate

💎 SELECT RATE SOURCE:""",
                            reply_markup=markup
                        )
                    else:
                        bot.send_message(user_id, "❌ Name too long (max 50)")
                
                elif input_type == "override_rate" and trade_session:
                    try:
                        override_rate = safe_float(text)
                        if 1000 <= override_rate <= 10000:
                            trade_session.final_rate_per_oz = override_rate
                            trade_session.step = "confirmation"
                            
                            # Skip premium/discount and go directly to confirmation
                            show_confirmation(None, trade_session, user_id)
                        else:
                            bot.send_message(user_id, "❌ Rate must be between $1,000 - $10,000 per ounce")
                    except ValueError:
                        bot.send_message(user_id, "❌ Invalid rate format. Please enter a number (e.g., 2650.00)")
                
                del session_data["awaiting_input"]
                
            except ValueError:
                bot.send_message(user_id, "❌ Invalid input")
            except Exception as e:
                bot.send_message(user_id, f"❌ Error: {e}")
        
    except Exception as e:
        logger.error(f"❌ Text error: {e}")

# ============================================================================
# MAIN FUNCTION WITH TELEGRAM NOTIFICATIONS
# ============================================================================

def main():
    """Main function with Telegram notification system"""
    try:
        logger.info("=" * 60)
        logger.info("🥇 GOLD TRADING BOT v4.9 - TELEGRAM NOTIFICATIONS!")
        logger.info("=" * 60)
        logger.info("📲 TELEGRAM NOTIFICATION FEATURES:")
        logger.info("✅ Instant Telegram alerts for approvers")
        logger.info("✅ Auto-registration of approver Telegram IDs")
        logger.info("✅ Sequential notification workflow")
        logger.info("✅ Final approval broadcasts")
        logger.info("✅ Rich HTML formatting")
        logger.info("📊 ACCOUNTING WORKFLOW:")
        logger.info("✅ ABHAY - Head Accountant (Notified first)")
        logger.info("✅ MUSHTAQ - Level 2 (Auto-notified after Abhay)")
        logger.info("✅ AHMADREZA - Manager (Final approval)")
        logger.info("=" * 60)
        
        # Initialize market data
        market_data["last_update"] = get_uae_time().strftime('%H:%M:%S')
        
        # Test systems
        sheets_ok, sheets_msg = test_sheets_connection()
        logger.info(f"📊 Sheets: {sheets_msg}")
        
        # Fetch initial rate
        rate_ok = fetch_gold_rate()
        if rate_ok:
            logger.info(f"💰 Initial Rate: ${market_data['gold_usd_oz']:.2f} (UAE: {market_data['last_update']})")
        else:
            logger.warning(f"💰 Using default rate: ${market_data['gold_usd_oz']:.2f}")
        
        # Start rate updater
        start_rate_updater()
        time.sleep(2)
        
        logger.info(f"✅ TELEGRAM NOTIFICATION BOT v4.9 READY:")
        logger.info(f"  💰 Gold: {format_money(market_data['gold_usd_oz'])} | {format_money_aed(market_data['gold_usd_oz'])}")
        logger.info(f"  🇦🇪 UAE Time: {market_data['last_update']}")
        logger.info(f"  📊 Sheets: {'Connected' if sheets_ok else 'Fallback mode'}")
        logger.info(f"  📲 Telegram Notifications: ENABLED")
        logger.info(f"  📊 ABHAY: Head Accountant (First notifications)")
        logger.info(f"  🟠 MUSHTAQ: Level 2 (Sequential notifications)")
        logger.info(f"  🟢 AHMADREZA: Manager/Final (Final notifications)")
        logger.info(f"  ⚡ All Features: WORKING")
        logger.info(f"  🔄 Rate Updates: Every 2 minutes")
        logger.info(f"  ☁️ Platform: Railway (24/7 operation)")
        
        logger.info("🚀 STARTING TELEGRAM NOTIFICATION BOT v4.9 FOR 24/7 OPERATION...")
        logger.info("=" * 60)
        
        # Start bot polling
        while True:
            try:
                logger.info("🚀 Starting TELEGRAM NOTIFICATION bot v4.9 polling...")
                bot.infinity_polling(
                    timeout=30, 
                    long_polling_timeout=30,
                    restart_on_change=False,
                    skip_pending=True
                )
            except Exception as e:
                logger.error(f"❌ Bot polling error: {e}")
                logger.info("🔄 Restarting in 10 seconds...")
                time.sleep(10)
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        logger.info("🔄 Attempting restart in 5 seconds...")
        time.sleep(5)
        main()

if __name__ == '__main__':
    main()
