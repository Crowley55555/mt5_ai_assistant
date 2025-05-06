
import tkinter as tk
from ui.main_window import TradingAssistantApp
from core import init_core_components
from config import Settings
from utils.logger import TradingLogger
import pandas as pd
from datetime import datetime
from pathlib import Path
import shutil

logger = TradingLogger(log_file="logs/trading_assistant.log")


def main():
    root = tk.Tk()
    app = TradingAssistantApp(root)
    root.mainloop()

    settings = Settings()

    try:
        # Инициализация всех компонентов ядра
        core = init_core_components(settings, logger)
        logger.info("Запуск торгового ассистента")
        # Проверка подключения к БД
        test_db_connection(core.database)
        if core.database:
            # Создаем резервную копию при старте
            try:
                backup_path = f"backups/db_{datetime.now().strftime('%Y%m%d')}.db"
                Path(backup_path).parent.mkdir(exist_ok=True)
                shutil.copy2(core.database.connection_string.replace('sqlite:///', ''), backup_path)
                logger.info(f"Создана резервная копия БД: {backup_path}")
            except Exception as e:
                logger.error(f"Ошибка резервного копирования: {str(e)}")

        # Дальнейшая логика приложения...

    except Exception as e:
        logger.critical(f"Ошибка запуска: {str(e)}", exc_info=True)
        raise


def test_db_connection(db):
    """Проверка работоспособности БД"""
    try:
        # Тестовая запись и чтение
        test_data = pd.DataFrame({
            'open': [1.1], 'high': [1.2], 'low': [1.0],
            'close': [1.15], 'volume': [1000]
        }, index=[pd.Timestamp.now()])

        db.save_market_data('TEST', 1, test_data)
        retrieved = db.get_market_data('TEST', 1)

        if retrieved.empty:
            raise RuntimeError("База данных не возвращает сохраненные данные")

        logger.info("База данных успешно протестирована")
    except Exception as e:
        logger.error(f"Ошибка тестирования БД: {str(e)}")
        raise

if __name__ == "__main__":
    main()