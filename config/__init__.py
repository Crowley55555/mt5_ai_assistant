"""
Модуль конфигурации торгового ассистента

Содержит:
- Класс Settings для работы с настройками
- Константы приложения
- Функции для управления конфигурацией
"""

from .settings import Settings
from .constants import (
    Timeframes,
    TradeAction,
    OrderType,
    StrategyNames
)

__all__ = [
    'Settings',
    'Timeframes',
    'TradeAction',
    'OrderType',
    'StrategyNames'
]

# Инициализация логгера (будет переопределена в основном приложении)
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

def get_version():
    """Возвращает версию конфигурационного модуля"""
    return '1.1.0'