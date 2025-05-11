import logging
from pathlib import Path
from typing import Optional, Dict, ClassVar


class ColoredFormatter(logging.Formatter):
    """Кастомный цветной форматтер для консольного вывода"""
    COLORS: ClassVar[Dict[str, str]] = {
        'DEBUG': '\033[94m',  # Синий
        'INFO': '\033[92m',  # Зеленый
        'WARNING': '\033[93m',  # Желтый
        'ERROR': '\033[91m',  # Красный
        'CRITICAL': '\033[95m'  # Пурпурный
    }
    RESET_SEQ: ClassVar[str] = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись лога с цветом"""
        color = self.COLORS.get(record.levelname, '')
        message = super().format(record)
        return f"{color}{message}{self.RESET_SEQ}"


class TradingLogger:
    """
    Кастомный логгер для торгового приложения с поддержкой:
    - Цветного вывода в консоль
    - Записи в файл
    - Разных уровней логирования
    """

    _DEFAULT_FORMAT: ClassVar[str] = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    def __init__(self, name: str = "trading_bot", log_file: Optional[str] = None):
        """
        Инициализация логгера

        Args:
            name: Имя логгера (по умолчанию 'trading_bot')
            log_file: Путь к файлу для записи логов (опционально)
        """
        self.logger = self._configure_logger(name, log_file)
        self.logger.info("Логгер успешно инициализирован")

    def _configure_logger(self, name: str, log_file: Optional[str]) -> logging.Logger:
        """Настраивает и возвращает сконфигурированный логгер"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        self._remove_existing_handlers(logger)
        self._add_console_handler(logger)

        if log_file:
            self._add_file_handler(logger, log_file)

        return logger

    @staticmethod
    def _remove_existing_handlers(logger: logging.Logger) -> None:
        """Удаляет все существующие обработчики у логгера"""
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    def _add_console_handler(self, logger: logging.Logger) -> None:
        """Добавляет цветной консольный обработчик"""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(ColoredFormatter(self._DEFAULT_FORMAT))
        logger.addHandler(console_handler)

    def _add_file_handler(self, logger: logging.Logger, log_file: str) -> None:
        """Добавляет файловый обработчик с обработкой ошибок"""
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(self._DEFAULT_FORMAT))
            logger.addHandler(file_handler)
            logger.debug("Файловый логгер успешно инициализирован")
        except Exception as e:
            logger.warning(f"Ошибка инициализации файлового логгера: {str(e)}")

    def debug(self, message: str) -> None:
        """Логирование сообщения уровня DEBUG"""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """Логирование сообщения уровня INFO"""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Логирование сообщения уровня WARNING"""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Логирование сообщения уровня ERROR"""
        self.logger.error(message)

    def critical(self, message: str) -> None:
        """Логирование сообщения уровня CRITICAL"""
        self.logger.critical(message)