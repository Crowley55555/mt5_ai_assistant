from typing import Dict, Optional
from datetime import datetime, time
from utils.logger import TradingLogger


class RiskManager:
    def __init__(self, mt5_client, logger: TradingLogger, database: Optional[MarketDatabase] = None):
        self.database = database
        self.mt5_client = mt5_client
        self.logger = logger
        self.risk_per_trade = 1.0  # % от депозита
        self.risk_all_trades = 5.0  # % от депозита
        self.daily_risk = 10.0  # % от депозита
        self.daily_loss_limit = 0
        self.daily_profit = 0
        self.today = datetime.now().date()

    def get_trade_statistics(self, symbol: str = None, days: int = 30) -> Dict:
        """Анализ статистики сделок из БД"""
        if not self.database:
            return {}

        stats = {
            'total_trades': 0,
            'win_rate': 0,
            'avg_profit': 0,
            'symbol': symbol or 'all'
        }

        trades = self.database.get_trades(symbol=symbol, limit=1000)
        if trades:
            profitable = [t for t in trades if t['profit'] > 0]
            stats.update({
                'total_trades': len(trades),
                'win_rate': len(profitable) / len(trades),
                'avg_profit': sum(t['profit'] for t in trades) / len(trades)
            })

        return stats

    def update_settings(self, risk_per_trade: float, risk_all_trades: float, daily_risk: float):
        """Обновление параметров риск-менеджмента"""
        self.risk_per_trade = risk_per_trade
        self.risk_all_trades = risk_all_trades
        self.daily_risk = daily_risk
        self.logger.info(
            f"Обновлены параметры риска: "
            f"на сделку={risk_per_trade}%, "
            f"на все сделки={risk_all_trades}%, "
            f"дневной={daily_risk}%"
        )

    def check_daily_limits(self) -> bool:
        """Проверка дневных лимитов"""
        today = datetime.now().date()
        if today != self.today:
            self.today = today
            self.daily_profit = 0
            account_info = self.mt5_client.get_account_info()
            if account_info:
                self.daily_loss_limit = account_info['balance'] * (self.daily_risk / 100)
                return True
            return False

        if self.daily_profit <= -self.daily_loss_limit:
            self.logger.warning(f"Достигнут дневной лимит убытков: {-self.daily_profit}/{self.daily_loss_limit}")
            return False

        return True

    def calculate_position_size(self, symbol: str, stop_loss_pips: float) -> Optional[float]:
        """Расчет объема позиции на основе риска"""
        if not self.check_daily_limits():
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

        # Расчет объема с учетом риска и стоп-лосса
        tick_value = symbol_info.trade_tick_value
        if symbol_info.currency_profit != account_info['currency']:
            # Конвертируем tick_value в валюту счета, если они разные
            # Здесь нужна дополнительная логика конвертации
            pass

        if tick_value == 0 or stop_loss_pips == 0:
            self.logger.error("Нулевое значение tick_value или stop_loss_pips")
            return None

        volume = risk_amount / (stop_loss_pips * tick_value)

        # Проверяем минимальный и максимальный объем
        volume = max(volume, symbol_info.volume_min)
        volume = min(volume, symbol_info.volume_max)

        # Округляем до допустимого шага объема
        step = symbol_info.volume_step
        volume = round(volume / step) * step

        self.logger.info(
            f"Рассчитан объем для {symbol}: {volume:.2f} "
            f"(риск={self.risk_per_trade}%, стоп-лосс={stop_loss_pips} пунктов)"
        )

        return volume

    def check_all_trades_risk(self, new_trade_risk: float = 0) -> bool:
        """Проверка общего риска по всем открытым сделкам"""
        account_info = self.mt5_client.get_account_info()
        if not account_info:
            self.logger.error("Не удалось получить информацию о счете для проверки общего риска")
            return False

        balance = account_info['balance']
        max_all_trades_risk = balance * (self.risk_all_trades / 100)

        # Здесь должна быть логика расчета текущего риска по всем открытым сделкам
        # Для примера будем считать, что текущий риск равен new_trade_risk
        current_risk = new_trade_risk

        if current_risk >= max_all_trades_risk:
            self.logger.warning(
                f"Превышен общий риск по сделкам: {current_risk}/{max_all_trades_risk} "
                f"({self.risk_all_trades}% от депозита)"
            )
            return False

        return True