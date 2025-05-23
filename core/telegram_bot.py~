import requests
from typing import Optional
from utils.logger import TradingLogger
from tkinter import messagebox
from datetime import datetime

class TelegramBot:
    def __init__(self, logger: TradingLogger, token: str = None, chat_id: str = None):
        """
        Инициализация бота

        :param logger: Объект логгера
        """
        self.logger = logger.logger  # Получаем корневой логгер
        self.token = token
        self.chat_id = chat_id
        self.enabled = False
        self.logger = logger.logger  # Получаем logging.Logger
        self.bot = None

    def initialize(self, token: str, chat_id: str) -> bool:
        """
        Инициализация бота с проверкой токена и chat_id

        :param token: Токен бота
        :param chat_id: ID чата
        :return: Успех инициализации
        """
        if not token or not chat_id:
            self.logger.warning("Попытка инициализировать Telegram бот без токена или chat_id")
            return False

        self.token = token
        self.chat_id = chat_id
        self.enabled = True
        self.logger.info("Telegram бот успешно инициализирован")
        return True

    def send_message(self, text: str) -> bool:
        """
        Отправка сообщения в Telegram

        :param text: Текст сообщения
        :return: Успех отправки
        """
        if not self.enabled:
            self.logger.warning("Попытка отправить сообщение через неинициализированный Telegram бот")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        params = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }

        try:
            response = requests.post(url, params=params, timeout=10)

            if response.status_code == 200:
                self.logger.info(f"Уведомление отправлено в Telegram: {text[:50]}...")
                return True

            error_msg = f"Ошибка отправки уведомления: {response.status_code} - {response.text}"
            self.logger.error(error_msg)

            # Попытка повторной отправки
            if response.status_code == 502:
                self.logger.warning("Получен ответ 502 от Telegram API. Повторная попытка...")
                response = requests.post(url, params=params, timeout=10)
                if response.status_code == 200:
                    self.logger.info("Уведомление отправлено после повторной попытки")
                    return True
                self.logger.error(f"Повторная попытка не удалась: {response.status_code} - {response.text}")

            return False

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Критическая ошибка подключения к Telegram API: {str(e)}")
            return False

    def notify_trade_opened(self, symbol: str, action: str, volume: float,
                            price: float, stop_loss: float, take_profit: float,
                            strategy: str) -> bool:
        """
        Уведомление об открытии сделки

        :param symbol: Символ
        :param action: Действие ('buy'/'sell')
        :param volume: Объем
        :param price: Цена входа
        :param stop_loss: Stop Loss
        :param take_profit: Take Profit
        :param strategy: Название стратегии
        :return: Успех отправки
        """
        if not self.enabled:
            self.logger.warning("Попытка отправить уведомление через неинициализированный Telegram бот")
            return False

        try:
            emoji = "📈" if action.lower() in ['buy', 'покупка'] else "📉"
            message = (
                f"<b>{emoji} Открыта сделка</b>\n"
                f"Стратегия: <code>{strategy}</code>\n"
                f"Символ: <code>{symbol}</code>\n"
                f"Действие: <code>{'Покупка' if action == 'buy' else 'Продажа'}</code>\n"
                f"Объем: <code>{volume:.2f}</code>\n"
                f"Цена: <code>{price:.5f}</code>\n"
                f"Стоп-лосс: <code>{stop_loss:.5f}</code>\n"
                f"Тейк-профит: <code>{take_profit:.5f}</code>"
            )
            return self.send_message(message)
        except Exception as e:
            self.logger.error(f"Ошибка формирования уведомления об открытии сделки: {str(e)}")
            return False

    def notify_trade_closed(self, symbol: str, position_id: int,
                            profit: float, price: float, reason: str) -> bool:
        """
        Уведомление о закрытии сделки

        :param symbol: Символ
        :param position_id: ID позиции
        :param profit: Прибыль
        :param price: Цена закрытия
        :param reason: Причина закрытия
        :return: Успех отправки
        """
        if not self.enabled:
            self.logger.warning("Попытка отправить уведомление о закрытии сделки без инициализации бота")
            return False

        try:
            emoji = "🟢" if profit >= 0 else "🔴"
            color = "green" if profit >= 0 else "red"
            message = (
                f"<b>📉 Закрыта сделка</b>\n"
                f"Символ: <code>{symbol}</code>\n"
                f"ID позиции: <code>{position_id}</code>\n"
                f"Прибыль: <font color='{color}'>{profit:.2f}</font>\n"
                f"Цена закрытия: <code>{price:.5f}</code>\n"
                f"Причина: <code>{reason}</code>"
            )
            return self.send_message(message)
        except Exception as e:
            self.logger.error(f"Ошибка формирования уведомления о закрытии сделки: {str(e)}")
            return False

    def notify_error(self, error_message: str) -> bool:
        """
        Уведомление об ошибке

        :param error_message: Сообщение об ошибке
        :return: Успех отправки
        """
        if not self.enabled:
            self.logger.warning("Попытка отправить уведомление об ошибке без инициализации бота")
            return False

        try:
            message = (
                f"<b>⚠️ Ошибка</b>\n"
                f"<code>{error_message}</code>"
            )
            return self.send_message(message)
        except Exception as e:
            self.logger.error(f"Ошибка формирования уведомления об ошибке: {str(e)}")
            return False

    def send_daily_report(self, database) -> bool:
        """
        Отправка ежедневного отчета

        :param database: База данных для получения статистики
        :return: Успех отправки
        """
        if not self.enabled:
            self.logger.warning("Попытка отправить отчет без инициализации бота")
            return False

        if not hasattr(database, 'get_trades'):
            self.logger.warning("База данных не поддерживает получение сделок")
            return False

        stats = {
            'day': datetime.now().strftime('%Y-%m-%d'),
            'trades': database.get_trades(limit=100),
            'summary': {
                'total': 0,
                'profit': 0.0
            }
        }

        for trade in stats['trades']:
            if trade['exit_time'].date() == datetime.now().date():
                stats['summary']['total'] += 1
                stats['summary']['profit'] += trade['profit']

        message = (
            f"📊 Отчет за {stats['day']}\n"
            f"Сделок: {stats['summary']['total']}\n"
            f"Прибыль: {stats['summary']['profit']:.2f}"
        )

        return self.send_message(message)