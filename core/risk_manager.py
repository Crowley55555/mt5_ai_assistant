from typing import Dict
from datetime import datetime
import MetaTrader5 as mt5
import logging
from core.mt5_client import MT5Client
from typing import Optional

class RiskManager:
    def __init__(self, mt5_client: MT5Client, logger: logging.Logger):
        """
        Инициализация менеджера рисков

        :param mt5_client: Клиент для работы с MT5
        :param logger: Объект логгера
        """
        self.logger = logger
        self.mt5_client = mt5_client
        self.risk_per_trade = 1.0  # % от депозита
        self.risk_all_trades = 5.0  # % от депозита
        self.daily_risk = 10.0  # % от депозита
        self.daily_loss_limit = 0
        self.daily_profit = 0
        self.today = datetime.now().date()

    def get_trade_statistics(self, symbol: str = None, days: int = 30) -> Dict:
        """Анализ статистики сделок"""
        stats = {
            'total_trades': 0,
            'win_rate': 0.0,
            'avg_profit': 0.0,
            'symbol': symbol or 'all'
        }

        try:
            if not hasattr(self.mt5_client, 'database') or not self.mt5_client.database:
                self.logger.debug("База данных не доступна для анализа статистики")
                return stats

            trades = self.mt5_client.database.get_trades(strategy=symbol, limit=1000)
            if not trades:
                self.logger.debug(f"Нет данных о сделках для {symbol or 'всех'} стратегий")
                return stats

            profitable = [t for t in trades if t['profit'] > 0]
            avg_profit = sum(t['profit'] for t in trades) / len(trades)

            stats.update({
                'total_trades': len(trades),
                'win_rate': len(profitable) / len(trades),
                'avg_profit': avg_profit
            })

            self.logger.debug(f"Получена статистика для {symbol or 'всех'} стратегий")
            return stats

        except Exception as e:
            self.logger.warning(f"Ошибка получения статистики: {str(e)}")
            return stats

    def update_settings(self, risk_per_trade: float, risk_all_trades: float, daily_risk: float):
        """Обновление параметров риск-менеджмента"""
        if not all(0 < r <= 100 for r in [risk_per_trade, risk_all_trades, daily_risk]):
            raise ValueError("Все параметры риска должны быть между 0 и 100")

        if risk_per_trade > risk_all_trades:
            raise ValueError("Риск на сделку не может превышать общий риск по всем сделкам")

        if risk_all_trades > daily_risk:
            raise ValueError("Общий риск по всем сделкам не может превышать дневной риск")

        self.risk_per_trade = risk_per_trade
        self.risk_all_trades = risk_all_trades
        self.daily_risk = daily_risk
        self._update_daily_limits()
        self.logger.info(
            f"Обновлены параметры риска: "
            f"на сделку={risk_per_trade}%, "
            f"по всем сделкам={risk_all_trades}%, "
            f"дневной={daily_risk}%"
        )

    def _update_daily_limits(self):
        """Обновляет дневной лимит убытков на основе текущего баланса"""
        account_info = self.mt5_client.get_account_info()
        if not account_info:
            self.logger.warning("Не удалось получить информацию о счете для обновления дневного лимита")
            return

        self.daily_loss_limit = account_info['balance'] * (self.daily_risk / 100)
        self.logger.debug(f"Дневной лимит убытков установлен на уровне {self.daily_loss_limit:.2f}")

    def check_daily_limits(self) -> bool:
        """Проверка дневных лимитов"""
        current_date = datetime.now().date()

        if current_date != self.today:
            self.today = current_date
            self.daily_profit = 0
            self._update_daily_limits()
            self.logger.info(f"Смена дня. Новый дневной лимит: {self.daily_loss_limit:.2f}")

        account_info = self.mt5_client.get_account_info()
        if not account_info:
            self.logger.warning("Не удалось получить информацию о счете для проверки дневного лимита")
            return False

        # Получаем текущие позиции
        positions = mt5.positions_get()
        profit_positions = sum(p.profit for p in positions) if positions else 0

        # Получаем историю за сегодня
        history = mt5.history_orders_get(self.today, datetime.now())
        profit_history = 0
        if history:
            profit_history = sum(o.profit for o in history if o.time_setup.date() == current_date)

        total_profit = self.daily_profit + profit_positions + profit_history

        if total_profit <= -self.daily_loss_limit:
            self.logger.warning(
                f"Превышен дневной лимит убытков: {-total_profit:.2f}/{self.daily_loss_limit:.2f}"
            )
            return False

        return True

    def calculate_position_size(self, symbol: str, stop_loss_pips: float) -> Optional[float]:
        """Расчет объема позиции на основе риска"""
        if not self.check_daily_limits():
            self.logger.warning("Не удается рассчитать объем из-за превышения дневного лимита")
            return None

        account_info = self.mt5_client.get_account_info()
        if not account_info:
            self.logger.error("Не удалось получить информацию о счете для расчета объема")
            return None

        balance = account_info['balance']
        risk_amount = balance * (self.risk_per_trade / 100)

        symbol_info = self.mt5_client.get_symbol_info(symbol)
        if not symbol_info:
            self.logger.error(f"Не удалось получить информацию о символе {symbol}")
            return None

        tick_value = symbol_info['trade_tick_value']
        base_currency = symbol_info['currency_base']
        profit_currency = symbol_info['currency_profit']
        point = symbol_info['point']

        # Конвертируем значение тика в валюту счета
        if base_currency != account_info['currency']:
            # TODO: Реализовать конвертацию через API или внешний источник
            self.logger.warning(f"Конвертация для {base_currency} -> {account_info['currency']} не реализована")
            # Пока предполагаем равенство, но в реальности это нужно считать
            pass

        if stop_loss_pips == 0:
            self.logger.error("Нулевой стоп-лосс при расчете объема")
            return None

        volume = risk_amount / (stop_loss_pips * tick_value)

        # Приводим объем к требованиям биржи
        volume = max(volume, symbol_info.volume_min)
        volume = min(volume, symbol_info.volume_max)

        # Округляем до допустимого шага
        step = symbol_info.volume_step
        volume = round(volume / step) * step

        self.logger.info(
            f"Рассчитан объем для {symbol}: {volume:.2f} "
            f"(риск={self.risk_per_trade}%, стоп-лосс={stop_loss_pips} пунктов)"
        )

        return volume

    def check_all_trades_risk(self, new_trade_risk: float = 0) -> bool:
        """Проверка общего риска по всем сделкам"""
        account_info = self.mt5_client.get_account_info()
        if not account_info:
            self.logger.warning("Не удалось получить информацию о счете для проверки общего риска")
            return False

        balance = account_info['balance']
        max_all_trades_risk = balance * (self.risk_all_trades / 100)

        # Расчет текущего риска по всем открытым позициям
        try:
            positions = mt5.positions_get()
            open_positions_value = 0

            if positions:
                for position in positions:
                    # Здесь должна быть сложная логика расчета текущего риска по каждой открытой позиции
                    # В упрощенном виде используем фиксированную сумму всех позиций
                    open_positions_value += position.volume * position.price_current * position.contract_size

            # В реальном проекте здесь должен быть более сложный расчет
            # Например, сумма возможных потерь по всем позициям
            current_risk = open_positions_value + new_trade_risk

            if current_risk >= max_all_trades_risk:
                self.logger.warning(
                    f"Превышен общий риск по сделкам: {current_risk:.2f}/{max_all_trades_risk:.2f} "
                    f"({self.risk_all_trades}% от депозита)"
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"Ошибка проверки общего риска: {str(e)}")
            return False