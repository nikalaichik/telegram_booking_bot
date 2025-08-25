import logging
import asyncio
import sys
import os
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN
from bot.handlers import BotHandlers

def setup_logging():
    """Настройка логирования с поддержкой Unicode"""
    # Настраиваем кодировку для Windows
    if sys.platform == "win32":
        os.environ["PYTHONIOENCODING"] = "utf-8"

    # Создаем форматтер без эмодзи для файла
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Создаем форматтер с эмодзи для консоли (если поддерживается)
    try:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    except:
        console_formatter = file_formatter

    # Настройка логгера
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Файловый хандлер (без эмодзи)
    file_handler = logging.FileHandler('bot.log', encoding='utf-8')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Консольный хандлер
    try:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    except:
        pass  # Игнорируем ошибки консольного вывода

def main():
    """Основная функция запуска бота"""
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Создание приложения
        application = Application.builder().token(BOT_TOKEN).build()

        # Создание обработчиков
        handlers = BotHandlers()

        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", handlers.start))
        application.add_handler(CommandHandler("help", handlers.help_command))
        application.add_handler(CommandHandler("mybookings", handlers.my_bookings))
        application.add_handler(CallbackQueryHandler(handlers.button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_contact_info))

        # Запуск бота
        logger.info("Бот запущен и готов к работе")
        application.run_polling()

    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        raise

if __name__ == '__main__':
    main()