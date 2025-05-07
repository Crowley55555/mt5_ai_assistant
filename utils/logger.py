import logging
from pathlib import Path
from typing import Optional


class TradingLogger:
    def __init__(self, name: str = "trading_bot", log_file: Optional[str] = None):
        """
        Инициализация кастомного логгера

        :param name: Имя логгера
        :param log_file: Путь к файлу логов (опционально)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Удаляем старые обработчики
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Форматтер
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self._create_colored_formatter())
        self.logger.addHandler(console_handler)

        # Файловый обработчик
        if log_file:
            try:
                log_path = Path(log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)

                file_handler = logging.FileHandler(log_path, encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
                self.logger.debug("Файловый логгер успешно инициализирован")
            except Exception as e:
                self.logger.warning(f"Ошибка инициализации файлового логгера: {str(e)}")

        self.logger.info("Логгер инициализирован")

    def _create_colored_formatter(self):
        """Создание цветного форматтера для консоли"""

        class ColoredFormatter(logging.Formatter):
            COLORS = {
                'DEBUG': '\033[94m',  # Синий
                'INFO': '\033[92m',  # Зеленый
                'WARNING': '\033[93m',  # Желтый
                'ERROR': '\033[91m',  # Красный
                'CRITICAL': '\033[95m'  # Пурпурный
            }
            RESET_SEQ = "\033[0m"

            def format(self, record):
                color = self.COLORS.get(record.levelname, '')
                message = super().format(record)
                return f"{color}{message}{self.RESET_SEQ}"

        return ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def debug(self, message: str):
        """Запись DEBUG уровня"""
        self.logger.debug(message)

    def info(self, message: str):
        """Запись INFO уровня"""
        self.logger.info(message)

    def warning(self, message: str):
        """Запись WARNING уровня"""
        self.logger.warning(message)

    def error(self, message: str):
        """Запись ERROR уровня"""
        self.logger.error(message)

    def critical(self, message: str):
        """Запись CRITICAL уровня"""
        self.logger.critical(message)