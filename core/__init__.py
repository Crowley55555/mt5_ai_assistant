"""
Модуль ядра торговой системы (core)

Содержит основные компоненты:
- MT5Client: Клиент для работы с MetaTrader 5
- RiskManager: Управление рисками
- TelegramBot: Уведомления в Telegram
- OllamaIntegration: Интеграция с Ollama
- MarketDatabase: Работа с базой данных
- Strategies: Торговые стратегии
"""

from .mt5_client import MT5Client
from .risk_manager import RiskManager, TradeStats, PositionSizeResult
from .telegram_bot import TelegramBot
from .ollama_integration import OllamaIntegration, AnalysisResult, KnowledgeItem
from .database import MarketDatabase

# Импорты для стратегий
from .strategies.base import BaseStrategy
from .strategies.sniper import SniperStrategy
from .strategies.smart_sniper import SmartSniperStrategy
from .strategies.smart_money import SmartMoneyStrategy

__all__ = [
    # Основные компоненты
    'MT5Client',
    'RiskManager',
    'TelegramBot',
    'OllamaIntegration',
    'MarketDatabase',

    # Стратегии
    'BaseStrategy',
    'SniperStrategy',
    'SmartSniperStrategy',
    'SmartMoneyStrategy',

    # Типы данных
    'TradeStats',
    'PositionSizeResult',
    'AnalysisResult',
    'KnowledgeItem'
]

# Версия модуля
__version__ = '1.0.0'

class _CoreModule:
    """Внутренний класс для инициализации модуля core"""

    def __init__(self):
        self._version = __version__

    @property
    def version(self) -> str:
        """Версия модуля core"""
        return self._version

# Инициализация модуля
core = _CoreModule()