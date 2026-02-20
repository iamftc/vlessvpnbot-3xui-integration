import logging
import asyncio
import threading
from pathlib import Path

from shop_bot.data_manager.database import initialize_db
from shop_bot.webhook_server.app import create_webhook_app
from shop_bot.bot_controller import BotController

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def run_flask_app():
    """Запуск Flask приложения на порту 8999"""
    app = create_webhook_app()
    app.run(host='0.0.0.0', port=8999, debug=False, use_reloader=False)

def main():
    logger.info("Starting VPN Bot...")
    
    # Инициализация БД
    initialize_db()
    logger.info("Database initialized.")
    
    # Запуск веб-панели в отдельном потоке
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    logger.info("Web panel started on http://0.0.0.0:8999")
    
    # Запуск бота
    controller = BotController()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    controller.set_loop(loop)
    
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        loop.stop()

if __name__ == "__main__":
    main()