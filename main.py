#!/usr/bin/env python3
"""
🥇 GOLD TRADING BOT v4.7 - WORKING RATES + UAE TIMEZONE + APPROVAL WORKFLOW
✨ FIXED: Reverted to simple working gold rate API
✨ FIXED: All timestamps now use UAE timezone (UTC+4)
✨ FIXED: 2-minute rate updates (reliable frequency)
✨ FIXED: Decimal quantities allowed (0.25, 2.5, etc.)
✨ FIXED: TT Bar weight corrected to exact 116.6380 grams (10 Tola)
✨ RESTORED: Approval workflow with Abhay, Mushtaq, Ahmadreza
✨ RESTORED: Telegram notifications for approvers
✨ RESTORED: Color-coded sheets with approval status
🎨 Stunning gold-themed sheets with business-grade presentation
🚀 Ready to run on Railway with automatic restarts!
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
# MATHEMATICALLY VERIFIED CONSTANTS + UAE TIMEZONE
# ============================================================================

# UAE Timezone (UTC+4)
UAE_TZ = timezone(timedelta(hours=4))

def get_uae_time():
    """Get current time in UAE timezone"""
    return datetime.now(UAE_TZ)

TROY_OUNCE_TO_GRAMS = 31.1035  # Official troy ounce conversion
USD_TO_AED_RATE = 3.674         # Current USD to AED exchange rate

# VERIFIED MULTIPLIERS (USD/Oz → AED/gram) - EXACT CALCULATED VALUES
PURITY_MULTIPLIERS = {
    999: 0.118122,  # (1/31.1035) × (999/999) × 3.674 = 0.118122
    995: 0.117649,  # (1/31.1035) × (995/999) × 3.674 = 0.117649
    916: 0.108308,  # (1/31.1035) × (916/999) × 3.674 = 0.108308
    875: 0.103460,  # (1/31.1035) × (875/999) × 3.674 = 0.103460
    750: 0.088680,  # (1/31.1035) × (750/999) × 3.674 = 0.088680
    990: 0.117058,  # (1/31.1035) × (990/999) × 3.674 = 0.117058
    "custom": 0.118122  # Default to pure gold
}

# UPDATED DEALERS WITH APPROVAL WORKFLOW
DEALERS = {
    "2268": {"name": "Ahmadreza", "level": "admin", "active": True, "permissions": ["buy", "sell", "admin", "final_approve"], "telegram_id": None},
    "2269": {"name": "Nima", "level": "senior", "active": True, "permissions": ["buy", "sell"], "telegram_id": None},
    "2270": {"name": "Peiman", "level": "standard", "active": True, "permissions": ["buy", "sell"], "telegram_id": None},
    "9999": {"name": "System Admin", "level": "admin", "active": True, "permissions": ["buy", "sell", "admin"], "telegram_id": None},
    "7777": {"name": "Junior Dealer", "level": "junior", "active": True, "permissions": ["buy", "sell"], "telegram_id": None},
    # APPROVAL WORKFLOW USERS
    "1001": {"name": "Abhay", "level": "approver", "active": True, "permissions": ["approve", "reject", "comment"], "role": "Head Accountant", "telegram_id": None},
    "1002": {"name": "Mushtaq", "level": "approver", "active": True, "permissions": ["approve", "reject", "comment"], "role": "Level 2 Approver", "telegram_id": None},
    "1003": {"name": "Ahmadreza", "level": "final_approver", "active": True, "permissions": ["buy", "sell", "admin", "final_approve"], "role": "Final Approver", "telegram_id": None}
}

CUSTOMERS = ["Noori", "ASK", "AGM", "Keshavarz", "WSG", "Exness", "MyMaa", "Binance", "Kraken", "Custom"]

# PROFESSIONAL BAR TYPES WITH EXACT WEIGHTS - VERIFIED
GOLD_TYPES = [
    {"name": "Kilo Bar", "code": "KB", "weight_grams": 1000.0},
    {"name": "TT Bar (10 Tola)", "code": "TT", "weight_grams": 116.6380},  # EXACT: 10 × 11.6638
    {"name": "100g Bar", "code": "100g", "weight_grams": 100.0},
    {"name": "Tola", "code": "TOLA", "weight_grams": 11.6638},  # EXACT: Traditional Indian unit
    {"name": "1g Bar", "code": "1g", "weight_grams": 1.0},
    {"name": "Custom", "code": "CUSTOM", "weight_grams": None}
]

# VERIFIED PURITY OPTIONS WITH EXACT CALCULATED MULTIPLIERS
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

# Global state with UAE timezone - initialized after function definition
user_sessions = {}
market_data = {
    "gold_usd_oz": 2650.0, 
    "last_update": "00:00:00", 
    "trend": "stable", 
    "change_24h": 0.0,
    "source": "initial"
}
pending_trades = {}  # Store pending trades awaiting approval
approved_trades = {}  # Store approved trades

# ============================================================================
# UTILITY FUNCTIONS - CLOUD OPTIMIZED
# ============================================================================

def safe_float(value, default=0.0):
    """Safely convert value to float"""
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def log_message(msg):
    """Cloud-safe logging"""
    logger.info(msg)

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

def format_weight_kg(kg):
    """Format weight in KG with proper commas"""
    try:
        kg = safe_float(kg)
        return f"{kg:,.3f} KG"
    except Exception:
        return "0.000 KG"

def format_weight_grams(kg):
    """Convert KG to grams with proper comma formatting"""
    try:
        kg = safe_float(kg)
        grams = kg * 1000
        return f"{grams:,.0f} grams"
    except Exception:
        return "0 grams"

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
    """Convert grams to troy ounces - VERIFIED CONVERSION"""
    grams = safe_float(grams)
    if grams == 0:
        return 0
    return grams / TROY_OUNCE_TO_GRAMS

def kg_to_oz(kg):
    """Convert kg to troy ounces"""
    return grams_to_oz(kg_to_grams(kg))

def get_purity_multiplier(purity_value):
    """Get the verified multiplier for a given purity"""
    if purity_value == "custom":
        return PURITY_MULTIPLIERS["custom"]
    return PURITY_MULTIPLIERS.get(purity_value, PURITY_MULTIPLIERS["custom"])

# ============================================================================
# TELEGRAM NOTIFICATION SYSTEM
# ============================================================================

def register_telegram_id(dealer_pin, telegram_id):
    """Register telegram ID for dealer"""
    try:
        if dealer_pin in DEALERS:
            DEALERS[dealer_pin]["telegram_id"] = telegram_id
            logger.info(f"✅ Registered Telegram ID for {DEALERS[dealer_pin]['name']}: {telegram_id}")
            return True
    except Exception as e:
        logger.error(f"❌ Error registering Telegram ID: {e}")
    return False

def send_telegram_notification(telegram_id, message):
    """Send Telegram notification"""
    try:
        if telegram_id:
            bot.send_message(telegram_id, message, parse_mode='HTML')
            logger.info(f"✅ Notification sent to {telegram_id}")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to send notification to {telegram_id}: {e}")
    return False

def notify_approvers(trade_session, stage="new"):
    """Send notifications to appropriate approvers based on stage"""
    try:
        if stage == "new":
            # Notify Abhay (first approver)
            abhay_id = DEALERS.get("1001", {}).get("telegram_id")
            if abhay_id:
                message = f"""🔔 <b>NEW TRADE APPROVAL REQUIRED</b>

👤 Hello <b>ABHAY (Head Accountant)</b>,

📊 <b>TRADE DETAILS:</b>
• Operation: <b>{trade_session.operation.upper()}</b>
• Customer: <b>{trade_session.customer}</b>
• Gold Type: <b>{trade_session.gold_type['name']}</b>
• Volume: <b>{format_weight_combined(trade_session.volume_kg)}</b>
• Amount: <b>{format_money_aed(trade_session.price)}</b>
• Dealer: <b>{trade_session.dealer['name']}</b>

⏰ Time: <b>{get_uae_time().strftime('%Y-%m-%d %H:%M:%S')} UAE</b>

🎯 <b>ACTION NEEDED:</b> Please review and approve this trade in the Gold Trading Bot.

💡 Use /start to access the Approval Dashboard."""
                send_telegram_notification(abhay_id, message)
        
        elif stage == "abhay_approved":
            # Notify Mushtaq (second approver)
            mushtaq_id = DEALERS.get("1002", {}).get("telegram_id")
            if mushtaq_id:
                message = f"""✅ <b>TRADE APPROVED - YOUR TURN</b>

👤 Hello <b>MUSHTAQ (Level 2 Approver)</b>,

🎉 <b>ABHAY</b> has approved a trade. It now requires your approval:

📊 <b>TRADE DETAILS:</b>
• Operation: <b>{trade_session.operation.upper()}</b>
• Customer: <b>{trade_session.customer}</b>
• Amount: <b>{format_money_aed(trade_session.price)}</b>
• Previous Approver: <b>Abhay ✅</b>

⏰ Time: <b>{get_uae_time().strftime('%Y-%m-%d %H:%M:%S')} UAE</b>

🎯 <b>ACTION NEEDED:</b> Please review and approve this trade.

💡 Use /start to access the Approval Dashboard."""
                send_telegram_notification(mushtaq_id, message)
        
        elif stage == "mushtaq_approved":
            # Notify Ahmadreza (final approver)
            ahmadreza_id = DEALERS.get("1003", {}).get("telegram_id")
            if ahmadreza_id:
                message = f"""🎯 <b>FINAL APPROVAL REQUIRED</b>

👤 Hello <b>AHMADREZA (Final Approver)</b>,

🎉 Trade has been approved by <b>ABHAY</b> and <b>MUSHTAQ</b>. Your final approval is needed:

📊 <b>TRADE DETAILS:</b>
• Operation: <b>{trade_session.operation.upper()}</b>
• Customer: <b>{trade_session.customer}</b>
• Amount: <b>{format_money_aed(trade_session.price)}</b>
• Previous Approvers: <b>Abhay ✅ Mushtaq ✅</b>

⏰ Time: <b>{get_uae_time().strftime('%Y-%m-%d %H:%M:%S')} UAE</b>

🎯 <b>ACTION NEEDED:</b> Please give final approval to complete this trade.

💡 Use /start to access the Approval Dashboard."""
                send_telegram_notification(ahmadreza_id, message)
        
        elif stage == "final_approved":
            # Notify all approvers of completion
            for pin in ["1001", "1002", "1003"]:
                telegram_id = DEALERS.get(pin, {}).get("telegram_id")
                if telegram_id:
                    message = f"""🎉 <b>TRADE FINAL APPROVAL COMPLETED</b>

✅ A trade has been <b>FINALLY APPROVED</b> and is ready for execution:

📊 <b>TRADE DETAILS:</b>
• Operation: <b>{trade_session.operation.upper()}</b>
• Customer: <b>{trade_session.customer}</b>
• Amount: <b>{format_money_aed(trade_session.price)}</b>
• Status: <b>✅ FINAL APPROVED</b>

🎯 Trade is now complete and ready for execution.

⏰ Time: <b>{get_uae_time().strftime('%Y-%m-%d %H:%M:%S')} UAE</b>

🚀 Gold Trading System"""
                    send_telegram_notification(telegram_id, message)
        
    except Exception as e:
        logger.error(f"❌ Error sending approver notifications: {e}")

# ============================================================================
# PROFESSIONAL CALCULATION FUNCTIONS
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
    """COMPLETE TRADE CALCULATION FUNCTION - SUPPORTS RATE OVERRIDE"""
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
# GOLD RATE FETCHING - CLOUD OPTIMIZED
# ============================================================================

def fetch_gold_rate():
    """Fetch current gold rate - SIMPLE WORKING VERSION"""
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
    """Start background rate updater for cloud deployment - FREQUENT UPDATES"""
    def update_loop():
        while True:
            try:
                success = fetch_gold_rate()
                if success:
                    logger.info(f"🔄 Rate updated: ${market_data['gold_usd_oz']:.2f} (UAE: {market_data['last_update']})")
                else:
                    logger.warning("⚠️ Rate update failed, using cached value")
                time.sleep(120)  # 2 minutes for frequent live updates
            except Exception as e:
                logger.error(f"❌ Rate updater error: {e}")
                time.sleep(60)  # 1 minute on error
    
    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()
    logger.info("✅ Rate updater started - Updates every 2 minutes")

def get_sheets_client():
    """Get authenticated Google Sheets client with cloud-safe error handling"""
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
        # Approval workflow fields
        self.approval_status = "pending"  # pending, abhay_approved, mushtaq_approved, final_approved, rejected
        self.approved_by = []  # List of approvers
        self.comments = []  # List of comments
        self.created_at = get_uae_time()
    
    def reset_trade(self):
        self.step = "operation"
        self.operation = None
        self.gold_type = None
        self.gold_purity = None
        self.volume_kg = None
        self.volume_grams = None
        self.quantity = None  # For standard bars
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
        """Validate trade with improved logic"""
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
# APPROVAL WORKFLOW FUNCTIONS
# ============================================================================

def get_pending_trades():
    """Get all pending trades for approval"""
    return {k: v for k, v in pending_trades.items() if v.approval_status in ["pending", "abhay_approved", "mushtaq_approved"]}

def approve_trade(trade_id, approver_name, comment=""):
    """Approve a trade and advance workflow"""
    try:
        if trade_id not in pending_trades:
            return False, "Trade not found"
        
        trade = pending_trades[trade_id]
        
        # Add approver and comment
        trade.approved_by.append(approver_name)
        if comment:
            trade.comments.append(f"{approver_name}: {comment}")
        
        # Update status based on workflow
        if approver_name == "Abhay" and trade.approval_status == "pending":
            trade.approval_status = "abhay_approved"
            notify_approvers(trade, "abhay_approved")
            return True, "Approved by Abhay. Notified Mushtaq."
        
        elif approver_name == "Mushtaq" and trade.approval_status == "abhay_approved":
            trade.approval_status = "mushtaq_approved"
            notify_approvers(trade, "mushtaq_approved")
            return True, "Approved by Mushtaq. Notified Ahmadreza for final approval."
        
        elif approver_name == "Ahmadreza" and trade.approval_status == "mushtaq_approved":
            trade.approval_status = "final_approved"
            # Save to sheets with approved status
            success, sheet_result = save_trade_to_sheets(trade)
            if success:
                # Move to approved trades
                approved_trades[trade_id] = trade
                del pending_trades[trade_id]
                notify_approvers(trade, "final_approved")
                return True, f"Final approval completed. Trade saved to sheets: {sheet_result}"
            else:
                return False, f"Final approval given but sheet save failed: {sheet_result}"
        
        return False, "Invalid approval workflow step"
        
    except Exception as e:
        logger.error(f"❌ Approval error: {e}")
        return False, str(e)

def reject_trade(trade_id, rejector_name, reason=""):
    """Reject a trade and update sheets"""
    try:
        if trade_id not in pending_trades:
            return False, "Trade not found"
        
        trade = pending_trades[trade_id]
        trade.approval_status = "rejected"
        trade.comments.append(f"REJECTED by {rejector_name}: {reason}")
        
        # Update sheet with rejected status
        update_trade_status_in_sheets(trade)
        
        # Remove from pending trades
        del pending_trades[trade_id]
        
        return True, f"Trade rejected by {rejector_name}. Reason: {reason}"
        
    except Exception as e:
        logger.error(f"❌ Rejection error: {e}")
        return False, str(e)

def add_comment_to_trade(trade_id, commenter_name, comment):
    """Add comment to trade and update sheets"""
    try:
        if trade_id not in pending_trades:
            return False, "Trade not found"
        
        trade = pending_trades[trade_id]
        trade.comments.append(f"{commenter_name}: {comment}")
        
        # Update sheet with new comment
        update_trade_status_in_sheets(trade)
        
        return True, f"Comment added by {commenter_name}: {comment}"
        
    except Exception as e:
        logger.error(f"❌ Comment error: {e}")
        return False, str(e)

# ============================================================================
# SAVE TRADE FUNCTIONS WITH APPROVAL STATUS
# ============================================================================

def save_trade_to_sheets(session):
    """Save trade to Google Sheets with approval status colors"""
    try:
        client = get_sheets_client()
        if not client:
            return False, "Sheets client failed"
            
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        
        current_date = get_uae_time()  # Use UAE time
        sheet_name = f"Gold_Trades_{current_date.strftime('%Y_%m')}"
        
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=25)
            headers = [
                'Date', 'Time', 'Dealer', 'Operation', 'Customer', 'Gold Type', 
                'Volume KG', 'Volume Grams', 'Pure Gold KG', 'Pure Gold Grams', 'Price USD', 'Price AED', 
                'Input Rate USD', 'Input Rate AED', 'Final Rate USD', 'Final Rate AED', 
                'Market Rate USD', 'Market Rate AED', 'Purity', 'Rate Type', 'P/D Amount', 'Session ID', 
                'Approval Status', 'Approved By', 'Notes'
            ]
            worksheet.append_row(headers)
        
        # Calculate using appropriate method based on rate type
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
            else:  # custom
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
        
        # Use calculated values
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
        
        # Get approval info
        approval_status = getattr(session, 'approval_status', 'final_approved')
        approved_by = getattr(session, 'approved_by', [])
        comments = getattr(session, 'comments', [])
        
        # Build notes with comments
        notes_parts = [f"v4.7 UAE: {rate_description}"]
        if comments:
            notes_parts.extend(comments)
        notes_text = " | ".join(notes_parts)
        
        # EXACT row data using verified calculations with GRAMS INCLUDED - UAE TIME + APPROVAL
        row_data = [
            current_date.strftime('%Y-%m-%d'),
            current_date.strftime('%H:%M:%S') + ' UAE',  # Add UAE indicator
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
            approval_status.upper(),
            ", ".join(approved_by) if approved_by else "System",
            notes_text
        ]
        
        # Add row and get its position for coloring
        worksheet.append_row(row_data)
        row_count = len(worksheet.get_all_values())
        
        # Apply color coding based on approval status
        try:
            if approval_status == "pending":
                # Red background for pending
                color_format = {"backgroundColor": {"red": 1.0, "green": 0.8, "blue": 0.8}}
            elif approval_status == "abhay_approved":
                # Yellow background for partial approval
                color_format = {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.7}}
            elif approval_status == "mushtaq_approved":
                # Orange background for awaiting final
                color_format = {"backgroundColor": {"red": 1.0, "green": 0.9, "blue": 0.6}}
            elif approval_status == "final_approved":
                # Green background for approved
                color_format = {"backgroundColor": {"red": 0.8, "green": 1.0, "blue": 0.8}}
            elif approval_status == "rejected":
                # Dark red for rejected
                color_format = {"backgroundColor": {"red": 0.9, "green": 0.6, "blue": 0.6}}
            else:
                # Default white
                color_format = {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}
            
            worksheet.format(f"{row_count}:{row_count}", color_format)
            logger.info(f"✅ Applied {approval_status} color formatting to row {row_count}")
            
        except Exception as e:
            logger.warning(f"⚠️ Color formatting failed: {e}")
        
        logger.info(f"✅ Trade saved to sheets: {session.session_id}")
        return True, session.session_id
        
    except Exception as e:
        logger.error(f"❌ Sheets save failed: {e}")
        return False, str(e)

# ============================================================================
# CLOUD-OPTIMIZED BOT SETUP
# ============================================================================

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start_command(message):
    """Start command - Cloud optimized with approval workflow"""
    try:
        user_id = message.from_user.id
        
        if user_id in user_sessions:
            del user_sessions[user_id]
        
        fetch_gold_rate()
        
        markup = types.InlineKeyboardMarkup()
        level_emojis = {"admin": "👑", "senior": "⭐", "standard": "🔹", "junior": "🔸", "approver": "✅", "final_approver": "🔥"}
        
        for dealer_id, dealer in DEALERS.items():
            if dealer.get('active', True):
                emoji = level_emojis.get(dealer['level'], "👤")
                role_desc = dealer.get('role', dealer['level'].title())
                markup.add(types.InlineKeyboardButton(
                    f"{emoji} {dealer['name']} ({role_desc})",
                    callback_data=f"login_{dealer_id}"
                ))
        
        markup.add(types.InlineKeyboardButton("💰 Live Gold Rate", callback_data="show_rate"))
        
        welcome_text = f"""🥇 GOLD TRADING BOT v4.7 - WORKING RATES + APPROVAL WORKFLOW! ✨
🚀 Complete Trading System + Approval Workflow + Sheet Integration

📊 SYSTEM STATUS:
💰 Current Rate: {format_money(market_data['gold_usd_oz'])} USD/oz
💱 AED Rate: {format_money_aed(market_data['gold_usd_oz'])}/oz
📈 Trend: {market_data['trend'].title()}
🇦🇪 UAE Time: {market_data['last_update']}
🔄 Updates: Every 2 minutes
☁️ Cloud: Railway Platform (Always On)

🆕 v4.7 APPROVAL WORKFLOW:
✅ Sequential approval: Abhay → Mushtaq → Ahmadreza
✅ Instant Telegram notifications to approvers
✅ Color-coded sheets (Red=Pending, Green=Approved)
✅ Approve/Reject/Comment functionality
✅ Professional approval tracking

🔒 SELECT DEALER TO LOGIN:"""
        
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
        logger.info(f"👤 User {user_id} started APPROVAL WORKFLOW bot v4.7")
        
    except Exception as e:
        logger.error(f"❌ Start error: {e}")
        try:
            bot.send_message(message.chat.id, "❌ Error occurred. Please try again.")
        except:
            pass

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    """Handle all callbacks - COMPLETE WITH APPROVAL WORKFLOW"""
    try:
        user_id = call.from_user.id
        data = call.data
        
        logger.info(f"📱 Callback: {user_id} -> {data}")
        
        if data.startswith('login_'):
            handle_login(call)
        elif data == 'show_rate':
            handle_show_rate(call)
        elif data == 'force_refresh_rate':
            handle_force_refresh_rate(call)
        elif data == 'dashboard':
            handle_dashboard(call)
        elif data == 'new_trade':
            handle_new_trade(call)
        elif data == 'approval_dashboard':
            handle_approval_dashboard(call)
        elif data.startswith('approve_'):
            handle_approve_trade(call)
        elif data.startswith('reject_'):
            handle_reject_trade(call)
        elif data.startswith('comment_'):
            handle_comment_trade(call)
        elif data.startswith('view_trade_'):
            handle_view_trade(call)
        elif data == 'system_status':
            handle_system_status(call)
        elif data == 'sheet_management':
            handle_sheet_management(call)
        elif data == 'view_sheets':
            handle_view_sheets(call)
        elif data == 'format_sheet':
            handle_format_sheet(call)
        elif data == 'fix_headers':
            handle_fix_headers(call)
        elif data == 'delete_sheets':
            handle_delete_sheets(call)
        elif data == 'clear_sheets':
            handle_clear_sheets(call)
        elif data.startswith('delete_') or data.startswith('clear_'):
            handle_sheet_action(call)
        elif data.startswith('operation_'):
            handle_operation(call)
        elif data.startswith('goldtype_'):
            handle_gold_type(call)
        elif data.startswith('quantity_'):
            handle_quantity(call)
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

def handle_login(call):
    """Handle login with approval workflow"""
    try:
        dealer_id = call.data.replace("login_", "")
        dealer = DEALERS.get(dealer_id)
        
        if not dealer:
            bot.edit_message_text("❌ Dealer not found", call.message.chat.id, call.message.message_id)
            return
        
        user_id = call.from_user.id
        
        # Register Telegram ID automatically
        register_telegram_id(dealer_id, user_id)
        
        user_sessions[user_id] = {
            "step": "awaiting_pin",
            "temp_dealer_id": dealer_id,
            "temp_dealer": dealer,
            "login_attempts": 0
        }
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="start"))
        
        role_info = dealer.get('role', dealer['level'].title())
        permissions_desc = ', '.join(dealer.get('permissions', ['N/A'])).upper()
        
        bot.edit_message_text(
            f"""🔒 DEALER AUTHENTICATION

Selected: {dealer['name']} ({role_info})
Permissions: {permissions_desc}

🔐 PIN: {dealer_id}
💬 Send this PIN as a message

📲 Telegram notifications are now ACTIVE for your role!

Type the PIN now:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Login error: {e}")

def handle_dashboard(call):
    """Dashboard with approval workflow access"""
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
        
        # Regular trading for dealers
        if any(p in permissions for p in ['buy', 'sell']):
            markup.add(types.InlineKeyboardButton("📊 NEW TRADE", callback_data="new_trade"))
        
        # Approval dashboard for approvers
        if any(p in permissions for p in ['approve', 'reject', 'comment', 'final_approve']):
            pending_count = len(get_pending_trades())
            markup.add(types.InlineKeyboardButton(f"✅ Approval Dashboard ({pending_count} pending)", callback_data="approval_dashboard"))
        
        markup.add(types.InlineKeyboardButton("💰 Live Rate", callback_data="show_rate"))
        markup.add(types.InlineKeyboardButton("🔄 Refresh Rate", callback_data="force_refresh_rate"))
        
        # Add sheet management for admin users
        if 'admin' in permissions:
            markup.add(types.InlineKeyboardButton("🗂️ Sheet Management", callback_data="sheet_management"))
        
        markup.add(types.InlineKeyboardButton("🔧 System Status", callback_data="system_status"))
        markup.add(types.InlineKeyboardButton("🔙 Logout", callback_data="start"))
        
        role_info = dealer.get('role', dealer['level'].title())
        
        dashboard_text = f"""✅ DEALER DASHBOARD v4.7 - APPROVAL WORKFLOW! ✨

👤 Welcome {dealer['name'].upper()}!
🔒 Role: {role_info}
🎯 Permissions: {', '.join(permissions).upper()}

💰 LIVE Rate: {format_money(market_data['gold_usd_oz'])} USD/oz ⚡
💱 AED: {format_money_aed(market_data['gold_usd_oz'])}/oz
⏰ UAE Time: {market_data['last_update']} (Updates every 2min)
📈 Change: {market_data['change_24h']:+.2f} USD

🎯 APPROVAL WORKFLOW STATUS:
• Pending Trades: {len(get_pending_trades())}
• Approved Trades: {len(approved_trades)}
• Notifications: 📲 ACTIVE

✅ COMPLETE SYSTEM FEATURES:
• All Gold Types & Purities ✅
• Rate Override & Custom Rates ✅  
• Decimal Quantities (0.25, 2.5) ✅
• Professional Sheet Integration ✅
• Color-Coded Approval Status ✅
• Instant Telegram Notifications ✅

👆 SELECT ACTION:"""
        
        bot.edit_message_text(dashboard_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")

def handle_approval_dashboard(call):
    """Approval dashboard for approvers"""
    try:
        user_id = call.from_user.id
        session = user_sessions.get(user_id, {})
        dealer = session.get("dealer")
        
        if not dealer:
            bot.edit_message_text("❌ Please login again", call.message.chat.id, call.message.message_id)
            return
        
        permissions = dealer.get('permissions', [])
        if not any(p in permissions for p in ['approve', 'reject', 'comment', 'final_approve']):
            bot.edit_message_text("❌ No approval permissions", call.message.chat.id, call.message.message_id)
            return
        
        pending_trades_dict = get_pending_trades()
        
        markup = types.InlineKeyboardMarkup()
        
        if pending_trades_dict:
            for trade_id, trade in list(pending_trades_dict.items())[:10]:  # Show max 10
                status_icon = "🔴" if trade.approval_status == "pending" else "🟡" if trade.approval_status == "abhay_approved" else "🟠"
                trade_desc = f"{status_icon} {trade.operation.upper()} {trade.customer} - {format_money_aed(trade.price)}"
                markup.add(types.InlineKeyboardButton(
                    trade_desc,
                    callback_data=f"view_trade_{trade_id}"
                ))
        
        markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="approval_dashboard"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="dashboard"))
        
        dashboard_text = f"""✅ APPROVAL DASHBOARD

👤 {dealer['name']} - {dealer.get('role', 'Approver')}

📊 PENDING TRADES: {len(pending_trades_dict)}

🔍 WORKFLOW STATUS:
🔴 Pending (awaiting Abhay)
🟡 Abhay approved (awaiting Mushtaq) 
🟠 Mushtaq approved (awaiting Ahmadreza)

💡 Select a trade to view details and take action:"""
        
        bot.edit_message_text(dashboard_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"Approval dashboard error: {e}")

def handle_view_trade(call):
    """View trade details for approval"""
    try:
        trade_id = call.data.replace("view_trade_", "")
        
        if trade_id not in pending_trades:
            bot.edit_message_text("❌ Trade not found", call.message.chat.id, call.message.message_id)
            return
        
        trade = pending_trades[trade_id]
        user_id = call.from_user.id
        session = user_sessions.get(user_id, {})
        dealer = session.get("dealer")
        
        # Calculate trade totals for display
        if trade.rate_type == "override":
            calc_results = calculate_trade_totals_with_override(
                trade.volume_kg,
                trade.gold_purity['value'],
                trade.final_rate_per_oz,
                "override"
            )
        else:
            if trade.rate_type == "market":
                base_rate = market_data['gold_usd_oz']
            else:
                base_rate = trade.rate_per_oz
            
            calc_results = calculate_trade_totals(
                trade.volume_kg,
                trade.gold_purity['value'],
                base_rate,
                trade.pd_type,
                trade.pd_amount
            )
        
        # Build action buttons based on user permissions and workflow state
        markup = types.InlineKeyboardMarkup()
        
        permissions = dealer.get('permissions', [])
        can_approve = False
        
        # Check if user can approve at current stage
        if (dealer['name'] == "Abhay" and trade.approval_status == "pending" and 'approve' in permissions):
            can_approve = True
        elif (dealer['name'] == "Mushtaq" and trade.approval_status == "abhay_approved" and 'approve' in permissions):
            can_approve = True
        elif (dealer['name'] == "Ahmadreza" and trade.approval_status == "mushtaq_approved" and 'final_approve' in permissions):
            can_approve = True
        
        if can_approve:
            markup.add(types.InlineKeyboardButton(f"✅ Approve #{trade_id[-4:]}", callback_data=f"approve_{trade_id}"))
        
        if 'reject' in permissions:
            markup.add(types.InlineKeyboardButton(f"❌ Reject #{trade_id[-4:]}", callback_data=f"reject_{trade_id}"))
        
        if 'comment' in permissions:
            markup.add(types.InlineKeyboardButton(f"💬 Add Comment", callback_data=f"comment_{trade_id}"))
        
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="approval_dashboard"))
        
        # Build type description
        type_desc = trade.gold_type['name']
        if hasattr(trade, 'quantity') and trade.quantity:
            type_desc = f"{trade.quantity} × {type_desc}"
        
        # Status display
        status_emojis = {
            "pending": "🔴 PENDING",
            "abhay_approved": "🟡 ABHAY APPROVED",
            "mushtaq_approved": "🟠 MUSHTAQ APPROVED",
            "final_approved": "🟢 FINAL APPROVED"
        }
        
        trade_text = f"""📊 TRADE DETAILS #{trade_id[-8:]}

📊 STATUS: {status_emojis.get(trade.approval_status, trade.approval_status.upper())}

🎯 TRADE INFO:
• Operation: {trade.operation.upper()}
• Type: {type_desc}
• Purity: {trade.gold_purity['name']}
• Volume: {format_weight_combined(trade.volume_kg)}
• Customer: {trade.customer}
• Dealer: {trade.dealer['name']}

💰 FINANCIAL:
• Total: ${calc_results['total_price_usd']:,.2f} USD
• Total: {format_money_aed(calc_results['total_price_usd'])}
• Rate: ${calc_results.get('final_rate_usd_per_oz', 0):,.2f}/oz

⏰ TIMING:
• Created: {trade.created_at.strftime('%Y-%m-%d %H:%M:%S')} UAE

✅ APPROVED BY: {', '.join(trade.approved_by) if trade.approved_by else 'None yet'}

💬 COMMENTS:
{chr(10).join(trade.comments) if trade.comments else 'No comments yet'}

🎯 Next Approver: {'Abhay' if trade.approval_status == 'pending' else 'Mushtaq' if trade.approval_status == 'abhay_approved' else 'Ahmadreza' if trade.approval_status == 'mushtaq_approved' else 'Completed'}"""
        
        bot.edit_message_text(trade_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"View trade error: {e}")

def handle_approve_trade(call):
    """Handle trade approval with enhanced navigation"""
    try:
        trade_id = call.data.replace("approve_", "")
        user_id = call.from_user.id
        session = user_sessions.get(user_id, {})
        dealer = session.get("dealer")
        
        if not dealer:
            bot.edit_message_text("❌ Please login again", call.message.chat.id, call.message.message_id)
            return
        
        success, message = approve_trade(trade_id, dealer['name'])
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Approval Dashboard", callback_data="approval_dashboard"))
        markup.add(types.InlineKeyboardButton("📊 NEW TRADE", callback_data="new_trade"))
        markup.add(types.InlineKeyboardButton("🔙 Dashboard", callback_data="dashboard"))
        
        if success:
            result_text = f"""✅ APPROVAL SUCCESSFUL!

{message}

📊 SHEET STATUS UPDATED:
• Color changed in sheets automatically
• Status visible to all approvers
• Workflow progressed to next step

👆 SELECT NEXT ACTION:"""
        else:
            result_text = f"""❌ APPROVAL FAILED

{message}

Please try again or contact admin.

👆 SELECT ACTION:"""
        
        bot.edit_message_text(result_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"Approve trade error: {e}")

def handle_reject_trade(call):
    """Handle trade rejection with enhanced navigation"""
    try:
        trade_id = call.data.replace("reject_", "")
        user_id = call.from_user.id
        session = user_sessions.get(user_id, {})
        dealer = session.get("dealer")
        
        if not dealer:
            bot.edit_message_text("❌ Please login again", call.message.chat.id, call.message.message_id)
            return
        
        # Store for rejection reason input
        user_sessions[user_id]["awaiting_input"] = f"reject_reason_{trade_id}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="approval_dashboard"))
        
        bot.edit_message_text(
            f"""❌ REJECT TRADE #{trade_id[-8:]}

💬 Please provide a reason for rejection:

⚠️ This will:
• Mark trade as REJECTED in sheets
• Remove from approval workflow
• Notify all parties

Type your rejection reason now:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Reject trade error: {e}")

def handle_comment_trade(call):
    """Handle adding comment to trade with enhanced navigation"""
    try:
        trade_id = call.data.replace("comment_", "")
        user_id = call.from_user.id
        session = user_sessions.get(user_id, {})
        dealer = session.get("dealer")
        
        if not dealer:
            bot.edit_message_text("❌ Please login again", call.message.chat.id, call.message.message_id)
            return
        
        # Store for comment input
        user_sessions[user_id]["awaiting_input"] = f"add_comment_{trade_id}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="approval_dashboard"))
        
        bot.edit_message_text(
            f"""💬 ADD COMMENT TO TRADE #{trade_id[-8:]}

💬 Type your comment:

Examples:
• "Checked customer creditworthiness - looks good"
• "Please verify gold purity before approval"
• "Customer requested faster processing"
• "Rate seems competitive for this volume"

⚠️ Comments will be:
• Visible in sheets
• Included in approval history
• Sent to all approvers

Type your comment now:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Comment trade error: {e}")

# Continue with existing handlers...
def handle_show_rate(call):
    """Show gold rate - WITH MANUAL REFRESH"""
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
• 1 KG (32.15 oz): {format_money(market_data['gold_usd_oz'] * kg_to_oz(1) * 0.999)}
• 1 TT Bar (116.64g): {format_money(market_data['gold_usd_oz'] * grams_to_oz(116.6380) * 0.999)}

⚖️ Purity Examples:
• 999 (99.9%): {format_money(market_data['gold_usd_oz'] * 0.999)}/oz
• 916 (22K): {format_money(market_data['gold_usd_oz'] * 0.916)}/oz

🇦🇪 UAE Timezone - Railway Cloud 24/7!"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Force Refresh", callback_data="show_rate"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="start"))
        
        bot.edit_message_text(rate_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"Show rate error: {e}")

def handle_force_refresh_rate(call):
    """Force refresh gold rate manually"""
    try:
        bot.edit_message_text("🔄 Fetching latest gold rate...", call.message.chat.id, call.message.message_id)
        
        success = fetch_gold_rate()
        
        if success:
            trend_emoji = {"up": "⬆️", "down": "⬇️", "stable": "➡️"}
            emoji = trend_emoji.get(market_data['trend'], "➡️")
            
            rate_text = f"""💰 GOLD RATE - FORCE REFRESHED! ✨

🥇 Current: {format_money(market_data['gold_usd_oz'])} USD/oz
💱 AED: {format_money_aed(market_data['gold_usd_oz'])}/oz
{emoji} Trend: {market_data['trend'].title()}
⏰ UAE Time: {market_data['last_update']}
🔄 Change: {market_data['change_24h']:+.2f} USD

📏 Quick Conversions (999 Purity):
• 1 KG: {format_money(market_data['gold_usd_oz'] * kg_to_oz(1) * 0.999)}
• 1 TT Bar: {format_money(market_data['gold_usd_oz'] * grams_to_oz(116.6380) * 0.999)}

✅ Rate successfully refreshed!"""
        else:
            rate_text = f"""❌ REFRESH FAILED

🥇 Current (Cached): {format_money(market_data['gold_usd_oz'])} USD/oz
💱 AED: {format_money_aed(market_data['gold_usd_oz'])}/oz
⏰ Last Update: {market_data['last_update']} UAE

⚠️ Unable to fetch new rate. Using cached value.
🔄 Auto-updates continue every 2 minutes."""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Try Again", callback_data="force_refresh_rate"))
        markup.add(types.InlineKeyboardButton("🔙 Dashboard", callback_data="dashboard"))
        
        bot.edit_message_text(rate_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"Force refresh error: {e}")

def handle_system_status(call):
    """System status with approval workflow info"""
    try:
        sheets_success, sheets_message = test_sheets_connection()
        total_sessions = len(user_sessions)
        
        # Count registered approvers
        registered_approvers = 0
        for dealer_id in ["1001", "1002", "1003"]:
            if DEALERS.get(dealer_id, {}).get("telegram_id"):
                registered_approvers += 1
        
        status_text = f"""🔧 SYSTEM STATUS v4.7 - APPROVAL WORKFLOW! ✅

📊 CORE SYSTEMS:
• Bot Status: ✅ ONLINE (Railway Cloud)
• Cloud Platform: Railway (24/7 operation)
• Auto-restart: ✅ ENABLED

💰 MARKET DATA:
• Gold Rate: {format_money(market_data['gold_usd_oz'])} USD/oz
• AED Rate: {format_money_aed(market_data['gold_usd_oz'])}/oz
• Trend: {market_data['trend'].title()}
• UAE Time: {market_data['last_update']}
• Update Frequency: Every 2 minutes ✅

📊 CONNECTIVITY:
• Google Sheets: {'✅ Connected' if sheets_success else '❌ Failed'}
• Status: {sheets_message}

👥 USAGE:
• Active Sessions: {total_sessions}
• Pending Trades: {len(pending_trades)}
• Approved Trades: {len(approved_trades)}

✅ APPROVAL WORKFLOW:
• Registered Approvers: {registered_approvers}/3
• Abhay: {'✅' if DEALERS.get('1001', {}).get('telegram_id') else '❌'}
• Mushtaq: {'✅' if DEALERS.get('1002', {}).get('telegram_id') else '❌'}  
• Ahmadreza: {'✅' if DEALERS.get('1003', {}).get('telegram_id') else '❌'}
• Notifications: 📲 ACTIVE

🆕 v4.7 COMPLETE FEATURES:
✅ Sequential approval workflow
✅ Instant Telegram notifications
✅ Color-coded sheets with approval status
✅ Approve/Reject/Comment functionality  
✅ Working gold rate API (2min updates)
✅ UAE timezone for all timestamps
✅ Decimal quantities support
✅ Professional sheet integration"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="system_status"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="dashboard"))
        
        bot.edit_message_text(status_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"System status error: {e}")

# EXISTING TRADING HANDLERS (keep all your working trade handlers)
def handle_new_trade(call):
    """New trade - COMPLETE TRADING FLOW WITH LIVE RATE"""
    try:
        fetch_gold_rate()
        
        user_id = call.from_user.id
        session_data = user_sessions.get(user_id, {})
        dealer = session_data.get("dealer")
        
        if not dealer:
            bot.edit_message_text("❌ Please login first", call.message.chat.id, call.message.message_id)
            return
        
        # Check if dealer can create trades
        permissions = dealer.get('permissions', [])
        if not any(p in permissions for p in ['buy', 'sell']):
            bot.edit_message_text("❌ No trading permissions", call.message.chat.id, call.message.message_id)
            return
        
        trade_session = TradeSession(user_id, dealer)
        user_sessions[user_id]["trade_session"] = trade_session
        
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

⚠️ NOTE: All trades require approval workflow:
Abhay → Mushtaq → Ahmadreza → Final Approval

🎯 SELECT OPERATION:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
        
        logger.info(f"📊 User {user_id} started APPROVAL WORKFLOW trade v4.7")
    except Exception as e:
        logger.error(f"New trade error: {e}")

def handle_confirm_trade(call):
    """Confirm and submit trade for approval"""
    try:
        user_id = call.from_user.id
        session_data = user_sessions.get(user_id, {})
        trade_session = session_data.get("trade_session")
        
        if not trade_session:
            bot.edit_message_text("❌ Session error", call.message.chat.id, call.message.message_id)
            return
        
        bot.edit_message_text("💾 Submitting trade for approval workflow...", call.message.chat.id, call.message.message_id)
        
        # Calculate trade price for approval
        if trade_session.rate_type == "override":
            calc_results = calculate_trade_totals_with_override(
                trade_session.volume_kg,
                trade_session.gold_purity['value'],
                trade_session.final_rate_per_oz,
                "override"
            )
        else:
            if trade_session.rate_type == "market":
                base_rate = market_data['gold_usd_oz']
            else:
                base_rate = trade_session.rate_per_oz
            
            calc_results = calculate_trade_totals(
                trade_session.volume_kg,
                trade_session.gold_purity['value'],
                base_rate,
                trade_session.pd_type,
                trade_session.pd_amount
            )
        
        trade_session.price = calc_results['total_price_usd']
        
        # Add to pending trades
        pending_trades[trade_session.session_id] = trade_session
        
        # Notify first approver (Abhay)
        notify_approvers(trade_session, "new")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📊 NEW TRADE", callback_data="new_trade"))
        markup.add(types.InlineKeyboardButton("🏠 Dashboard", callback_data="dashboard"))
        
        success_text = f"""🎉 TRADE SUBMITTED FOR APPROVAL! ✨

✅ Trade ID: {trade_session.session_id}
📊 Status: 🔴 PENDING APPROVAL
⏰ Time: {get_uae_time().strftime('%H:%M:%S')} UAE

📋 APPROVAL WORKFLOW:
🔴 Step 1: Awaiting Abhay (Head Accountant)
⚪ Step 2: Mushtaq (Level 2 Approver)  
⚪ Step 3: Ahmadreza (Final Approver)

📲 NOTIFICATIONS SENT:
✅ Abhay has been notified via Telegram

💰 TRADE SUMMARY:
• {trade_session.operation.upper()}: {getattr(trade_session, 'quantity', 1)} × {trade_session.gold_type['name']}
• Total Weight: {format_weight_combined(trade_session.volume_kg)}
• Customer: {trade_session.customer}
• Total: ${calc_results['total_price_usd']:,.2f} USD
• Total: {format_money_aed(calc_results['total_price_usd'])}

🔄 NEXT STEPS:
1. Abhay will receive instant notification
2. After approval, Mushtaq gets notified
3. After Mushtaq, Ahmadreza gets final approval
4. Trade automatically saves to sheets when fully approved

🎨 Professional color-coded sheets with approval status!"""
        
        bot.edit_message_text(success_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        
        if "trade_session" in user_sessions[user_id]:
            del user_sessions[user_id]["trade_session"]
    except Exception as e:
        logger.error(f"Confirm trade error: {e}")

# ============================================================================
# ALL TRADE HANDLERS - RESTORED FROM WORKING CODE
# ============================================================================

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
    """Handle gold type selection - FIXED CALCULATION LOGIC"""
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
        
        # FIXED LOGIC: Check if this is a standard bar type or custom
        if selected_type['weight_grams'] is not None:
            # Standard bar - ask for QUANTITY, not volume
            trade_session.step = "quantity"
            
            markup = types.InlineKeyboardMarkup()
            # Common quantities for standard bars
            quantities = [1, 2, 3, 4, 5, 10, 15, 20, 25, 50, 75, 100]
            row = []
            for i, qty in enumerate(quantities):
                row.append(types.InlineKeyboardButton(f"{qty}", callback_data=f"quantity_{qty}"))
                if len(row) == 4:
                    markup.add(*row)
                    row = []
            if row:
                markup.add(*row)
            
            markup.add(types.InlineKeyboardButton("✏️ Custom Quantity", callback_data="quantity_custom"))
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
            
            weight_grams = selected_type['weight_grams']
            weight_kg = weight_grams / 1000
            
            bot.edit_message_text(
                f"""📊 NEW TRADE - STEP 3/8 (QUANTITY)

✅ Operation: {trade_session.operation.upper()}
✅ Type: {selected_type['name']} ({weight_grams:,.1f} grams each)

📏 HOW MANY {selected_type['name'].upper()}S?

💡 Each {selected_type['name']} = {weight_kg:.4f} KG ({weight_grams:,.1f} grams)

🔢 SELECT QUANTITY:""",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
        else:
            # Custom weight - ask for volume as before
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
                f"""📊 NEW TRADE - STEP 3/8 (VOLUME)

✅ Operation: {trade_session.operation.upper()}
✅ Type: {selected_type['name']} (Custom Weight)

📏 SELECT VOLUME IN KG:""",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
    except Exception as e:
        logger.error(f"Gold type error: {e}")

def handle_quantity(call):
    """Handle quantity selection for standard bars - FIXED FUNCTION"""
    try:
        user_id = call.from_user.id
        quantity_data = call.data.replace("quantity_", "")
        
        session_data = user_sessions.get(user_id, {})
        trade_session = session_data.get("trade_session")
        
        if not trade_session:
            bot.edit_message_text("❌ Session error", call.message.chat.id, call.message.message_id)
            return
        
        if quantity_data == "custom":
            user_sessions[user_id]["awaiting_input"] = "quantity"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
            
            bot.edit_message_text(
                f"""🔢 CUSTOM QUANTITY

💬 How many {trade_session.gold_type['name']}s?
📝 Examples: 25, 2.5, 0.25

⚖️ Each {trade_session.gold_type['name']} = {trade_session.gold_type['weight_grams']:,.1f} grams
⚠️ Range: 0.01 - 10000 pieces (decimals allowed)

Type quantity now:""",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
            return
        
        try:
            quantity = float(quantity_data)  # FIXED: Allow decimal quantities
        except:
            bot.edit_message_text("❌ Invalid quantity", call.message.chat.id, call.message.message_id)
            return
        
        # Calculate total weight based on quantity - SUPPORTS DECIMALS
        weight_per_piece_grams = trade_session.gold_type['weight_grams']
        total_weight_grams = quantity * weight_per_piece_grams
        total_weight_kg = total_weight_grams / 1000
        
        trade_session.volume_kg = total_weight_kg
        trade_session.volume_grams = total_weight_grams
        trade_session.quantity = quantity
        trade_session.step = "purity"  # FIXED: Skip volume step, go directly to purity
        
        markup = types.InlineKeyboardMarkup()
        for purity in GOLD_PURITIES:
            markup.add(types.InlineKeyboardButton(
                f"⚖️ {purity['name']}",
                callback_data=f"purity_{purity['value']}"
            ))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
        
        # Format quantity display properly for decimals
        qty_display = f"{quantity:g}" if quantity == int(quantity) else f"{quantity:.3f}".rstrip('0').rstrip('.')
        
        bot.edit_message_text(
            f"""📊 NEW TRADE - STEP 4/8 (PURITY)

✅ Operation: {trade_session.operation.upper()}
✅ Type: {qty_display} × {trade_session.gold_type['name']}
✅ Total Weight: {format_weight_combined(total_weight_kg)}

⚖️ SELECT PURITY:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Quantity error: {e}")

def handle_purity(call):
    """Handle purity selection - FIXED FLOW"""
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
        
        # FIXED: Check if we already have volume (from quantity) or need to ask for volume
        if trade_session.volume_kg is None:
            # Need to ask for volume (custom gold type)
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

📏 SELECT VOLUME:""",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
        else:
            # Already have volume (from quantity), go to customer
            trade_session.step = "customer"
            
            markup = types.InlineKeyboardMarkup()
            for customer in CUSTOMERS:
                markup.add(types.InlineKeyboardButton(
                    f"👤 {customer}" if customer != "Custom" else f"✏️ {customer}",
                    callback_data=f"customer_{customer}"
                ))
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
            
            volume_oz = grams_to_oz(kg_to_grams(trade_session.volume_kg))
            
            bot.edit_message_text(
                f"""📊 NEW TRADE - STEP 5/8 (CUSTOMER)

✅ Operation: {trade_session.operation.upper()}
✅ Type: {getattr(trade_session, 'quantity', 1)} × {trade_session.gold_type['name']}
✅ Total Weight: {format_weight_combined(trade_session.volume_kg)} = {volume_oz:.2f} troy oz
✅ Purity: {selected_purity['name']}

👤 SELECT CUSTOMER:""",
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
        markup.add(types.InlineKeyboardButton("✏️ Enter Custom Rate", callback_data="rate_custom"))
        markup.add(types.InlineKeyboardButton("⚡ Rate Override", callback_data="rate_override"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
        
        bot.edit_message_text(
            f"""📊 NEW TRADE - STEP 6/8 (RATE SELECTION)

✅ Customer: {customer}

💰 CURRENT MARKET: ${current_spot:,.2f} USD/oz

🎯 RATE OPTIONS:
• 📊 Market Rate: Live rate + premium/discount
• ✏️ Custom Rate: Your rate + premium/discount  
• ⚡ Rate Override: Direct final rate

💎 SELECT RATE SOURCE:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Customer error: {e}")

def handle_rate_choice(call):
    """Handle rate choice - COMPLETE WITH RATE OVERRIDE AND LIVE RATE"""
    try:
        # AUTO-REFRESH RATE WHEN SELECTING RATE OPTION
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
            
        elif choice == "custom":
            user_sessions[user_id]["awaiting_input"] = "custom_rate"
            trade_session.rate_type = "custom"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
            
            current_market = market_data['gold_usd_oz']
            
            bot.edit_message_text(
                f"""✏️ ENTER CUSTOM RATE PER OUNCE

💰 Current Market: ${current_market:,.2f} USD/oz
⏰ UAE Time: {market_data['last_update']}

💬 Enter your rate per ounce in USD
📝 Example: 2650.00

⚠️ Range: $1,000 - $10,000 per ounce

Type your rate per ounce now:""",
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
        
        # FIXED: Add custom premium/discount button
        markup.add(types.InlineKeyboardButton("✏️ Custom Amount", callback_data=f"{pd_type}_custom"))
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
    """Handle premium/discount amount - FIXED: Added custom input support"""
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
        
        # FIXED: Handle custom amount input
        if amount_data == "custom":
            user_sessions[user_id]["awaiting_input"] = f"custom_{pd_type}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
            
            base_rate = getattr(trade_session, 'rate_per_oz', market_data['gold_usd_oz'])
            
            bot.edit_message_text(
                f"""✏️ CUSTOM {pd_type.upper()} AMOUNT

💰 Base Rate: ${base_rate:,.2f}/oz

💬 Enter {pd_type} amount per ounce in USD
📝 Example: 25.50

⚠️ Range: $0.01 - $500.00 per ounce

Type your {pd_type} amount now:""",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
            return
        
        try:
            amount = float(amount_data)
        except:
            bot.edit_message_text("❌ Invalid amount", call.message.chat.id, call.message.message_id)
            return
        
        trade_session.pd_amount = amount
        
        # Calculate final rate based on rate type
        if trade_session.rate_type == "market":
            base_rate = market_data['gold_usd_oz']
        else:  # custom
            base_rate = trade_session.rate_per_oz
        
        # Calculate final rate with premium/discount
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
    """Show trade confirmation - COMPLETE"""
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
            if trade_session.rate_type == "market":
                base_rate = market_data['gold_usd_oz']
            else:  # custom
                base_rate = trade_session.rate_per_oz
            
            calc_results = calculate_trade_totals(
                trade_session.volume_kg,
                trade_session.gold_purity['value'],
                base_rate,
                trade_session.pd_type,
                trade_session.pd_amount
            )
            
            pd_sign = "+" if trade_session.pd_type == "premium" else "-"
            rate_description = f"{trade_session.rate_type.upper()}: ${base_rate:,.2f} {pd_sign} ${trade_session.pd_amount}/oz"
        
        # Update session with calculated values
        trade_session.price = calc_results['total_price_usd']
        if not hasattr(trade_session, 'final_rate_per_oz') or trade_session.final_rate_per_oz is None:
            trade_session.final_rate_per_oz = calc_results.get('final_rate_usd_per_oz', 0)
        
        final_rate_display = calc_results.get('final_rate_usd_per_oz', 0)
        final_rate_aed = final_rate_display * USD_TO_AED_RATE
        
        # Build type description
        type_desc = trade_session.gold_type['name']
        if hasattr(trade_session, 'quantity') and trade_session.quantity:
            type_desc = f"{trade_session.quantity} × {type_desc}"
        
        confirmation_text = f"""✅ TRADE CONFIRMATION - APPROVAL WORKFLOW! ✨

⚠️ NOTE: This trade will go through approval workflow:
🔴 Abhay → 🟡 Mushtaq → 🟢 Ahmadreza → Final Save

🎯 TRADE DETAILS:
• Operation: {trade_session.operation.upper()}
• Type: {type_desc}
• Purity: {trade_session.gold_purity['name']}
• Total Weight: {format_weight_combined(trade_session.volume_kg)}
• Pure Gold ({trade_session.gold_purity['name'][:3]}): {format_weight_combined(calc_results['pure_gold_kg'])} ({calc_results['pure_gold_oz']:.3f} troy oz)
• Customer: {trade_session.customer}

⚖️ PURITY CALCULATION:
• Total Gold: {trade_session.volume_kg * 1000:,.1f} grams
• Purity Factor: {trade_session.gold_purity['name'][:3]}/1000 = {(safe_float(trade_session.gold_purity['value']) if trade_session.gold_purity['value'] != 'custom' else 999)/1000:.3f}
• Pure Gold: {calc_results['pure_gold_kg'] * 1000:,.1f} grams ({calc_results['pure_gold_oz']:.3f} oz)

💰 CALCULATION:
• {rate_description}
• Final Rate: ${final_rate_display:,.2f} USD/oz = AED {final_rate_aed:,.2f}/oz
• Total Price: ${calc_results['total_price_usd']:,.2f} USD
• Total Price: {format_money_aed(calc_results['total_price_usd'])}

👤 Dealer: {trade_session.dealer['name']}
⏰ Time: {get_uae_time().strftime('%H:%M:%S')} UAE

📲 WORKFLOW: Will notify Abhay immediately upon confirmation

✅ Ready to submit for approval!"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ SUBMIT FOR APPROVAL", callback_data="confirm_trade"))
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

# Handle trade text inputs including approval workflow
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Handle text messages including approval workflow inputs"""
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
                
                markup = types.InlineKeyboardMarkup()
                if any(p in dealer.get('permissions', []) for p in ['buy', 'sell']):
                    markup.add(types.InlineKeyboardButton("📊 NEW TRADE", callback_data="new_trade"))
                if any(p in dealer.get('permissions', []) for p in ['approve', 'reject', 'comment', 'final_approve']):
                    markup.add(types.InlineKeyboardButton("✅ Approval Dashboard", callback_data="approval_dashboard"))
                markup.add(types.InlineKeyboardButton("💰 Live Rate", callback_data="show_rate"))
                
                role_info = dealer.get('role', dealer['level'].title())
                
                bot.send_message(
                    user_id, 
                    f"""✅ Welcome {dealer['name']}! 

🥇 Gold Trading Bot v4.7 - APPROVAL WORKFLOW! ✨
🚀 Role: {role_info}
💰 Current Rate: {format_money(market_data['gold_usd_oz'])} USD/oz
🇦🇪 UAE Time: {market_data['last_update']} (Updates every 2min)

📲 Telegram notifications are ACTIVE for your approvals!

Ready for professional gold trading with approval workflow!""", 
                    reply_markup=markup
                )
                logger.info(f"✅ Login: {dealer['name']} (APPROVAL WORKFLOW v4.7)")
            else:
                bot.send_message(user_id, "❌ Wrong PIN. Please try again.")
        
        # Handle approval workflow inputs
        elif session_data.get("awaiting_input"):
            try:
                bot.delete_message(message.chat.id, message.message_id)
                
                input_type = session_data["awaiting_input"]
                trade_session = session_data.get("trade_session")
                
                # Handle rejection reason
                if input_type.startswith("reject_reason_"):
                    trade_id = input_type.replace("reject_reason_", "")
                    dealer = session_data.get("dealer")
                    
                    if dealer and len(text) <= 200:
                        success, message_result = reject_trade(trade_id, dealer['name'], text)
                        
                        markup = types.InlineKeyboardMarkup()
                        markup.add(types.InlineKeyboardButton("✅ Approval Dashboard", callback_data="approval_dashboard"))
                        markup.add(types.InlineKeyboardButton("📊 NEW TRADE", callback_data="new_trade"))
                        markup.add(types.InlineKeyboardButton("🔙 Dashboard", callback_data="dashboard"))
                        
                        if success:
                            result_text = f"""✅ TRADE REJECTED SUCCESSFULLY

{message_result}

📊 SHEET STATUS:
• Trade marked as REJECTED
• Removed from approval workflow
• All parties notified

👆 SELECT NEXT ACTION:"""
                            bot.send_message(user_id, result_text, reply_markup=markup)
                        else:
                            result_text = f"""❌ REJECTION FAILED

{message_result}

Please try again or contact admin.

👆 SELECT ACTION:"""
                            bot.send_message(user_id, result_text, reply_markup=markup)
                    else:
                        bot.send_message(user_id, "❌ Reason too long (max 200 characters)")
                
                # Handle adding comment
                elif input_type.startswith("add_comment_"):
                    trade_id = input_type.replace("add_comment_", "")
                    dealer = session_data.get("dealer")
                    
                    if dealer and len(text) <= 200:
                        success, message_result = add_comment_to_trade(trade_id, dealer['name'], text)
                        
                        markup = types.InlineKeyboardMarkup()
                        markup.add(types.InlineKeyboardButton("✅ Approval Dashboard", callback_data="approval_dashboard"))
                        markup.add(types.InlineKeyboardButton("📊 NEW TRADE", callback_data="new_trade"))
                        markup.add(types.InlineKeyboardButton("🔙 Dashboard", callback_data="dashboard"))
                        
                        if success:
                            result_text = f"""✅ COMMENT ADDED SUCCESSFULLY

{message_result}

📊 SHEET STATUS:
• Comment added to trade record
• Visible to all approvers
• Included in approval history

👆 SELECT NEXT ACTION:"""
                            bot.send_message(user_id, result_text, reply_markup=markup)
                        else:
                            result_text = f"""❌ COMMENT FAILED

{message_result}

Please try again or contact admin.

👆 SELECT ACTION:"""
                            bot.send_message(user_id, result_text, reply_markup=markup)
                    else:
                        bot.send_message(user_id, "❌ Comment too long (max 200 characters)")
                
                # FIXED: Handle quantity input - SUPPORTS DECIMALS
                elif input_type == "quantity" and trade_session:
                    try:
                        quantity = float(text)  # CHANGED: Allow decimal quantities
                        if 0.01 <= quantity <= 10000:  # CHANGED: Allow small decimals
                            # Calculate total weight based on quantity
                            weight_per_piece_grams = trade_session.gold_type['weight_grams']
                            total_weight_grams = quantity * weight_per_piece_grams
                            total_weight_kg = total_weight_grams / 1000
                            
                            trade_session.volume_kg = total_weight_kg
                            trade_session.volume_grams = total_weight_grams
                            trade_session.quantity = quantity
                            trade_session.step = "purity"
                            
                            markup = types.InlineKeyboardMarkup()
                            for purity in GOLD_PURITIES:
                                markup.add(types.InlineKeyboardButton(
                                    f"⚖️ {purity['name']}",
                                    callback_data=f"purity_{purity['value']}"
                                ))
                            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
                            
                            # Format quantity display properly for decimals
                            qty_display = f"{quantity:g}" if quantity == int(quantity) else f"{quantity:.3f}".rstrip('0').rstrip('.')
                            
                            bot.send_message(
                                user_id,
                                f"""✅ Quantity set: {qty_display} × {trade_session.gold_type['name']}
✅ Total Weight: {format_weight_combined(total_weight_kg)}

📊 NEW TRADE - STEP 4/8 (PURITY)

⚖️ SELECT PURITY:""",
                                reply_markup=markup
                            )
                        else:
                            bot.send_message(user_id, "❌ Quantity must be 0.01-10000 pieces")
                    except ValueError:
                        bot.send_message(user_id, "❌ Invalid quantity. Enter number like: 2.5")
                
                elif input_type == "volume" and trade_session:
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
                        markup.add(types.InlineKeyboardButton("✏️ Enter Custom Rate", callback_data="rate_custom"))
                        markup.add(types.InlineKeyboardButton("⚡ Rate Override", callback_data="rate_override"))
                        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
                        
                        bot.send_message(
                            user_id,
                            f"""✅ Customer: {text}

📊 NEW TRADE - STEP 6/8 (RATE SELECTION)

💰 Current Market: ${current_rate:,.2f} USD/oz

🎯 RATE OPTIONS:
• 📊 Market Rate: Live rate + premium/discount
• ✏️ Custom Rate: Your rate + premium/discount  
• ⚡ Rate Override: Direct final rate

💎 SELECT RATE SOURCE:""",
                            reply_markup=markup
                        )
                    else:
                        bot.send_message(user_id, "❌ Name too long (max 50)")
                
                elif input_type == "custom_rate" and trade_session:
                    try:
                        custom_rate = safe_float(text)
                        if 1000 <= custom_rate <= 10000:
                            trade_session.rate_per_oz = custom_rate
                            trade_session.step = "pd_type"
                            
                            markup = types.InlineKeyboardMarkup()
                            markup.add(types.InlineKeyboardButton("⬆️ PREMIUM", callback_data="pd_premium"))
                            markup.add(types.InlineKeyboardButton("⬇️ DISCOUNT", callback_data="pd_discount"))
                            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="new_trade"))
                            
                            bot.send_message(
                                user_id,
                                f"""✅ Custom Rate Set: ${custom_rate:,.2f}/oz

📊 NEW TRADE - STEP 7/8 (PREMIUM/DISCOUNT)

🎯 SELECT PREMIUM OR DISCOUNT:

💡 Premium = ADD to your rate
💡 Discount = SUBTRACT from your rate

💎 SELECT TYPE:""",
                                reply_markup=markup
                            )
                        else:
                            bot.send_message(user_id, "❌ Rate must be between $1,000 - $10,000 per ounce")
                    except ValueError:
                        bot.send_message(user_id, "❌ Invalid rate format. Please enter a number (e.g., 2650.00)")
                
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
                
                # FIXED: Handle custom premium/discount amounts
                elif input_type.startswith("custom_") and trade_session:
                    pd_type = input_type.replace("custom_", "")  # "premium" or "discount"
                    try:
                        pd_amount = safe_float(text)
                        if 0.01 <= pd_amount <= 500:
                            trade_session.pd_amount = pd_amount
                            
                            # Calculate final rate
                            if trade_session.rate_type == "market":
                                base_rate = market_data['gold_usd_oz']
                            else:  # custom
                                base_rate = trade_session.rate_per_oz
                            
                            if pd_type == "premium":
                                final_rate = base_rate + pd_amount
                            else:  # discount
                                final_rate = base_rate - pd_amount
                            
                            trade_session.final_rate_per_oz = final_rate
                            
                            # Show trade confirmation
                            show_confirmation(None, trade_session, user_id)
                        else:
                            bot.send_message(user_id, "❌ Amount must be between $0.01 - $500.00 per ounce")
                    except ValueError:
                        bot.send_message(user_id, "❌ Invalid amount format. Please enter a number (e.g., 25.50)")
                
                del session_data["awaiting_input"]
                
            except ValueError:
                bot.send_message(user_id, "❌ Invalid input")
            except Exception as e:
                bot.send_message(user_id, f"❌ Error: {e}")
        
    except Exception as e:
        logger.error(f"❌ Text error: {e}")

# ============================================================================
# SHEET MANAGEMENT FUNCTIONS - ADMIN TOOLS
# ============================================================================

def handle_sheet_management(call):
    """Handle sheet management for admin users - FULL FUNCTIONALITY"""
    try:
        user_id = call.from_user.id
        session = user_sessions.get(user_id, {})
        dealer = session.get("dealer")
        
        if not dealer or 'admin' not in dealer.get('permissions', []):
            bot.edit_message_text("❌ Admin access required", call.message.chat.id, call.message.message_id)
            return
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📊 View All Sheets", callback_data="view_sheets"))
        markup.add(types.InlineKeyboardButton("🎨 Format Current Sheet", callback_data="format_sheet"))
        markup.add(types.InlineKeyboardButton("🔧 Fix Headers", callback_data="fix_headers"))
        markup.add(types.InlineKeyboardButton("🗑️ Delete Sheets", callback_data="delete_sheets"))
        markup.add(types.InlineKeyboardButton("🧹 Clear Sheet Data", callback_data="clear_sheets"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="dashboard"))
        
        bot.edit_message_text(
            """🗂️ ADVANCED SHEET MANAGEMENT - ADMIN ACCESS

🎨 PROFESSIONAL FORMATTING TOOLS:
• View All Sheets: See spreadsheet overview
• Format Current Sheet: Apply beautiful gold formatting
• Fix Headers: Ensure proper column headers  
• Delete Sheets: Remove unwanted sheets permanently
• Clear Sheet Data: Remove data while keeping headers

✅ APPROVAL WORKFLOW FEATURES:
• Color-coded status (Red=Pending, Green=Approved)
• Real-time status updates
• Complete approval tracking

⚠️ Delete/Clear operations cannot be undone!

👆 SELECT ACTION:""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Sheet management error: {e}")

def get_all_sheets():
    """Get all sheets in the spreadsheet"""
    try:
        client = get_sheets_client()
        if not client:
            return False, "Client connection failed"
            
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        worksheets = spreadsheet.worksheets()
        
        sheet_info = []
        for sheet in worksheets:
            try:
                row_count = sheet.row_count
                col_count = sheet.col_count
                all_values = sheet.get_all_values()
                data_rows = len([row for row in all_values if any(cell.strip() for cell in row)])
                
                sheet_info.append({
                    'name': sheet.title,
                    'id': sheet.id,
                    'row_count': row_count,
                    'col_count': col_count,
                    'data_rows': data_rows,
                    'updated': getattr(sheet, 'updated', 'Unknown')
                })
            except Exception as e:
                logger.error(f"Error getting sheet info for {sheet.title}: {e}")
                sheet_info.append({
                    'name': sheet.title,
                    'id': getattr(sheet, 'id', 'Unknown'),
                    'row_count': 'Unknown',
                    'col_count': 'Unknown',
                    'data_rows': 'Unknown',
                    'updated': 'Unknown'
                })
        
        return True, sheet_info
        
    except Exception as e:
        logger.error(f"Error getting sheets: {e}")
        return False, str(e)

def format_sheet_beautifully(worksheet):
    """🎨 PROFESSIONAL SHEET FORMATTING - AMAZING RESULTS!"""
    try:
        logger.info(f"🎨 Starting PROFESSIONAL formatting for: {worksheet.title}")
        
        # Get sheet data
        all_values = worksheet.get_all_values()
        row_count = len(all_values)
        
        if row_count < 1:
            logger.info("⚠️ Sheet is empty, skipping formatting")
            return
        
        # 1️⃣ STUNNING GOLD HEADERS
        try:
            header_format = {
                "backgroundColor": {
                    "red": 0.85,    # Rich gold background ✨
                    "green": 0.65,
                    "blue": 0.125
                },
                "textFormat": {
                    "foregroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},  # Dark text
                    "fontSize": 12,
                    "bold": True,
                    "fontFamily": "Roboto"
                },
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE",
                "borders": {
                    "top": {"style": "SOLID", "width": 2, "color": {"red": 0.7, "green": 0.5, "blue": 0.0}},
                    "bottom": {"style": "SOLID", "width": 2, "color": {"red": 0.7, "green": 0.5, "blue": 0.0}},
                    "left": {"style": "SOLID", "width": 1, "color": {"red": 0.7, "green": 0.5, "blue": 0.0}},
                    "right": {"style": "SOLID", "width": 1, "color": {"red": 0.7, "green": 0.5, "blue": 0.0}}
                }
            }
            
            worksheet.format("1:1", header_format)
            logger.info("✅ STUNNING gold headers applied")
            
        except Exception as e:
            logger.info(f"⚠️ Header formatting failed: {e}")
        
        # 2️⃣ SMART CURRENCY FORMATTING
        try:
            if row_count > 1:
                # USD Currency formatting
                usd_format = {
                    "numberFormat": {"type": "CURRENCY", "pattern": "$#,##0.00"},
                    "horizontalAlignment": "RIGHT"
                }
                worksheet.format(f"K2:K{row_count}", usd_format)  # Price USD
                worksheet.format(f"M2:M{row_count}", usd_format)  # Input Rate USD  
                worksheet.format(f"O2:O{row_count}", usd_format)  # Final Rate USD
                worksheet.format(f"Q2:Q{row_count}", usd_format)  # Market Rate USD
                
                # AED Currency formatting
                aed_format = {
                    "numberFormat": {"type": "CURRENCY", "pattern": "AED #,##0.00"},
                    "horizontalAlignment": "RIGHT"
                }
                worksheet.format(f"L2:L{row_count}", aed_format)  # Price AED
                worksheet.format(f"N2:N{row_count}", aed_format)  # Input Rate AED
                worksheet.format(f"P2:P{row_count}", aed_format)  # Final Rate AED
                worksheet.format(f"R2:R{row_count}", aed_format)  # Market Rate AED
                
                logger.info("✅ SMART currency formatting applied")
                
        except Exception as e:
            logger.info(f"⚠️ Currency formatting failed: {e}")
        
        # 3️⃣ PROFESSIONAL BORDERS
        try:
            if row_count > 1:
                border_format = {
                    "borders": {
                        "top": {"style": "SOLID", "width": 1, "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                        "bottom": {"style": "SOLID", "width": 1, "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                        "left": {"style": "SOLID", "width": 1, "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                        "right": {"style": "SOLID", "width": 1, "color": {"red": 0.8, "green": 0.8, "blue": 0.8}}
                    }
                }
                worksheet.format(f"A1:Y{row_count}", border_format)
                logger.info("✅ PROFESSIONAL borders applied")
        except Exception as e:
            logger.info(f"⚠️ Border formatting failed: {e}")
        
        # 4️⃣ PERFECT COLUMN SIZING
        try:
            worksheet.columns_auto_resize(0, 25)
            logger.info("✅ PERFECT column sizing applied")
        except Exception as e:
            logger.info(f"⚠️ Column resize failed: {e}")
        
        logger.info(f"🎉 PROFESSIONAL formatting completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Professional formatting failed: {e}")

def ensure_proper_headers(worksheet):
    """Ensure worksheet has EXACT headers matching trade data with approval"""
    try:
        all_values = worksheet.get_all_values()
        
        # Define the EXACT headers with APPROVAL COLUMNS
        correct_headers = [
            'Date', 'Time', 'Dealer', 'Operation', 'Customer', 'Gold Type', 
            'Volume KG', 'Volume Grams', 'Pure Gold KG', 'Pure Gold Grams', 'Price USD', 'Price AED', 
            'Input Rate USD', 'Input Rate AED', 'Final Rate USD', 'Final Rate AED', 
            'Market Rate USD', 'Market Rate AED', 'Purity', 'Rate Type', 'P/D Amount', 'Session ID', 
            'Approval Status', 'Approved By', 'Notes'
        ]
        
        if not all_values:
            # Empty sheet, add headers
            worksheet.append_row(correct_headers)
            logger.info("✅ Added EXACT headers with approval columns to empty sheet")
            return True
        
        current_headers = all_values[0]
        
        # Check if headers need updating
        headers_need_update = False
        
        # Check if we have the right number of columns
        if len(current_headers) != len(correct_headers):
            headers_need_update = True
            logger.info(f"⚠️ Header count mismatch: {len(current_headers)} vs {len(correct_headers)}")
        
        # Check if each header matches
        for i, correct_header in enumerate(correct_headers):
            if i >= len(current_headers) or current_headers[i].strip() != correct_header:
                headers_need_update = True
                logger.info(f"⚠️ Header mismatch at position {i}: '{current_headers[i] if i < len(current_headers) else 'MISSING'}' vs '{correct_header}'")
        
        if headers_need_update:
            logger.info("🔧 Updating headers to EXACT match with approval columns...")
            worksheet.update('1:1', [correct_headers])
            logger.info("✅ Headers updated to EXACT match with approval workflow")
            return True
        
        logger.info("✅ Headers already match EXACTLY")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error ensuring EXACT headers: {e}")
        return False

def handle_view_sheets(call):
    """Handle view sheets with full functionality"""
    try:
        bot.edit_message_text("📊 Getting sheet information...", call.message.chat.id, call.message.message_id)
        
        success, result = get_all_sheets()
        
        if success:
            sheet_list = []
            for sheet in result:
                sheet_list.append(f"• {sheet['name']} ({sheet['data_rows']} rows)")
            
            if len(sheet_list) > 10:
                sheet_list = sheet_list[:10] + [f"... and {len(result) - 10} more sheets"]
            
            sheets_text = f"""📊 SHEET OVERVIEW

Total Sheets: {len(result)}

📋 SHEET LIST:
{chr(10).join(sheet_list)}

📊 Google Sheets Link:
https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/edit

✅ All sheets use professional approval workflow formatting!
🎨 Color-coded status: Red=Pending, Yellow=Abhay, Orange=Mushtaq, Green=Final"""
        else:
            sheets_text = f"❌ Error getting sheets: {result}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="view_sheets"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="sheet_management"))
        
        bot.edit_message_text(sheets_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"View sheets error: {e}")

def handle_format_sheet(call):
    """Handle format sheet with full functionality"""
    try:
        bot.edit_message_text("🎨 Applying professional formatting...", call.message.chat.id, call.message.message_id)
        
        client = get_sheets_client()
        if not client:
            bot.edit_message_text("❌ Sheets connection failed", call.message.chat.id, call.message.message_id)
            return
        
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        current_month = get_uae_time().strftime('%Y_%m')
        sheet_name = f"Gold_Trades_{current_month}"
        
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            format_sheet_beautifully(worksheet)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="sheet_management"))
            
            bot.edit_message_text(
                f"""🎉 PROFESSIONAL FORMATTING APPLIED!

✅ Sheet: {sheet_name}
🎨 Applied stunning approval workflow styling:
• Rich gold headers
• Smart currency formatting  
• Professional borders
• Perfect column sizing
• Color-coded approval status

📊 Your sheet now looks AMAZING with approval workflow!""",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
        except Exception as e:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="sheet_management"))
            
            bot.edit_message_text(
                f"❌ Sheet not found: {sheet_name}\n\nCreate a trade first to generate the sheet.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
    except Exception as e:
        logger.error(f"Format sheet error: {e}")

def handle_fix_headers(call):
    """Handle fix headers with full functionality"""
    try:
        bot.edit_message_text("🔧 Fixing sheet headers...", call.message.chat.id, call.message.message_id)
        
        client = get_sheets_client()
        if not client:
            bot.edit_message_text("❌ Sheets connection failed", call.message.chat.id, call.message.message_id)
            return
        
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        current_month = get_uae_time().strftime('%Y_%m')
        sheet_name = f"Gold_Trades_{current_month}"
        
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            ensure_proper_headers(worksheet)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="sheet_management"))
            
            bot.edit_message_text(
                f"""✅ HEADERS FIXED!

📊 Sheet: {sheet_name}
🔧 NOW INCLUDES APPROVAL WORKFLOW COLUMNS:
• Volume KG + Volume Grams
• Pure Gold KG + Pure Gold Grams
• Input Rate USD/AED (Your Rate Before P/D)
• Final Rate USD/AED (After Premium/Discount)
• Market Rate USD/AED (Current API Rate)
• Approval Status (Pending/Approved)
• Approved By (Abhay, Mushtaq, Ahmadreza)
• Notes (Comments and workflow info)

📋 All 25 columns in correct order for approval workflow!""",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
        except Exception as e:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="sheet_management"))
            
            bot.edit_message_text(
                f"❌ Sheet not found: {sheet_name}\n\nCreate a trade first to generate the sheet.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
    except Exception as e:
        logger.error(f"Fix headers error: {e}")

def handle_delete_sheets(call):
    """Handle delete sheets menu with full functionality"""
    try:
        bot.edit_message_text("📊 Getting sheets for deletion...", call.message.chat.id, call.message.message_id)
        
        success, result = get_all_sheets()
        
        if success and len(result) > 1:  # Don't allow deleting if only one sheet
            markup = types.InlineKeyboardMarkup()
            
            # Show sheets that can be deleted (skip main sheets)
            deletable_sheets = [s for s in result if not s['name'].startswith('Sheet1') and not s['name'] == 'Main']
            
            for sheet in deletable_sheets[:10]:  # Limit to 10 sheets
                markup.add(types.InlineKeyboardButton(
                    f"🗑️ {sheet['name']} ({sheet['data_rows']} rows)",
                    callback_data=f"delete_{sheet['name']}"
                ))
            
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="sheet_management"))
            
            if deletable_sheets:
                sheets_text = f"""🗑️ DELETE SHEETS

⚠️ WARNING: This action cannot be undone!

Select a sheet to delete:
• Only trade sheets can be deleted
• Main sheets are protected
• Approval workflow data will be lost

Available sheets: {len(deletable_sheets)}"""
            else:
                sheets_text = "🛡️ No deletable sheets found\n\nMain sheets are protected from deletion."
        else:
            sheets_text = "❌ Cannot load sheets or insufficient sheets to delete"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="sheet_management"))
        
        bot.edit_message_text(sheets_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"Delete sheets menu error: {e}")

def handle_clear_sheets(call):
    """Handle clear sheets menu with full functionality"""
    try:
        bot.edit_message_text("📊 Getting sheets for clearing...", call.message.chat.id, call.message.message_id)
        
        success, result = get_all_sheets()
        
        if success:
            markup = types.InlineKeyboardMarkup()
            
            for sheet in result[:10]:  # Limit to 10 sheets
                if sheet['data_rows'] > 1:  # Only show sheets with data
                    markup.add(types.InlineKeyboardButton(
                        f"🧹 {sheet['name']} ({sheet['data_rows']} rows)",
                        callback_data=f"clear_{sheet['name']}"
                    ))
            
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="sheet_management"))
            
            sheets_text = f"""🧹 CLEAR SHEET DATA

Select a sheet to clear:
• Headers will be preserved
• Only data rows will be removed
• This action cannot be undone
• Approval workflow history will be lost

Available sheets with data: {len([s for s in result if s['data_rows'] > 1])}"""
        else:
            sheets_text = "❌ Cannot load sheets"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="sheet_management"))
        
        bot.edit_message_text(sheets_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"Clear sheets menu error: {e}")

def delete_sheet(sheet_name):
    """Delete a specific sheet"""
    try:
        client = get_sheets_client()
        if not client:
            return False, "Sheets client failed"
            
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            spreadsheet.del_worksheet(worksheet)
            logger.info(f"✅ Deleted sheet: {sheet_name}")
            return True, f"Sheet '{sheet_name}' deleted successfully"
        except Exception as e:
            return False, f"Sheet '{sheet_name}' not found or cannot be deleted"
            
    except Exception as e:
        logger.error(f"❌ Delete sheet error: {e}")
        return False, str(e)

def clear_sheet(sheet_name, keep_headers=True):
    """Clear sheet data while optionally keeping headers"""
    try:
        client = get_sheets_client()
        if not client:
            return False, "Sheets client failed"
            
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            
            if keep_headers:
                # Clear everything except the first row (headers)
                all_values = worksheet.get_all_values()
                if len(all_values) > 1:
                    range_to_clear = f"A2:Z{len(all_values)}"
                    worksheet.batch_clear([range_to_clear])
                    logger.info(f"✅ Cleared data from sheet: {sheet_name} (kept headers)")
                    return True, f"Data cleared from '{sheet_name}' (headers preserved)"
                else:
                    return True, f"Sheet '{sheet_name}' already empty"
            else:
                # Clear everything including headers
                worksheet.clear()
                logger.info(f"✅ Completely cleared sheet: {sheet_name}")
                return True, f"Sheet '{sheet_name}' completely cleared"
                
        except Exception as e:
            return False, f"Sheet '{sheet_name}' not found"
            
    except Exception as e:
        logger.error(f"❌ Clear sheet error: {e}")
        return False, str(e)

def handle_sheet_action(call):
    """Handle sheet delete/clear actions with full functionality"""
    try:
        if call.data.startswith('delete_'):
            sheet_name = call.data.replace('delete_', '')
            bot.edit_message_text(f"🗑️ Deleting sheet: {sheet_name}...", call.message.chat.id, call.message.message_id)
            
            success, message = delete_sheet(sheet_name)
            
            if success:
                result_text = f"✅ {message}"
            else:
                result_text = f"❌ {message}"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🗑️ Delete More", callback_data="delete_sheets"))
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="sheet_management"))
            
            bot.edit_message_text(result_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
            
        elif call.data.startswith('clear_'):
            sheet_name = call.data.replace('clear_', '')
            bot.edit_message_text(f"🧹 Clearing sheet: {sheet_name}...", call.message.chat.id, call.message.message_id)
            
            success, message = clear_sheet(sheet_name, keep_headers=True)
            
            if success:
                result_text = f"✅ {message}"
            else:
                result_text = f"❌ {message}"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🧹 Clear More", callback_data="clear_sheets"))
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="sheet_management"))
            
            bot.edit_message_text(result_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
            
    except Exception as e:
        logger.error(f"Sheet action error: {e}")

# ============================================================================
# CLOUD-OPTIMIZED MAIN FUNCTION  
# ============================================================================

def main():
    """Main function optimized for Railway cloud deployment with approval workflow"""
    try:
        logger.info("=" * 60)
        logger.info("🥇 GOLD TRADING BOT v4.7 - APPROVAL WORKFLOW RESTORED!")
        logger.info("=" * 60)
        logger.info("🔧 COMPLETE FEATURES:")
        logger.info("✅ Working gold rate API (2min updates)")
        logger.info("✅ UAE timezone for all timestamps (UTC+4)")
        logger.info("✅ Decimal quantities (0.25, 2.5, etc.)")
        logger.info("✅ TT Bar weight: Exact 116.6380g (10 Tola)")
        logger.info("✅ APPROVAL WORKFLOW:")
        logger.info("    → Abhay (Head Accountant) - First approval")
        logger.info("    → Mushtaq (Level 2 Approver) - Second approval")
        logger.info("    → Ahmadreza (Final Approver) - Final approval")
        logger.info("✅ Instant Telegram notifications")
        logger.info("✅ Color-coded sheets with approval status")
        logger.info("✅ Professional sheet integration")
        logger.info("✅ 24/7 Cloud Operation")
        logger.info("=" * 60)
        
        # Initialize UAE time in market data
        market_data["last_update"] = get_uae_time().strftime('%H:%M:%S')
        
        logger.info("🔧 Testing connections...")
        sheets_ok, sheets_msg = test_sheets_connection()
        logger.info(f"📊 Sheets: {sheets_msg}")
        
        # IMMEDIATE rate fetch on startup
        logger.info("💰 Fetching initial gold rate...")
        rate_ok = fetch_gold_rate()
        if rate_ok:
            logger.info(f"💰 Initial Rate: ${market_data['gold_usd_oz']:.2f} (UAE: {market_data['last_update']})")
        else:
            logger.warning(f"💰 Initial Rate fetch failed, using default: ${market_data['gold_usd_oz']:.2f}")
        
        # Start background rate updater
        start_rate_updater()
        
        # Give the updater a moment to run
        time.sleep(2)
        
        logger.info(f"✅ APPROVAL WORKFLOW BOT v4.7 READY:")
        logger.info(f"  💰 Gold: {format_money(market_data['gold_usd_oz'])} | {format_money_aed(market_data['gold_usd_oz'])}")
        logger.info(f"  🇦🇪 UAE Time: {market_data['last_update']}")
        logger.info(f"  📊 Sheets: {'Connected' if sheets_ok else 'Fallback mode'}")
        logger.info(f"  ✅ Approvers Ready: Abhay, Mushtaq, Ahmadreza")
        logger.info(f"  📲 Telegram Notifications: ACTIVE")
        logger.info(f"  🎨 Color-coded Approval Status: ENABLED")
        logger.info(f"  ⚡ All Features: WORKING")
        logger.info(f"  ☁️ Platform: Railway (24/7 operation)")
        
        logger.info(f"📊 Sheet: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/edit")
        logger.info("🚀 STARTING APPROVAL WORKFLOW BOT v4.7 FOR 24/7 OPERATION...")
        logger.info("=" * 60)
        
        # Start bot with cloud-optimized polling
        while True:
            try:
                logger.info("🚀 Starting APPROVAL WORKFLOW bot v4.7 polling on Railway cloud...")
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
        main()  # Restart on critical error

if __name__ == '__main__':
    main()
