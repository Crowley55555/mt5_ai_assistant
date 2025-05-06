from typing import Union
from config.constants import Timeframes


def format_price(price: float, symbol: str) -> str:
    """
    Форматирует цену в зависимости от инструмента

    :param price: Цена для форматирования
    :param symbol: Тикер инструмента (например, 'EURUSD')
    :return: Отформатированная строка цены
    """
    decimals = 5 if 'JPY' not in symbol else 3
    return f"{price:.{decimals}f}"


def calculate_pips(price1: float, price2: float, symbol: str) -> float:
    """
    Вычисляет разницу в пипсах между двумя ценами

    :param price1: Первая цена
    :param price2: Вторая цена
    :param symbol: Тикер инструмента
    :return: Разница в пипсах
    """
    multiplier = 100 if 'JPY' in symbol else 10000
    return round(abs(price1 - price2) * multiplier, 1)


def validate_symbol(symbol: str) -> bool:
    """
    Проверяет валидность символа

    :param symbol: Тикер для проверки
    :return: True если символ валиден
    """
    return isinstance(symbol, str) and len(symbol) >= 6 and symbol.isalpha()


def timeframe_to_str(timeframe: Union[int, Timeframes]) -> str:
    """
    Конвертирует таймфрейм в читаемую строку

    :param timeframe: Число минут или значение Timeframes
    :return: Строковое представление (например, 'H1')
    """
    if isinstance(timeframe, Timeframes):
        timeframe = timeframe.value

    if timeframe >= 43200:
        return f"{timeframe // 43200}MN"
    elif timeframe >= 10080:
        return f"{timeframe // 10080}W"
    elif timeframe >= 1440:
        return f"{timeframe // 1440}D"
    elif timeframe >= 60:
        return f"{timeframe // 60}H"
    return f"{timeframe}M"