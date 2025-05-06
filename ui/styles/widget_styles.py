import tkinter as tk
from tkinter import ttk


def configure_styles():
    """Конфигурация специфических стилей виджетов"""
    style = ttk.Style()

    # Стиль для успешных операций
    style.configure('Success.TLabel', foreground='#2e7d32')
    style.configure('Success.TButton', foreground='#2e7d32')

    # Стиль для ошибок
    style.configure('Error.TLabel', foreground='#c62828')
    style.configure('Error.TButton', foreground='#c62828')

    # Стиль для Combobox
    style.map('TCombobox',
              fieldbackground=[('readonly', '#ffffff')],
              selectbackground=[('readonly', '#ffffff')])