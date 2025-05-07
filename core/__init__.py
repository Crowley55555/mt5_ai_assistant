"""
Ядро торгового ассистента (core module)

Основные компоненты системы:
- MT5Client - взаимодействие с MetaTrader 5
- RiskManager - управление рисками
- TelegramBot - уведомления в Telegram
- OllamaIntegration - анализ с помощью LLM
"""

from core.mt5_client import MT5Client
from core.risk_manager import RiskManager
from core.telegram_bot import TelegramBot
from core.ollama_integration import OllamaIntegration
from .database import MarketDatabase
from config.settings import Settings
import logging
from utils.logger import TradingLogger


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
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class CoreComponents:
    """Контейнер для основных компонентов системы"""
    def __init__(self):
        self.database = None     # База данных
        self.mt5 = None          # Клиент MT5
        self.risk_manager = None # Менеджер рисков
        self.telegram = None     # Telegram бот
        self.ollama = None       # Интеграция с Ollama
        self.strategies = {}     # Торговые стратегии


def init_core_components(settings: Settings, logger: logging.Logger) -> CoreComponents:
    """
    Инициализация всех компонентов ядра

    :param settings: Объект настроек
    :param logger: Логгер приложения
    :return: Объект CoreComponents
    """
    components = CoreComponents()

    try:
        # Инициализация базы данных
        db_config = settings._settings.get("database", {})
        if "connection_string" not in db_config:
            db_config["connection_string"] = "sqlite:///data.db"

        try:
            components.database = MarketDatabase(db_config["connection_string"], logger)
            logger.info("База данных успешно инициализирована")
        except Exception as e:
            logger.warning(f"Не удалось инициализировать базу данных: {str(e)}")

        # Инициализация клиента MT5
        mt5_settings = settings.current_account or {}
        if all(mt5_settings.values()):
            try:
                components.mt5 = MT5Client(logger)
                logger.debug("MT5 клиент создан")

                # Подключение только если есть данные
                if any(mt5_settings.values()):
                    connected = components.mt5.connect(
                        mt5_settings.get('login', ''),
                        mt5_settings.get('password', ''),
                        mt5_settings.get('server', ''),
                        mt5_settings.get('path', '')
                    )
                    if connected:
                        logger.info("Подключение к MT5 установлено")
                    else:
                        logger.warning("Не удалось подключиться к MT5")
            except Exception as e:
                logger.error(f"Ошибка инициализации MT5: {str(e)}")
        else:
            logger.debug("MT5 аккаунт не задан")

        # Инициализация менеджера рисков
        try:
            risk_settings = settings.risk_management
            if components.mt5:
                components.risk_manager = RiskManager(components.mt5, logger)
                if all(key in risk_settings for key in ['risk_per_trade', 'risk_all_trades', 'daily_risk']):
                    components.risk_manager.update_settings(**risk_settings)
                logger.info("Менеджер рисков инициализирован")
            else:
                logger.warning("Не удалось инициализировать менеджер рисков без MT5 клиента")
        except Exception as e:
            logger.error(f"Ошибка инициализации менеджера рисков: {str(e)}")

        # Инициализация Telegram бота
        telegram_settings = settings.telegram or {}
        if telegram_settings.get('token') and telegram_settings.get('chat_id'):
            try:
                components.telegram = TelegramBot(logger)
                components.telegram.initialize(
                    telegram_settings['token'],
                    telegram_settings['chat_id']
                )
                logger.info("Telegram бот инициализирован")
            except Exception as e:
                logger.warning(f"Ошибка инициализации Telegram: {str(e)}")
        else:
            logger.debug("Telegram не настроен")

        # Инициализация Ollama интеграции
        ollama_settings = settings.ollama or {}
        if ollama_settings.get('base_url') and ollama_settings.get('model'):
            try:
                components.ollama = OllamaIntegration(
                    ollama_settings['base_url'],
                    ollama_settings['model'],
                    logger
                )
                logger.info("Ollama интеграция инициализирована")
            except Exception as e:
                logger.warning(f"Ошибка инициализации Ollama: {str(e)}")
        else:
            logger.debug("Ollama не настроена")

        # Успешная инициализация ядра
        logger.info(f"Ядро системы инициализировано (v{__version__})")
        return components

    except Exception as e:
        logger.critical(f"Критическая ошибка инициализации ядра: {str(e)}")
        raise