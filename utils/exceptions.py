class TradingException(Exception):
    """Базовое исключение для торговых операций"""
    pass

class MT5ConnectionError(TradingException):
    """Ошибка подключения к MT5"""
    pass

class StrategyExecutionError(TradingException):
    """Ошибка выполнения стратегии"""
    pass

class RiskValidationError(TradingException):
    """Ошибка валидации параметров риска"""
    pass