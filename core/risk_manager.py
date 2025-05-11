from dataclasses import dataclass
from decimal import Decimal, getcontext
from datetime import datetime, date
from typing import Dict, Optional
import MetaTrader5 as mt5

from utils.logger import TradingLogger
from utils.exceptions import RiskManagementError, RiskValidationError
from core.mt5_client import MT5Client

# Установка точности для Decimal
getcontext().prec = 6


@dataclass
class TradeStats:
    """Класс для хранения статистики сделок"""
    total_trades: int = 0
    win_rate: float = 0.0
    avg_profit: float = 0.0
    symbol: str = 'all'


@dataclass
class PositionSizeResult:
    """Результат расчета объема позиции"""
    volume: float
    risk_amount: float
    risk_percent: float
    stop_loss_pips: float


class RiskManager:
    """Класс для управления рисками торговой системы."""

    def __init__(self, mt5_client: MT5Client, logger: TradingLogger):
        """
        Инициализация менеджера рисков.

        Args:
            mt5_client: Клиент для работы с MT5
            logger: Объект логгера
        """
        self.logger = logger
        self.mt5_client = mt5_client
        self._risk_per_trade = Decimal('1.0')
        self._risk_all_trades = Decimal('5.0')
        self._daily_risk = Decimal('10.0')
        self.daily_loss_limit = Decimal('0')
        self.daily_profit = Decimal('0')
        self.today = date.today()

    @property
    def risk_per_trade(self) -> float:
        """Риск на одну сделку (% от депозита)."""
        return float(self._risk_per_trade)

    @property
    def risk_all_trades(self) -> float:
        """Общий риск по всем сделкам (% от депозита)."""
        return float(self._risk_all_trades)

    @property
    def daily_risk(self) -> float:
        """Дневной риск (% от депозита)."""
        return float(self._daily_risk)

    def get_trade_statistics(self, symbol: Optional[str] = None) -> TradeStats:
        """
        Анализ статистики сделок.

        Args:
            symbol: Фильтр по символу (опционально). Если None, анализируются все сделки.

        Returns:
            TradeStats: Объект с торговой статистикой
        """
        stats = TradeStats(symbol=symbol or 'all')

        try:
            if not hasattr(self.mt5_client, 'database') or not self.mt5_client.database:
                self.logger.debug("База данных недоступна для анализа статистики")
                return stats

            trades = self.mt5_client.database.get_trades(strategy=symbol, limit=1000)
            if not trades:
                self.logger.debug(f"Нет данных о сделках для {stats.symbol}")
                return stats

            profitable = [t for t in trades if t['profit'] > 0]
            avg_profit = sum(Decimal(str(t['profit'])) for t in trades) / len(trades)

            stats.total_trades = len(trades)
            stats.win_rate = len(profitable) / len(trades)
            stats.avg_profit = float(avg_profit)

            self.logger.debug(f"Статистика для {stats.symbol}: {stats}")
            return stats

        except Exception as e:
            self.logger.warning(f"Ошибка получения статистики: {str(e)}")
            return stats

    def update_settings(self, risk_per_trade: float, risk_all_trades: float, daily_risk: float) -> None:
        """
        Обновление параметров риска.

        Args:
            risk_per_trade: Риск на сделку (%)
            risk_all_trades: Общий риск (%)
            daily_risk: Дневной риск (%)

        Raises:
            RiskValidationError: При невалидных параметрах
        """
        try:
            risk_per_trade_dec = Decimal(str(risk_per_trade))
            risk_all_trades_dec = Decimal(str(risk_all_trades))
            daily_risk_dec = Decimal(str(daily_risk))

            self._validate_risk_parameters(risk_per_trade_dec, risk_all_trades_dec, daily_risk_dec)

            self._risk_per_trade = risk_per_trade_dec
            self._risk_all_trades = risk_all_trades_dec
            self._daily_risk = daily_risk_dec
            self._update_daily_limits()

            self.logger.info(
                f"Обновлены параметры риска: "
                f"на сделку={float(self._risk_per_trade)}%, "
                f"общий={float(self._risk_all_trades)}%, "
                f"дневной={float(self._daily_risk)}%"
            )

        except RiskValidationError:
            raise
        except Exception as e:
            error_msg = f"Ошибка обновления настроек риска: {str(e)}"
            self.logger.error(error_msg)
            raise RiskManagementError(error_msg) from e
    @staticmethod
    def _validate_risk_parameters(risk_per_trade: Decimal, risk_all_trades: Decimal, daily_risk: Decimal) -> None:
        """Валидация параметров риска."""
        if not all(Decimal('0') < r <= Decimal('100') for r in [risk_per_trade, risk_all_trades, daily_risk]):
            raise RiskValidationError(
                message="Параметры риска должны быть в диапазоне 0-100%",
                parameter="risk_settings",
                value=f"{risk_per_trade}, {risk_all_trades}, {daily_risk}",
                valid_range="0-100%"
            )

        if risk_per_trade > risk_all_trades:
            raise RiskValidationError(
                message="Риск на сделку превышает общий риск",
                parameter="risk_per_trade",
                value=float(risk_per_trade),
                valid_range=f"0-{float(risk_all_trades)}%"
            )

        if risk_all_trades > daily_risk:
            raise RiskValidationError(
                message="Общий риск превышает дневной лимит",
                parameter="risk_all_trades",
                value=float(risk_all_trades),
                valid_range=f"0-{float(daily_risk)}%"
            )

    def _update_daily_limits(self) -> None:
        """Обновление дневных лимитов на основе текущего баланса."""
        account_info = self.mt5_client.get_account_info()
        if not account_info:
            raise RiskManagementError("Не удалось получить информацию о счете")

        balance = Decimal(str(account_info['balance']))
        self.daily_loss_limit = balance * (self._daily_risk / Decimal('100'))
        self.logger.debug(f"Обновлен дневной лимит убытков: {float(self.daily_loss_limit):.2f}")

    def check_daily_limits(self) -> bool:
        """
        Проверка дневных лимитов.

        Returns:
            bool: True если лимиты не превышены, иначе False
        """
        current_date = date.today()
        if current_date != self.today:
            self._reset_daily_values(current_date)

        try:
            total_profit = self._calculate_daily_profit(current_date)
            if total_profit <= -self.daily_loss_limit:
                self.logger.warning(
                    f"Превышен дневной лимит: {-float(total_profit):.2f}/"
                    f"{float(self.daily_loss_limit):.2f}"
                )
                return False
            return True

        except Exception as e:
            error_msg = f"Ошибка проверки дневных лимитов: {str(e)}"
            self.logger.error(error_msg)
            raise RiskManagementError(error_msg) from e

    def _reset_daily_values(self, current_date: date) -> None:
        """Сброс дневных значений при смене дня."""
        self.today = current_date
        self.daily_profit = Decimal('0')
        self._update_daily_limits()
        self.logger.info(f"Новый торговый день {current_date}. Лимит: {float(self.daily_loss_limit):.2f}")

    def _calculate_daily_profit(self, current_date: date) -> Decimal:
        """Расчет дневной прибыли/убытков."""
        positions_profit = self._get_open_positions_profit()
        history_profit = self._get_history_profit(current_date)
        return self.daily_profit + positions_profit + history_profit

    def _get_open_positions_profit(self) -> Decimal:
        """Получение прибыли по открытым позициям."""
        try:
            positions = mt5.positions_get()
            if not positions:
                return Decimal('0')

            total = Decimal('0')
            for p in positions:
                total += Decimal(str(float(p.profit)))
            return total

        except Exception as e:
            self.logger.warning(f"Ошибка получения открытых позиций: {str(e)}")
            return Decimal('0')

    def _get_history_profit(self, current_date: date) -> Decimal:
        """Получение прибыли по истории сделок за текущий день."""
        try:
            history = mt5.history_orders_get(current_date, datetime.now())
            if not history:
                return Decimal('0')

            total = Decimal('0')
            for o in history:
                if o.time_setup.date() == current_date:
                    total += Decimal(str(float(o.profit)))
            return total

        except Exception as e:
            self.logger.warning(f"Ошибка получения истории сделок: {str(e)}")
            return Decimal('0')

    def calculate_position_size(
            self,
            symbol: str,
            stop_loss_pips: float
    ) -> Optional[PositionSizeResult]:
        """
        Расчет объема позиции.

        Args:
            symbol: Торговый символ
            stop_loss_pips: Размер стоп-лосса в пунктах

        Returns:
            PositionSizeResult: Результат расчета или None при ошибке
        """
        if not self.check_daily_limits():
            self.logger.warning("Дневной лимит превышен")
            return None

        try:
            stop_loss_pips_dec = Decimal(str(stop_loss_pips))
            self._validate_stop_loss(stop_loss_pips_dec)

            account_info = self.mt5_client.get_account_info()
            if not account_info:
                raise RiskManagementError("Не удалось получить информацию о счете")

            symbol_info = self._get_validated_symbol_info(symbol)
            balance = Decimal(str(account_info['balance']))
            risk_amount = balance * (self._risk_per_trade / Decimal('100'))

            tick_value = Decimal(str(symbol_info['trade_tick_value']))
            volume = risk_amount / (stop_loss_pips_dec * tick_value)
            volume = self._adjust_volume_to_constraints(volume, symbol_info)

            result = PositionSizeResult(
                volume=float(volume),
                risk_amount=float(risk_amount),
                risk_percent=float(self._risk_per_trade),
                stop_loss_pips=float(stop_loss_pips_dec)
            )

            self.logger.info(
                f"Рассчитан объем для {symbol}: {result.volume:.2f}, "
                f"риск: {result.risk_amount:.2f} {account_info['currency']}"
            )
            return result

        except RiskValidationError as e:
            self.logger.warning(f"Невалидные параметры: {str(e)}")
            return None
        except Exception as e:
            error_msg = f"Ошибка расчета объема: {str(e)}"
            self.logger.error(error_msg)
            raise RiskManagementError(error_msg) from e

    @staticmethod
    def _validate_stop_loss(stop_loss: Decimal) -> None:
        """Валидация значения стоп-лосса."""
        if stop_loss <= Decimal('0'):
            raise RiskValidationError(
                message="Стоп-лосс должен быть положительным",
                parameter="stop_loss_pips",
                value=float(stop_loss),
                valid_range=">0"
            )

    def _get_validated_symbol_info(self, symbol: str) -> Dict:
        """Получение и валидация информации о символе."""
        symbol_info = self.mt5_client.get_symbol_info(symbol)
        if not symbol_info:
            raise RiskManagementError(f"Не удалось получить информацию о символе {symbol}")
        return symbol_info

    @staticmethod
    def _adjust_volume_to_constraints(volume: Decimal, symbol_info: Dict) -> Decimal:
        """Корректировка объема под ограничения символа."""
        min_volume = Decimal(str(symbol_info['volume_min']))
        max_volume = Decimal(str(symbol_info['volume_max']))
        step = Decimal(str(symbol_info['volume_step']))

        volume = max(min(volume, max_volume), min_volume)
        volume = (volume // step) * step
        return volume

    def check_all_trades_risk(self, new_trade_risk: float = 0) -> bool:
        """
        Проверка общего риска по всем сделкам.

        Args:
            new_trade_risk: Дополнительный риск от новой сделки

        Returns:
            bool: True если риск в пределах лимита
        """
        try:
            account_info = self.mt5_client.get_account_info()
            if not account_info:
                self.logger.warning("Не удалось получить информацию о счете")
                return False

            balance = Decimal(str(account_info['balance']))
            max_risk = balance * (self._risk_all_trades / Decimal('100'))
            current_risk = self._calculate_current_risk(new_trade_risk)

            if current_risk >= max_risk:
                self.logger.warning(
                    f"Превышен общий риск: {float(current_risk):.2f}/"
                    f"{float(max_risk):.2f}"
                )
                return False
            return True

        except Exception as e:
            error_msg = f"Ошибка проверки общего риска: {str(e)}"
            self.logger.error(error_msg)
            raise RiskManagementError(error_msg) from e

    def _calculate_current_risk(self, new_trade_risk: float) -> Decimal:
        """Расчет текущего общего риска."""
        open_positions_risk = self._calculate_open_positions_risk()
        return open_positions_risk + Decimal(str(new_trade_risk))

    def _calculate_open_positions_risk(self) -> Decimal:
        """Расчет риска по открытым позициям."""
        try:
            positions = mt5.positions_get()
            if not positions:
                return Decimal('0')

            total_risk = Decimal('0')
            for position in positions:
                symbol_info = self.mt5_client.get_symbol_info(position.symbol)
                if not symbol_info:
                    continue

                position_risk = (
                        Decimal(str(position.volume)) *
                        Decimal(str(position.price_current)) *
                        Decimal(str(symbol_info['trade_tick_value']))
                )
                total_risk += position_risk

            return total_risk

        except Exception as e:
            self.logger.warning(f"Ошибка расчета риска позиций: {str(e)}")
            return Decimal('0')