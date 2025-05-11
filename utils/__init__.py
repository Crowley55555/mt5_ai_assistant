"""
Модуль вспомогательных утилит (utils)

Содержит:
- TradingLogger - система логирования
- Helpers - вспомогательные функции
- Validators - валидация данных
- Decorators - полезные декораторы
"""

from .logger import TradingLogger
from .helpers import (
    format_price,
    calculate_pips,
    validate_symbol,
    timeframe_to_str
)
from .validators import (
    validate_login_credentials,
    validate_risk_parameters
)
from .decorators import (
    log_execution_time,
    handle_errors
)

__all__ = [
    'TradingLogger',
    'format_price',
    'calculate_pips',
    'validate_symbol',
    'timeframe_to_str',
    'validate_login_credentials',
    'validate_risk_parameters',
    'log_execution_time',
    'handle_errors'
]

# Версия модуля утилит
__version__ = '1.1.0'


class _UtilsInitializer:
    """Приватный класс для инициализации утилит"""

    def __init__(self):
        self.logger = TradingLogger()
        self.logger.info(f"Модуль утилит инициализирован (v{__version__})")


# Автоматическая инициализация при импорте
_initializer = _UtilsInitializer()