"""
Модуль пользовательского интерфейса торгового ассистента

Содержит:
- MainWindow - главное окно приложения
- Компоненты интерфейса
- Стили и темы оформления
"""

from .main_window import TradingAssistantApp
from .components import (
    AccountManagerFrame,
    StrategyControlPanel,
    RiskManagementPanel,
    LogViewer
)
from .styles import ThemeManager

__all__ = [
    'TradingAssistantApp',
    'AccountManagerFrame',
    'StrategyControlPanel',
    'RiskManagementPanel',
    'LogViewer',
    'ThemeManager'
]

# Версия модуля UI
__version__ = '1.0.0'

# Инициализация стилей
def init_ui():
    """Инициализация стилей и тем интерфейса"""
    try:
        ThemeManager('light')
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Ошибка инициализации UI: {str(e)}")
        return False

# Автоматическая инициализация при импорте
if init_ui():
    import logging
    logging.getLogger(__name__).info(f"UI модуль инициализирован (v{__version__})")