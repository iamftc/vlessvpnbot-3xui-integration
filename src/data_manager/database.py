import sqlite3
from datetime import datetime
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("/app/project")
DB_FILE = PROJECT_ROOT / "users.db"

def initialize_db():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                role TEXT DEFAULT 'user',
                total_spent REAL DEFAULT 0,
                total_months INTEGER DEFAULT 0,
                trial_used BOOLEAN DEFAULT 0,
                agreed_to_terms BOOLEAN DEFAULT 0,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_banned BOOLEAN DEFAULT 0,
                referred_by INTEGER,
                referral_balance REAL DEFAULT 0,
                referral_balance_all REAL DEFAULT 0,
                dealer_id INTEGER,
                created_by INTEGER
            )
            ''')
            
            # Таблица VPN ключей
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS vpn_keys (
                key_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                host_name TEXT NOT NULL,
                xui_client_uuid TEXT NOT NULL,
                key_email TEXT NOT NULL UNIQUE,
                expiry_date TIMESTAMP,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Таблица транзакций
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                username TEXT,
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                amount_rub REAL NOT NULL,
                amount_currency REAL,
                currency_name TEXT,
                payment_method TEXT,
                metadata TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Таблица настроек бота
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            ''')
            
            # Таблица дилер-клиентов
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS dealer_clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dealer_id INTEGER NOT NULL,
                client_id INTEGER NOT NULL,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dealer_id) REFERENCES users(telegram_id),
                FOREIGN KEY(client_id) REFERENCES users(telegram_id)
            )
            ''')
            
            # Таблица хостов XUI
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS xui_hosts(
                host_name TEXT NOT NULL,
                host_url TEXT NOT NULL,
                host_username TEXT NOT NULL,
                host_pass TEXT NOT NULL,
                host_inbound_id INTEGER NOT NULL
            )
            ''')
            
            # Таблица тарифов
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plans (
                plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                host_name TEXT NOT NULL,
                plan_name TEXT NOT NULL,
                months INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (host_name) REFERENCES xui_hosts (host_name)
            )
            ''')
            
            # Таблица тикетов поддержки
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_threads (
                user_id INTEGER PRIMARY KEY,
                thread_id INTEGER NOT NULL
            )
            ''')
            
            # Настройки по умолчанию
            default_settings = {
                "panel_login": "admin",
                "panel_password": "admin",
                "panel_port": "8999",
                "about_text": None,
                "terms_url": None,
                "privacy_url": None,
                "support_user": None,
                "support_text": None,
                "channel_url": None,
                "force_subscription": "true",
                "receipt_email": "example@example.com",
                "telegram_bot_token": None,
                "support_bot_token": None,
                "telegram_bot_username": None,
                "trial_enabled": "true",
                "trial_duration_days": "3",
                "enable_referrals": "true",
                "referral_percentage": "10",
                "referral_discount": "5",
                "minimum_withdrawal": "100",
                "support_group_id": None,
                "admin_telegram_id": None,
                "yookassa_shop_id": None,
                "yookassa_secret_key": None,
                "sbp_enabled": "false",
                "cryptobot_token": None,
                "heleket_merchant_id": None,
                "heleket_api_key": None,
                "domain": None,
                "ton_wallet_address": None,
                "tonapi_key": None,
                "stars_enabled": "false",
                "stars_price_rub": "1.0",
                "android_url": "https://telegra.ph/Instrukciya-Android-11-09",
                "ios_url": "https://telegra.ph/Instrukciya-iOS-11-09",
                "windows_url": "https://telegra.ph/Instrukciya-Windows-11-09",
                "linux_url": "https://telegra.ph/Instrukciya-Linux-11-09"
            }
            
            for key, value in default_settings.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)",
                    (key, str(value) if value is not None else None)
                )
            
            conn.commit()
            logger.info("Database initialized successfully.")
            
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С БД ====================

def get_setting(key: str) -> str | None:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None
    except sqlite3.Error as e:
        logger.error(f"Failed to get setting '{key}': {e}")
        return None

def set_setting(key: str, value: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)",
                (key, str(value))
            )
            conn.commit()
            logger.info(f"Setting '{key}' updated.")
    except sqlite3.Error as e:
        logger.error(f"Failed to set setting '{key}': {e}")

def get_user(telegram_id: int) -> dict | None:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
    except sqlite3.Error as e:
        logger.error(f"Failed to get user: {e}")
        return None

def register_user(telegram_id: int, username: str, referred_by: int = None):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO users (telegram_id, username, referred_by) VALUES (?, ?, ?)",
                (telegram_id, username, referred_by)
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to register user: {e}")

def get_user_role(telegram_id: int) -> str:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE telegram_id = ?", (telegram_id,))
            result = cursor.fetchone()
            return result[0] if result else "user"
    except sqlite3.Error as e:
        logger.error(f"Failed to get user role: {e}")
        return "user"

def set_user_role(telegram_id: int, role: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role = ? WHERE telegram_id = ?", (role, telegram_id))
            conn.commit()
            logger.info(f"User {telegram_id} role set to {role}")
    except sqlite3.Error as e:
        logger.error(f"Failed to set user role: {e}")

def get_dealer_clients(dealer_id: int) -> list:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.* FROM users u
                INNER JOIN dealer_clients dc ON u.telegram_id = dc.client_id
                WHERE dc.dealer_id = ?
            """, (dealer_id,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Failed to get dealer clients: {e}")
        return []

def add_dealer_client(dealer_id: int, client_id: int):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO dealer_clients (dealer_id, client_id) VALUES (?, ?)",
                (dealer_id, client_id)
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to add dealer client: {e}")

def get_all_clients_with_dealer() -> list:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.*, dc.dealer_id FROM users u
                LEFT JOIN dealer_clients dc ON u.telegram_id = dc.client_id
                WHERE u.role = 'user'
            """)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Failed to get clients with dealer: {e}")
        return []

def get_user_keys(user_id: int) -> list:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vpn_keys WHERE user_id = ?", (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Failed to get user keys: {e}")
        return []

def log_transaction(user_id: int, amount_rub: float, payment_method: str, status: str, metadata: str = None):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            payment_id = f"pay_{user_id}_{int(datetime.now().timestamp())}"
            cursor.execute("""
                INSERT INTO transactions (payment_id, user_id, status, amount_rub, payment_method, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (payment_id, user_id, status, amount_rub, payment_method, metadata))
            conn.commit()
            return payment_id
    except sqlite3.Error as e:
        logger.error(f"Failed to log transaction: {e}")
        return None

def get_plan_by_id(plan_id: int) -> dict | None:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM plans WHERE plan_id = ?", (plan_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
    except sqlite3.Error as e:
        logger.error(f"Failed to get plan: {e}")
        return None

def get_all_hosts() -> list:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM xui_hosts")
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Failed to get hosts: {e}")
        return []

def get_plans_for_host(host_name: str) -> list:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM plans WHERE host_name = ?", (host_name,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Failed to get plans: {e}")
        return []