"""
Модуль стилей и тем оформления

Содержит:
- apply_theme() - применение выбранной темы
- configure_styles() - настройка конкретных стилей виджетов
"""

# Импортируем функции из themes.py и widget_styles.py
from .themes import ThemeManager
from .widget_styles import StyleManager

# Экспортируем только эти функции по умолчанию
__all__ = [
    'ThemeManager',
    'StyleManager'
]