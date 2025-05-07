from typing import Union
from config.constants import Timeframes


def format_price(price: float, symbol: str) -> str:
    """
    Форматирует цену с учетом особенностей инструмента

    :param price: Цена
    :param symbol: Символ (например, EURUSD, USDJPY)
    :return: Отформатированная строка цены
    """
    if not isinstance(price, (int, float)):
        raise ValueError("Цена должна быть числом")

    if not isinstance(symbol, str):
        raise ValueError("Символ должен быть строкой")

    # Определяем количество знаков после запятой
    if 'JPY' in symbol.upper():
        decimals = 3
    elif 'XAU' in symbol.upper() or 'XAG' in symbol.upper():
        decimals = 2
    else:
        decimals = 5

    return f"{price:.{decimals}f}"


def calculate_pips(price1: float, price2: float, symbol: str = None) -> float:
    """
    Вычисляет разницу между двумя ценами в пипсах

    :param price1: Первая цена
    :param price2: Вторая цена
    :param symbol: Символ (для определения точки)
    :return: Разница в пипсах
    """
    if not all(isinstance(p, (int, float)) for p in [price1, price2]):
        raise ValueError("Обе цены должны быть числами")

    if symbol and not isinstance(symbol, str):
        raise ValueError("Символ должен быть строкой или None")

    point = 0.0001
    if symbol and 'JPY' in symbol.upper():
        point = 0.01
    elif symbol and ('XAU' in symbol.upper() or 'XAG' in symbol.upper()):
        point = 0.00001

    return abs(price1 - price2) / point


def validate_symbol(symbol: str) -> bool:
    """
    Проверяет, является ли символ допустимым

    :param symbol: Тикер инструмента
    :return: True, если символ валиден
    """
    if not isinstance(symbol, str):
        return False

    symbol = symbol.upper()
    if len(symbol) < 6:
        return False

    # Пример: EURUSD, GBPUSD, BTCUSD, XAUEUR и т.д.
    return symbol[:3].isalpha() and symbol[3:].isalpha()


def timeframe_to_str(timeframe: Union[int, Timeframes]) -> str:
    """
    Конвертирует таймфрейм в читаемый формат

    :param timeframe: Число минут или значение из Timeframes
    :return: Строка типа M1, H1, D1 и т.д.
    """
    try:
        if hasattr(timeframe, 'value'):
            value = timeframe.value
        elif isinstance(timeframe, int):
            value = timeframe
        else:
            raise ValueError(f"Неверный тип таймфрейма: {type(timeframe)}")

        if value >= 43200:
            return f"{value // 43200}MN"
        elif value >= 10080:
            return f"{value // 10080}W"
        elif value >= 1440:
            return f"{value // 1440}D"
        elif value >= 60:
            return f"{value // 60}H"
        else:
            return f"M{value}"

    except Exception as e:
        raise ValueError(f"Ошибка преобразования таймфрейма {timeframe}: {str(e)}")