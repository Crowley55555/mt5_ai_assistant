"""
Модуль торговых стратегий для AI Trading Assistant

Содержит базовый класс стратегии и конкретные реализации:
- SniperStrategy (Снайпер) - скальпинг на малых таймфреймах
- SmartSniperStrategy (Смарт Снайпер) - интрадей с анализом объемов
- SmartMoneyStrategy (Смарт Мани) - отслеживание крупных игроков
"""

from .base import BaseStrategy
from .sniper import SniperStrategy
from .smart_sniper import SmartSniperStrategy
from .smart_money import SmartMoneyStrategy
from config.constants import StrategyNames

__all__ = [
    'BaseStrategy',
    'SniperStrategy',
    'SmartSniperStrategy',
    'SmartMoneyStrategy',
    'StrategyNames'
]

# Регистрация доступных стратегий
STRATEGIES = {
    StrategyNames.SNIPER: SniperStrategy,
    StrategyNames.SMART_SNIPER: SmartSniperStrategy,
    StrategyNames.SMART_MONEY: SmartMoneyStrategy
}

def get_strategy_class(strategy_name: str):
    """
    Возвращает класс стратегии по имени
    :param strategy_name: Одно из значений StrategyNames
    :return: Класс стратегии
    :raises ValueError: Если стратегия не найдена
    """
    if strategy_name not in STRATEGIES:
        raise ValueError(f"Неизвестная стратегия: {strategy_name}")
    return STRATEGIES[strategy_name]

# Логирование
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())