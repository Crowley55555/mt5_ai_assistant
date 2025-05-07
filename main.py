import tkinter as tk
from ui.main_window import TradingAssistantApp
from core import init_core_components
from config import Settings
from utils.logger import TradingLogger
import pandas as pd
from pathlib import Path
import shutil
from datetime import datetime

# Инициализация корневого логгера
logger = TradingLogger(log_file="logs/trading_assistant.log")


def create_db_backup(db_path: str):
    """Создание резервной копии базы данных"""
    try:
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"db_backup_{timestamp}.db"

        if db_path.startswith('sqlite:///'):
            actual_db_path = db_path.replace('sqlite:///', '')
            shutil.copy2(actual_db_path, backup_path)
            logger.info(f"Создана резервная копия БД: {backup_path}")
        else:
            logger.warning("Резервное копирование поддерживается только для SQLite")
    except Exception as e:
        logger.error(f"Ошибка создания резервной копии БД: {str(e)}")


def test_db_connection(db):
    """Проверка работоспособности БД"""
    try:
        # Проверяем доступность БД
        if not hasattr(db, 'get_market_data') or not hasattr(db, 'save_market_data'):
            raise RuntimeError("Неверный объект БД — отсутствуют методы работы с данными")

        # Тестовая запись и чтение
        test_data = {
            "open": [1.1],
            "high": [1.2],
            "low": [1.0],
            "close": [1.15],
            "volume": [1000]
        }

        df = pd.DataFrame(test_data, index=[pd.Timestamp.now()])
        df.index.name = 'time'

        db.save_market_data('TEST', 1, df)
        retrieved = db.get_market_data('TEST', 1)

        if retrieved.empty:
            raise RuntimeError("База данных не возвращает сохраненные данные")

        logger.info("База данных успешно протестирована")
        return True
    except Exception as e:
        logger.warning(f"Предупреждение: ошибка тестирования БД — {str(e)}")
        return False  # Не останавливаем запуск приложения из-за этого


def main():
    # Сначала загружаем настройки
    settings = Settings()

    # Инициализируем ядро системы
    try:
        core = init_core_components(settings, logger)
        logger.info("Ядро системы инициализировано")
    except Exception as e:
        logger.critical(f"Не удалось инициализировать ядро: {str(e)}", exc_info=True)
        raise

    # Создаем резервную копию БД после успешной инициализации
    if core.database:
        is_db_working = test_db_connection(core.database)
        if is_db_working:
            create_db_backup(core.database.connection_string)

    # Запускаем графический интерфейс
    root = tk.Tk()
    app = TradingAssistantApp(root, core, settings, logger)
    root.mainloop()


if __name__ == "__main__":
    main()