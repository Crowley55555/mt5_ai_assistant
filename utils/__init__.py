"""
Модуль вспомогательных утилит (utils)

Содержит:
- TradingLogger: Система логирования
- Helpers: Вспомогательные функции для работы с ценами, символами и таймфреймами
- Validators: Валидация входных данных
- Decorators: Полезные декораторы для функций
- Exceptions: Кастомные исключения приложения
"""

from .logger import TradingLogger
from .exceptions import (
    TradingError,
    TradingConnectionError,
    MT5ConnectionError,
    StrategyError,
    StrategyExecutionError,
    RiskManagementError,
    RiskValidationError,
    CredentialsValidationError,
    OrderError,
    InsufficientFundsError,
    ConfigurationError,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    OllamaError,
    KnowledgeBaseError,
    TelegramError,
)
from .helpers import (
    PriceFormatter,
    PipCalculator,
    SymbolValidator,
    TimeframeConverter,
    DictFormatter,
    # Функции для обратной совместимости
    format_price,
    calculate_pips,
    validate_symbol,
    timeframe_to_str,
    format_dict
)
from .validators import (
    CredentialsValidator,
    RiskParametersValidator,
    # Функции для обратной совместимости
    validate_login_credentials,
    validate_risk_parameters
)
from .decorators import (
    log_execution_time,
    handle_errors,
    retry
)

__all__ = [
    # Логирование
    'TradingLogger',

    # Исключения
    'TradingError',
    'TradingConnectionError',
    'MT5ConnectionError',
    'StrategyError',
    'StrategyExecutionError',
    'RiskManagementError',
    'RiskValidationError',
    'CredentialsValidationError',
    'OrderError',
    'InsufficientFundsError',
    'ConfigurationError',
    'DatabaseError',
    'DatabaseConnectionError',
    'DatabaseQueryError',
    'OllamaError',
    'KnowledgeBaseError',
    'TelegramError',

    # Хелперы
    'PriceFormatter',
    'PipCalculator',
    'SymbolValidator',
    'TimeframeConverter',
    'DictFormatter',
    'format_price',
    'calculate_pips',
    'validate_symbol',
    'timeframe_to_str',
    'format_dict',

    # Валидаторы
    'CredentialsValidator',
    'RiskParametersValidator',
    'validate_login_credentials',
    'validate_risk_parameters',

    # Декораторы
    'log_execution_time',
    'handle_errors',
    'retry'
]

# Версия модуля утилит
__version__ = '1.2.0'

class _UtilsPackage:
    """Класс-контейнер для инициализации и управления утилитами"""

    def __init__(self):
        self._logger = TradingLogger(name='utils')
        self._logger.info(f"Инициализация модуля utils (v{__version__})")

    @property
    def logger(self) -> TradingLogger:
        """Главный логгер модуля"""
        return self._logger

    @staticmethod
    def get_version() -> str:
        """Возвращает версию модуля"""
        return __version__

# Инициализация модуля при импорте
utils = _UtilsPackage()