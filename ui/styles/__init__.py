"""
Стили и темы оформления

Содержит:
- apply_theme() - применение выбранной темы
- стили для конкретных виджетов
"""

from .themes import apply_theme
from .widget_styles import configure_styles

__all__ = ['apply_theme', 'configure_styles']