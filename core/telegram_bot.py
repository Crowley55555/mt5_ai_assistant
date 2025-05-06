import requests
from typing import Optional
from utils.logger import TradingLogger


class TelegramBot:
    def __init__(self, token: str, chat_id: str, logger: TradingLogger):
        self.token = token
        self.chat_id = chat_id
        self.logger = logger
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text: str) -> bool:
        """Отправка сообщения в Telegram"""
        if not self.token or not self.chat_id:
            self.logger.warning("Не настроен токен или chat_id для Telegram бота")
            return False

        url = f"{self.base_url}/sendMessage"
        params = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }

        try:
            response = requests.post(url, params=params)
            if response.status_code == 200:
                self.logger.info(f"Уведомление отправлено в Telegram: {text}")
                return True
            else:
                self.logger.error(
                    f"Ошибка отправки уведомления в Telegram: {response.status_code} - {response.text}"
                )
                return False
        except Exception as e:
            self.logger.error(f"Ошибка подключения к Telegram API: {str(e)}")
            return False

    def notify_trade_opened(self, symbol: str, action: str, volume: float,
                            price: float, stop_loss: float, take_profit: float,
                            strategy: str) -> bool:
        """Уведомление об открытии сделки"""
        message = (
            f"<b>📈 Открыта сделка</b>\n"
            f"Стратегия: <code>{strategy}</code>\n"
            f"Символ: <code>{symbol}</code>\n"
            f"Действие: <code>{'Покупка' if action == 'buy' else 'Продажа'}</code>\n"
            f"Объем: <code>{volume:.2f}</code>\n"
            f"Цена: <code>{price:.5f}</code>\n"
            f"Стоп-лосс: <code>{stop_loss:.5f}</code>\n"
            f"Тейк-профит: <code>{take_profit:.5f}</code>"
        )
        return self.send_message(message)

    def notify_trade_closed(self, symbol: str, position_id: int,
                            profit: float, price: float, reason: str) -> bool:
        """Уведомление о закрытии сделки"""
        profit_color = "🟢" if profit >= 0 else "🔴"
        message = (
            f"<b>📉 Закрыта сделка</b>\n"
            f"Символ: <code>{symbol}</code>\n"
            f"ID позиции: <code>{position_id}</code>\n"
            f"Прибыль: {profit_color} <code>{profit:.2f}</code>\n"
            f"Цена закрытия: <code>{price:.5f}</code>\n"
            f"Причина: <code>{reason}</code>"
        )
        return self.send_message(message)

    def notify_error(self, error_message: str) -> bool:
        """Уведомление об ошибке"""
        message = f"<b>⚠️ Ошибка</b>\n<code>{error_message}</code>"
        return self.send_message(message)

    python

    def send_daily_report(self, database: MarketDatabase):
        """Отправка ежедневного отчета в Telegram"""
        if not database or not self.chat_id:
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