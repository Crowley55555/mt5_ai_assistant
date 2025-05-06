import tkinter as tk
from tkinter import ttk
from typing import Literal

ThemeType = Literal['light', 'dark']


def apply_theme(theme: ThemeType):
    """Применяет выбранную тему ко всем виджетам"""
    style = ttk.Style()

    if theme == 'dark':
        bg = '#333333'
        fg = '#ffffff'
        primary = '#4a6984'
    else:  # light
        bg = '#f5f5f5'
        fg = '#000000'
        primary = '#0078d7'

    # Базовые настройки
    style.theme_use('default')
    style.configure('.', background=bg, foreground=fg, font=('Segoe UI', 9))

    # Настройка конкретных виджетов
    style.configure('TFrame', background=bg)
    style.configure('TLabel', background=bg, foreground=fg)
    style.configure('TButton', padding=5)
    style.configure('TEntry', fieldbackground='#ffffff')
    style.configure('TCombobox', fieldbackground='#ffffff')

    # Цвета для состояний
    style.map('TButton',
              background=[('active', primary)],
              foreground=[('active', '#ffffff')])