#!/bin/bash

echo "🚀 Установка VPN Bot..."

# Создание директории
mkdir -p /opt/my-vpn-bot
cd /opt/my-vpn-bot

# Копирование файлов (замените на ваш репозиторий)
git clone https://github.com/your-username/my-vpn-bot.git .

# Запуск через docker-compose
docker-compose up -d

echo ""
echo "✅ Установка завершена!"
echo ""
echo "📊 Веб-панель: http://your-server-ip:8999"
echo "🔐 Логин по умолчанию: admin"
echo "🔑 Пароль по умолчанию: admin"
echo ""
echo "📝 Логи: docker-compose logs -f"
echo "🛑 Остановка: docker-compose down"