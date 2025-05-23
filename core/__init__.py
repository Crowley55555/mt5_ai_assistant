"""
Ядро торгового ассистента (core module)

Основные компоненты системы:
- MT5Client - взаимодействие с MetaTrader 5
- RiskManager - управление рисками
- TelegramBot - уведомления в Telegram
- OllamaIntegration - анализ с помощью LLM
"""

from .mt5_client import MT5Client
from .risk_manager import RiskManager
from .telegram_bot import TelegramBot
from .ollama_integration import OllamaIntegration
from database import MarketDatabase

__all__ = [
    'MT5Client',
    'RiskManager',
    'TelegramBot',
    'OllamaIntegration',
    'MarketDatabase'
]

# Версия ядра
__version__ = '1.0.0'

# Инициализация логгера
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

class CoreComponents:
    """Контейнер для основных компонентов системы"""

    def __init__(self):
        self.mt5 = None          # Клиент MT5
        self.risk_manager = None # Менеджер рисков
        self.telegram = None     # Telegram бот
        self.ollama = None       # Интеграция с Ollama

def init_core_components(settings, logger):
    """
    Инициализация всех компонентов ядра
    :param settings: Объект настроек (config.Settings)
    :param logger: Логгер приложения
    :return: Объект CoreComponents
    """
    components = CoreComponents()

    try:
        # Инициализация базы данных (добавляем первым)
        components.database = MarketDatabase(
            settings.database['connection_string'],
            logger
        )

        # Инициализация клиента MT5
        components.mt5 = MT5Client(logger)


        # Инициализация менеджера рисков
        components.risk_manager = RiskManager(components.mt5, logger)

        # Инициализация Telegram бота (если есть токен)
        if settings.telegram.get('token'):
            components.telegram = TelegramBot(
                settings.telegram['token'],
                settings.telegram['chat_id'],
                logger
            )

        # Инициализация Ollama (если указан URL)
        if settings.ollama.get('base_url'):
            components.ollama = OllamaIntegration(
                settings.ollama['base_url'],
                settings.ollama['model'],
                logger
            )

        logger.info(f"Ядро системы инициализировано (v{__version__})")
        return components

    except Exception as e:
        logger.critical(f"Ошибка инициализации ядра: {str(e)}", exc_info=True)
        raise RuntimeError(f"Не удалось инициализировать ядро системы: {str(e)}")