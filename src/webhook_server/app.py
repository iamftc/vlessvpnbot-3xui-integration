import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import sqlite3
from pathlib import Path
from shop_bot.data_manager.database import (
    DB_FILE, get_setting, set_setting, get_all_hosts, get_plans_for_host,
    get_user, get_all_clients_with_dealer, get_dealer_clients
)

logger = logging.getLogger(__name__)

flask_app = Flask(__name__)
flask_app.secret_key = "your-secret-key-change-in-production"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

@flask_app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        
        panel_login = get_setting("panel_login") or "admin"
        panel_password = get_setting("panel_password") or "admin"
        
        if login == panel_login and password == panel_password:
            session['logged_in'] = True
            flash('✅ Успешный вход!', 'success')
            return redirect(url_for('dashboard_page'))
        else:
            flash('❌ Неверный логин или пароль', 'error')
    
    return render_template('login.html')

@flask_app.route('/dashboard')
@login_required
def dashboard_page():
    stats = {
        "total_users": 0,
        "active_keys": 0,
        "total_revenue": 0
    }
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            stats["total_users"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM vpn_keys")
            stats["active_keys"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(amount_rub) FROM transactions WHERE status = 'completed'")
            result = cursor.fetchone()[0]
            stats["total_revenue"] = float(result) if result else 0
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
    
    return render_template('dashboard.html', stats=stats)

@flask_app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_page():
    if request.method == 'POST':
        # Сохранение настроек
        settings_to_save = [
            "panel_login", "panel_password", "stars_enabled", "stars_price_rub",
            "trial_enabled", "trial_duration_days", "enable_referrals",
            "referral_percentage", "referral_discount", "telegram_bot_token",
            "telegram_bot_username", "admin_telegram_id", "yookassa_shop_id",
            "yookassa_secret_key", "cryptobot_token", "ton_wallet_address",
            "tonapi_key", "about_text", "terms_url", "privacy_url",
            "support_user", "support_text", "channel_url", "force_subscription"
        ]
        
        for key in settings_to_save:
            value = request.form.get(key)
            if value is not None:
                set_setting(key, value)
        
        flash('✅ Настройки сохранены!', 'success')
        return redirect(url_for('settings_page'))
    
    # Загрузка текущих настроек
    settings = {}
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM bot_settings")
            settings = {row[0]: row[1] for row in cursor.fetchall()}
    except Exception as e:
        logger.error(f"Settings load error: {e}")
    
    return render_template('settings.html', settings=settings)

@flask_app.route('/users')
@login_required
def users_page():
    users = []
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY registration_date DESC")
            users = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Users load error: {e}")
    
    return render_template('users.html', users=users)

@flask_app.route('/hosts')
@login_required
def hosts_page():
    hosts = get_all_hosts()
    return render_template('hosts.html', hosts=hosts)

@flask_app.route('/add-host', methods=['POST'])
@login_required
def add_host():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO xui_hosts (host_name, host_url, host_username, host_pass, host_inbound_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                request.form['host_name'],
                request.form['host_url'],
                request.form['host_username'],
                request.form['host_pass'],
                int(request.form['host_inbound_id'])
            ))
            conn.commit()
        flash('✅ Хост добавлен!', 'success')
    except Exception as e:
        flash(f'❌ Ошибка: {e}', 'error')
    
    return redirect(url_for('hosts_page'))

@flask_app.route('/logout')
def logout():
    session.clear()
    flash('✅ Вы вышли из системы', 'success')
    return redirect(url_for('login_page'))

def create_webhook_app():
    return flask_app