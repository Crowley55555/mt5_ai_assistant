from tkinter import ttk
from typing import Literal, Dict

ThemeType = Literal['light', 'dark']


class ThemeManager:
    def __init__(self, theme: ThemeType = 'light'):
        """
        Менеджер тем

        :param theme: Выбранная тема ('light' или 'dark')
        """
        self.theme = theme
        self.style = ttk.Style()
        self.colors = self._get_colors(theme)
        self.fonts = {
            'default': ('Segoe UI', 9),
            'title': ('Segoe UI', 10, 'bold'),
            'code': ('Consolas', 9)
        }

    def _get_colors(self, theme: ThemeType) -> Dict[str, str]:
        """Получение цветовой палитры по теме"""
        return {
            'bg': '#f5f5f5' if theme == 'light' else '#333333',
            'fg': '#000000' if theme == 'light' else '#ffffff',
            'primary': '#0078d7' if theme == 'light' else '#4a6984',
            'success': '#2e7d32' if theme == 'light' else '#66bb6a',
            'error': '#c62828' if theme == 'light' else '#ef5350',
            'warning': '#ef6c00' if theme == 'light' else '#fb8c00',
            'text_bg': '#ffffff' if theme == 'light' else '#2e2e2e'
        }

    def apply_global_style(self):
        """Применение глобальных стилей ко всем виджетам"""
        # Базовые стили
        self.style.configure('.', background=self.colors['bg'], foreground=self.colors['fg'])
        self.style.configure('TFrame', background=self.colors['bg'])
        self.style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['fg'])

        # Кнопки
        self.style.configure('TButton', padding=5, font=self.fonts['default'])
        self.style.map('TButton',
                       background=[('active', self.colors['primary'])],
                       foreground=[('active', self.colors['fg'])])

        # Поля ввода
        self.style.configure('TEntry', fieldbackground=self.colors['text_bg'])
        self.style.configure('TCombobox', fieldbackground=self.colors['text_bg'])

    def apply_success_style(self):
        """Стиль успешных операций"""
        self.style.configure('Success.TLabel', foreground=self.colors['success'])
        self.style.configure('Success.TButton', foreground=self.colors['success'])
        self.style.map('Success.TButton',
                       background=[('active', self.colors['success']),
                                   ('disabled', '#a5d6a7')],
                       foreground=[('active', '#ffffff')])

    def apply_error_style(self):
        """Стиль ошибок"""
        self.style.configure('Error.TLabel', foreground=self.colors['error'])
        self.style.configure('Error.TButton', foreground=self.colors['error'])
        self.style.map('Error.TButton',
                       background=[('active', self.colors['error']),
                                   ('disabled', '#ef9a9a')],
                       foreground=[('active', '#ffffff')])

    def apply_warning_style(self):
        """Стиль предупреждений"""
        self.style.configure('Warning.TLabel', foreground=self.colors['warning'])
        self.style.configure('Warning.TButton', foreground=self.colors['warning'])
        self.style.map('Warning.TButton',
                       background=[('active', self.colors['warning']),
                                   ('disabled', '#ffe0b2')],
                       foreground=[('active', '#ffffff')])

    def apply_to_window(self, window):
        """Применение темы к окну приложения"""
        try:
            self.apply_global_style()
            self.apply_success_style()
            self.apply_error_style()
            self.apply_warning_style()
            self.logger.info(f"Тема '{self.theme}' успешно применена")
        except Exception as e:
            self.logger.error(f"Ошибка применения темы: {str(e)}")

    @classmethod
    def set_theme(cls, window, theme='light'):
        """Фабричный метод для установки темы"""
        manager = cls(theme)
        manager.apply_to_window(window)

    ThemeType = Literal['light', 'dark']

