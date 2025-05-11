from enum import Enum, IntEnum
from typing import Final, Dict, Tuple

class Timeframe(IntEnum):
    """Таймфреймы для торговли (в минутах)"""
    M1 = 1
    M5 = 5
    M15 = 15
    M30 = 30
    H1 = 60
    H4 = 240
    D1 = 1440
    W1 = 10080
    MN1 = 43200

    @classmethod
    def get_display_name(cls, timeframe: 'Timeframe') -> str:
        """Возвращает читаемое название таймфрейма"""
        names: Dict['Timeframe', str] = {
            cls.M1: "1 Минута",
            cls.M5: "5 Минут",
            cls.M15: "15 Минут",
            cls.M30: "30 Минут",
            cls.H1: "1 Час",
            cls.H4: "4 Часа",
            cls.D1: "1 День",
            cls.W1: "1 Неделя",
            cls.MN1: "1 Месяц"
        }
        return names.get(timeframe, f"Unknown ({timeframe.value})")

class TradeAction(str, Enum):
    """Действия с ордерами"""
    BUY = 'buy'
    SELL = 'sell'
    CLOSE = 'close'
    MODIFY = 'modify'

    @property
    def display_name(self) -> str:
        """Возвращает локализованное название действия"""
        names: Dict['TradeAction', str] = {
            TradeAction.BUY: "Покупка",
            TradeAction.SELL: "Продажа",
            TradeAction.CLOSE: "Закрытие",
            TradeAction.MODIFY: "Изменение"
        }
        return names[self]

class OrderType(IntEnum):
    """Типы ордеров"""
    MARKET = 0
    LIMIT = 1
    STOP = 2
    STOP_LIMIT = 3

    def is_pending(self) -> bool:
        """Проверяет, является ли ордер отложенным"""
        return self in (OrderType.LIMIT, OrderType.STOP, OrderType.STOP_LIMIT)

class StrategyName(str, Enum):
    """Названия торговых стратегий"""
    SNIPER = "sniper"
    SMART_SNIPER = "smart_sniper"
    SMART_MONEY = "smart_money"

    @property
    def display_name(self) -> str:
        """Возвращает читаемое название стратегии"""
        names: Dict['StrategyName', str] = {
            StrategyName.SNIPER: "Снайпер",
            StrategyName.SMART_SNIPER: "Смарт Снайпер",
            StrategyName.SMART_MONEY: "Смарт Мани"
        }
        return names[self]

# Константы для всего приложения
DEFAULT_LOT_SIZE: Final[float] = 0.1
MAX_RETRY_ATTEMPTS: Final[int] = 3
REQUEST_TIMEOUT: Final[Tuple[int, int]] = (5, 10)  # (connect, read)