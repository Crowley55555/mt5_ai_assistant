from typing import Dict, List, Union, Optional, Any
from decimal import Decimal
from config.constants import Timeframe



class PriceFormatter:
    """Класс для форматирования цен с учетом специфики инструментов"""

    _SYMBOL_DECIMALS = {
        'JPY': 3,
        'XAU': 2,
        'XAG': 2,
        'XPT': 2,
        'XPD': 2
    }

    _DEFAULT_DECIMALS = 5

    @classmethod
    def format_price(cls, price: Union[float, Decimal], symbol: str) -> str:
        """
        Форматирует цену с учетом особенностей инструмента

        Args:
            price: Цена для форматирования
            symbol: Символ инструмента (например, EURUSD, USDJPY)

        Returns:
            Отформатированная строка цены

        Raises:
            ValueError: Если входные параметры невалидны
        """
        if not isinstance(price, (float, Decimal)):
            raise ValueError("Цена должна быть числом или Decimal")

        if not isinstance(symbol, str) or len(symbol) < 3:
            raise ValueError("Символ должен быть строкой длиной не менее 3 символов")

        decimals = cls._get_decimals_for_symbol(symbol)
        return f"{float(price):.{decimals}f}"

    @classmethod
    def _get_decimals_for_symbol(cls, symbol: str) -> int:
        """Возвращает количество знаков после запятой для символа"""
        symbol_upper = symbol.upper()
        for key, value in cls._SYMBOL_DECIMALS.items():
            if key in symbol_upper:
                return value
        return cls._DEFAULT_DECIMALS


class PipCalculator:
    """Класс для расчета разницы цен в пипсах"""

    _SYMBOL_POINTS = {
        'JPY': 0.01,
        'XAU': 0.00001,
        'XAG': 0.00001,
        'XPT': 0.00001,
        'XPD': 0.00001
    }

    _DEFAULT_POINT = 0.0001

    @classmethod
    def calculate_pips(
            cls,
            price1: Union[float, Decimal],
            price2: Union[float, Decimal],
            symbol: Optional[str] = None
    ) -> float:
        """
        Вычисляет разницу между двумя ценами в пипсах

        Args:
            price1: Первая цена
            price2: Вторая цена
            symbol: Символ инструмента (опционально)

        Returns:
            Разница в пипсах

        Raises:
            ValueError: Если входные параметры невалидны
        """
        if not all(isinstance(p, (float, Decimal)) for p in [price1, price2]):
            raise ValueError("Цены должны быть числами или Decimal")

        if symbol is not None and not isinstance(symbol, str):
            raise ValueError("Символ должен быть строкой или None")

        point = cls._get_point_for_symbol(symbol) if symbol else cls._DEFAULT_POINT
        return abs(float(price1) - float(price2)) / point

    @classmethod
    def _get_point_for_symbol(cls, symbol: str) -> float:
        """Возвращает значение point для символа"""
        symbol_upper = symbol.upper()
        for key, value in cls._SYMBOL_POINTS.items():
            if key in symbol_upper:
                return value
        return cls._DEFAULT_POINT


class SymbolValidator:
    """Класс для валидации торговых символов"""

    @staticmethod
    def validate(symbol: str) -> bool:
        """
        Проверяет, является ли символ допустимым

        Args:
            symbol: Тикер инструмента

        Returns:
            True если символ валиден, иначе False
        """
        if not isinstance(symbol, str):
            return False

        symbol = symbol.upper()
        if len(symbol) < 6:
            return False

        # Проверяем формат: 3 буквы + 3 буквы (например, EURUSD)
        # или X + 2 буквы + 3 буквы (например, XAUUSD)
        if symbol.startswith('X') and len(symbol) == 6:
            return symbol[1:3].isalpha() and symbol[3:].isalpha()
        return symbol[:3].isalpha() and symbol[3:].isalpha()


class TimeframeConverter:
    """Класс для конвертации таймфреймов"""

    _TIMEFRAME_UNITS = [
        (43200, 'MN'),
        (10080, 'W'),
        (1440, 'D'),
        (60, 'H'),
        (1, 'M')
    ]

    @classmethod
    def to_string(cls, timeframe: Union[int, Timeframe]) -> str:
        """
        Конвертирует таймфрейм в читаемый формат

        Args:
            timeframe: Число минут или значение из Timeframes

        Returns:
            Строка типа M1, H1, D1 и т.д.

        Raises:
            ValueError: Если таймфрейм невалиден
        """
        try:
            value = timeframe.value if hasattr(timeframe, 'value') else timeframe

            if not isinstance(value, int) or value <= 0:
                raise ValueError("Таймфрейм должен быть положительным целым числом")

            for minutes, suffix in cls._TIMEFRAME_UNITS:
                if value >= minutes:
                    count = value // minutes
                    return f"{count}{suffix}"

            return f"M{value}"

        except Exception as e:
            raise ValueError(f"Ошибка преобразования таймфрейма {timeframe}: {str(e)}")


class DictFormatter:
    """Класс для форматирования словарей в читаемые строки"""

    @staticmethod
    def format(data: Dict[str, Any], max_items: int = 5) -> str:
        """
        Форматирует словарь в читаемую строку

        Args:
            data: Словарь для форматирования
            max_items: Максимальное количество элементов для списков

        Returns:
            Отформатированная строка
        """

        def _format_recursive(d: Dict[str, Any], indent: int = 0) -> List[str]:
            lines = []
            for key, value in d.items():
                if isinstance(value, dict):
                    lines.append(f"{' ' * indent}{key}:")
                    lines.extend(_format_recursive(value, indent + 2))
                elif isinstance(value, (list, tuple)):
                    items = value[-max_items:] if len(value) > max_items else value
                    lines.append(f"{' ' * indent}{key}: [{', '.join(map(str, items))}]")
                else:
                    lines.append(f"{' ' * indent}{key}: {value}")
            return lines

        return "\n".join(_format_recursive(data))


# Функции для обратной совместимости
def format_price(price: float, symbol: str) -> str:
    return PriceFormatter.format_price(price, symbol)


def calculate_pips(price1: float, price2: float, symbol: str = None) -> float:
    return PipCalculator.calculate_pips(price1, price2, symbol)


def validate_symbol(symbol: str) -> bool:
    return SymbolValidator.validate(symbol)


def timeframe_to_str(timeframe: Union[int, Timeframe]) -> str:
    return TimeframeConverter.to_string(timeframe)


def format_dict(data: Dict) -> str:
    return DictFormatter.format(data)