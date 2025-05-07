import tkinter as tk
from tkinter import ttk


class StyleManager:
    def __init__(self, theme='light'):
        """
        Управление стилями виджетов

        :param theme: Тема оформления ('light' или 'dark')
        """
        self.theme = theme
        self.colors = self._get_theme_colors(theme)
        self.style = ttk.Style()
        self._apply_base_styles()
        self._apply_specific_styles()

    def _get_theme_colors(self, theme):
        """Получение цветовой палитры по теме"""
        themes = {
            'light': {
                'bg': '#f5f5f5',
                'fg': '#000000',
                'primary': '#0078d7',
                'success': '#2e7d32',
                'error': '#c62828',
                'warning': '#ef6c00',
                'text_bg': '#ffffff',
                'entry_bg': '#ffffff'
            },
            'dark': {
                'bg': '#333333',
                'fg': '#ffffff',
                'primary': '#4a6984',
                'success': '#1b5e20',
                'error': '#d32f2f',
                'warning': '#fb8c00',
                'text_bg': '#2e2e2e',
                'entry_bg': '#eeeeee'
            }
        }
        return themes.get(theme, themes['light'])

    def _apply_base_styles(self):
        """Применение базовых стилей ко всем виджетам"""
        self.style.configure('.', background=self.colors['bg'], foreground=self.colors['fg'])

        # Базовые настройки контейнеров
        self.style.configure('TFrame', background=self.colors['bg'])
        self.style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['fg'])

        # Кнопки
        self.style.configure('TButton', padding=5)
        self.style.map('TButton',
                       background=[('active', self.colors['primary'])],
                       foreground=[('active', self.colors['fg'])])

        # Поля ввода
        self.style.configure('TEntry', fieldbackground=self.colors['entry_bg'])
        self.style.configure('TCombobox', fieldbackground=self.colors['entry_bg'])

    def _apply_specific_styles(self):
        """Применение специфических стилей"""
        # Успех
        self.style.configure('Success.TLabel', foreground=self.colors['success'])
        self.style.configure('Success.TButton', foreground=self.colors['success'])
        self.style.map('Success.TButton',
                       background=[('active', self.colors['success']),
                                   ('disabled', '#a5d6a7')],
                       foreground=[('active', '#ffffff')])

        # Ошибка
        self.style.configure('Error.TLabel', foreground=self.colors['error'])
        self.style.configure('Error.TButton', foreground=self.colors['error'])
        self.style.map('Error.TButton',
                       background=[('active', self.colors['error']),
                                   ('disabled', '#ef9a9a')],
                       foreground=[('active', '#ffffff')])

        # Предупреждение
        self.style.configure('Warning.TLabel', foreground=self.colors['warning'])
        self.style.configure('Warning.TButton', foreground=self.colors['warning'])
        self.style.map('Warning.TButton',
                       background=[('active', self.colors['warning']),
                                   ('disabled', '#ffe0b2')],
                       foreground=[('active', '#ffffff')])

    def get_style_name(self, widget_type: str, severity: str = None) -> str:
        """Возвращает имя стиля для виджета"""
        if severity:
            return f"{severity}.{widget_type}"
        return widget_type

    @classmethod
    def apply_custom_styles(cls, root: tk.Tk, theme='light'):
        """Фабричный метод для применения стилей"""
        manager = cls(theme)
        manager.apply_to_all_widgets(root)

    def apply_to_all_widgets(self, root: tk.Tk):
        """Применяет кастомные стили ко всем виджетам"""
        for widget in root.winfo_children():
            self._apply_to_widget(widget)

    def _apply_to_widget(self, widget):
        """Рекурсивное применение стилей к виджету и его дочерним элементам"""
        try:
            class_name = widget.winfo_class()
            style_name = self._map_widget_to_style(class_name)
            if style_name:
                widget.configure(style=style_name)
        except tk.TclError:
            pass  # Пропускаем виджеты, которые не поддерживают стиль

        # Рекурсия для дочерних элементов
        for child in widget.winfo_children():
            self._apply_to_widget(child)

    def _map_widget_to_style(self, class_name: str) -> str:
        """Сопоставление класса виджета с именем стиля"""
        mapping = {
            'TFrame': 'TFrame',
            'TLabel': 'TLabel',
            'TButton': 'TButton',
            'TEntry': 'TEntry',
            'TCombobox': 'TCombobox'
        }
        return mapping.get(class_name, '')