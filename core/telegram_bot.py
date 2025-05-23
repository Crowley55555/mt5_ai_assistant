import requests
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from utils.logger import TradingLogger
from utils.exceptions import TelegramError
from requests.exceptions import RequestException


@dataclass
class TradeNotification:
    """Класс для хранения данных о торговом уведомлении"""
    symbol: str
    action: str
    volume: float
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: Optional[str] = None
    position_id: Optional[int] = None
    profit: Optional[float] = None
    reason: Optional[str] = None


class TelegramBot:
    """Класс для работы с Telegram Bot API"""

    BASE_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
    REQUEST_TIMEOUT = 10
    MAX_RETRIES = 2

    def __init__(self, logger: TradingLogger):
        """
        Инициализация бота

        Args:
            logger: Объект логгера TradingLogger
        """
        self.logger = logger
        self._token = None
        self._chat_id = None
        self._enabled = False

    @property
    def is_initialized(self) -> bool:
        """Проверка инициализации бота"""
        return self._enabled and self._token and self._chat_id

    def initialize(self, token: str, chat_id: str) -> bool:
        """
        Инициализация бота с проверкой токена и chat_id

        Args:
            token: Токен бота
            chat_id: ID чата

        Returns:
            bool: Успех инициализации
        """
        if not all(isinstance(x, str) for x in [token, chat_id]):
            self.logger.warning("Invalid token or chat_id format")
            return False

        self._token = token
        self._chat_id = chat_id
        self._enabled = True
        self.logger.info("Telegram bot initialized successfully")
        return True

    def send_message(self, text: str) -> bool:
        """
        Отправка сообщения в Telegram

        Args:
            text: Текст сообщения

        Returns:
            bool: Успех отправки

        Raises:
            TelegramError: При критических ошибках
        """
        if not self.is_initialized:
            self.logger.warning("Attempt to send message via uninitialized bot")
            return False

        url = self.BASE_API_URL.format(token=self._token)
        params = {
            'chat_id': self._chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = requests.post(
                    url,
                    params=params,
                    timeout=self.REQUEST_TIMEOUT
                )
                response.raise_for_status()

                self.logger.debug(f"Message sent to Telegram: {text[:50]}...")
                return True

            except RequestException as e:
                if attempt == self.MAX_RETRIES:
                    error_msg = f"Failed to send Telegram message after {self.MAX_RETRIES} attempts: {str(e)}"
                    self.logger.error(error_msg)
                    raise TelegramError(error_msg)
                continue

        return False

    def notify_trade(self, trade: TradeNotification) -> bool:
        """
        Уведомление о торговой операции

        Args:
            trade: Объект TradeNotification с данными о сделке

        Returns:
            bool: Успех отправки
        """
        if not self.is_initialized:
            self.logger.warning("Attempt to send trade notification via uninitialized bot")
            return False

        try:
            if trade.profit is not None:
                return self._send_trade_close_notification(trade)
            return self._send_trade_open_notification(trade)
        except Exception as e:
            self.logger.error(f"Error forming trade notification: {str(e)}")
            return False

    def _send_trade_open_notification(self, trade: TradeNotification) -> bool:
        """Формирование и отправка уведомления об открытии сделки"""
        emoji = "📈" if trade.action.lower() in ['buy', 'покупка'] else "📉"
        action_text = 'Покупка' if trade.action == 'buy' else 'Продажа'

        message = (
            f"<b>{emoji} Открыта сделка</b>\n"
            f"Стратегия: <code>{trade.strategy}</code>\n"
            f"Символ: <code>{trade.symbol}</code>\n"
            f"Действие: <code>{action_text}</code>\n"
            f"Объем: <code>{trade.volume:.2f}</code>\n"
            f"Цена: <code>{trade.price:.5f}</code>\n"
            f"Стоп-лосс: <code>{trade.stop_loss:.5f}</code>\n"
            f"Тейк-профит: <code>{trade.take_profit:.5f}</code>"
        )
        return self.send_message(message)

    def _send_trade_close_notification(self, trade: TradeNotification) -> bool:
        """Формирование и отправка уведомления о закрытии сделки"""
        emoji = "🟢" if trade.profit >= 0 else "🔴"
        color = "green" if trade.profit >= 0 else "red"

        message = (
            f"<b>📉 Закрыта сделка</b>\n"
            f"Символ: <code>{trade.symbol}</code>\n"
            f"ID позиции: <code>{trade.position_id}</code>\n"
            f"Прибыль: <font color='{color}'>{trade.profit:.2f}</font>\n"
            f"Цена закрытия: <code>{trade.price:.5f}</code>\n"
            f"Причина: <code>{trade.reason}</code>"
        )
        return self.send_message(message)

    def notify_error(self, error_message: str) -> bool:
        """
        Уведомление об ошибке

        Args:
            error_message: Сообщение об ошибке

        Returns:
            bool: Успех отправки
        """
        message = f"<b>⚠️ Ошибка</b>\n<code>{error_message}</code>"
        return self.send_message(message)

    def send_daily_report(self, trades_data: Dict[str, Any]) -> bool:
        """
        Отправка ежедневного отчета

        Args:
            trades_data: Данные о сделках за день

        Returns:
            bool: Успех отправки
        """
        if not trades_data or 'summary' not in trades_data:
            self.logger.warning("Invalid trades data format for daily report")
            return False

        message = (
            f"📊 Отчет за {trades_data.get('day', 'N/A')}\n"
            f"Сделок: {trades_data['summary'].get('total', 0)}\n"
            f"Прибыль: {trades_data['summary'].get('profit', 0):.2f}"
        )
        return self.send_message(message)