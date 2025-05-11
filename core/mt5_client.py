import pandas as pd
import MetaTrader5 as mt5
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime
from utils.logger import TradingLogger
from config.constants import TradeAction, Timeframe
from core.database import MarketDatabase
from utils.exceptions import MT5ConnectionError, TradingConnectionError, OrderError, InsufficientFundsError


class MT5Client:
    """Класс для работы с MetaTrader 5 API"""

    _MAGIC_NUMBER: int = 123456
    _DEVIATION: int = 10
    _ORDER_FILLING = mt5.ORDER_FILLING_IOC
    _ORDER_TIME = mt5.ORDER_TIME_GTC

    def __init__(self, logger: TradingLogger, database: Optional[MarketDatabase] = None):
        """
        Инициализация клиента MT5

        Args:
            logger: Объект логгера
            database: Объект базы данных рыночных данных (опционально)
        """
        self._logger = logger
        self._database = database
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Проверка подключения к терминалу"""
        return self._connected

    def connect(self, login: int, password: str, server: str, path: str) -> bool:
        """
        Подключение к терминалу MT5

        Args:
            login: Номер счета
            password: Пароль
            server: Название сервера
            path: Путь к терминалу

        Returns:
            bool: Успешность подключения
        """
        try:
            if not all([login, password, server, path]):
                raise ValueError("Неполные данные для подключения")

            if not Path(path).exists():
                raise FileNotFoundError(f"Файл терминала не найден: {path}")

            if not mt5.initialize(login=login, password=password, server=server, path=path):
                error_code = mt5.last_error()
                raise MT5ConnectionError(
                    server=server,
                    login=login,
                    error_code=error_code,
                    logger=self._logger
                )

            self._connected = True
            self._logger.info(f"Успешное подключение к MT5 (логин: {login}, сервер: {server})")
            return True

        except Exception as e:
            self._logger.error(f"Ошибка подключения: {str(e)}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Отключение от терминала MT5"""
        if self._connected:
            mt5.shutdown()
            self._connected = False
            self._logger.info("Отключение от MT5")

    def get_account_info(self) -> Dict[str, float]:
        """
        Получение информации о торговом счете

        Returns:
            Dict: Информация о счете
        """
        if not self._connected:
            raise TradingConnectionError("MT5", "Нет подключения", logger=self._logger)

        account_info = mt5.account_info()
        if account_info is None:
            error_code = mt5.last_error()
            raise TradingConnectionError(
                "MT5",
                f"Ошибка получения информации о счете: {error_code}",
                logger=self._logger
            )

        return {
            'login': account_info.login,
            'balance': account_info.balance,
            'equity': account_info.equity,
            'margin': account_info.margin,
            'free_margin': account_info.margin_free,
            'leverage': account_info.leverage
        }

    def get_symbols(self) -> List[str]:
        """
        Получение списка доступных символов

        Returns:
            List[str]: Список символов
        """
        if not self._connected:
            raise TradingConnectionError("MT5", "Нет подключения", logger=self._logger)

        symbols = mt5.symbols_get()
        return [s.name for s in symbols] if symbols else []

    def get_historical_data(
            self,
            symbol: str,
            timeframe: Timeframe,
            count: int,
            from_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        Получение исторических данных

        Args:
            symbol: Торговый символ
            timeframe: Таймфрейм
            count: Количество баров
            from_date: Дата начала (опционально)

        Returns:
            Optional[pd.DataFrame]: DataFrame с данными или None
        """
        if not self._connected:
            raise TradingConnectionError("MT5", "Нет подключения", logger=self._logger)

        try:
            # Пробуем получить из кэша
            if self._database:
                cached_data = self._database.get_market_data(symbol, timeframe, count)
                if cached_data is not None:
                    return cached_data

            # Получаем данные из MT5
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count) if from_date is None else \
                mt5.copy_rates_from(symbol, timeframe, from_date, count)

            if not rates:
                error_code = mt5.last_error()
                self._logger.warning(f"Нет данных для {symbol}: {error_code}")
                return None

            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)

            if self._database:
                self._database.save_market_data(symbol, timeframe, df)

            return df

        except Exception as e:
            self._logger.error(f"Ошибка получения данных: {str(e)}")
            return None

    def place_order(
            self,
            symbol: str,
            action: TradeAction,
            volume: float,
            stop_loss: float = 0.0,
            take_profit: float = 0.0,
            comment: str = ""
    ) -> int:
        """
        Размещение рыночного ордера

        Args:
            symbol: Торговый символ
            action: Тип действия (BUY/SELL)
            volume: Объем
            stop_loss: Уровень стоп-лосса
            take_profit: Уровень тейк-профита
            comment: Комментарий

        Returns:
            int: Номер ордера

        Raises:
            OrderError: Если не удалось разместить ордер
        """
        if not self._connected:
            raise TradingConnectionError("MT5", "Нет подключения", logger=self._logger)

        try:
            # Проверка символа
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                raise OrderError(
                    message=f"Символ {symbol} не найден",
                    symbol=symbol,
                    logger=self._logger
                )

            # Проверка баланса
            account_info = self.get_account_info()
            required_margin = volume * symbol_info.margin
            if account_info['free_margin'] < required_margin:
                raise InsufficientFundsError(
                    required=required_margin,
                    available=account_info['free_margin'],
                    currency=account_info['currency'],
                    logger=self._logger
                )

            # Подготовка запроса
            price = mt5.symbol_info_tick(symbol).ask if action == TradeAction.BUY else \
                mt5.symbol_info_tick(symbol).bid

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_BUY if action == TradeAction.BUY else mt5.ORDER_TYPE_SELL,
                "price": price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": self._DEVIATION,
                "magic": self._MAGIC_NUMBER,
                "comment": comment,
                "type_time": self._ORDER_TIME,
                "type_filling": self._ORDER_FILLING,
            }

            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                raise OrderError(
                    message=f"Ошибка размещения ордера: {result.comment}",
                    symbol=symbol,
                    logger=self._logger
                )

            self._logger.info(
                f"Ордер #{result.order} на {symbol} {action} {volume} по {price}"
            )
            return result.order

        except Exception as e:
            if not isinstance(e, (OrderError, InsufficientFundsError)):
                raise OrderError(
                    message=f"Ошибка размещения ордера: {str(e)}",
                    symbol=symbol,
                    logger=self._logger
                ) from e
            raise

    def close_position(self, position_id: int, volume: Optional[float] = None) -> bool:
        """
        Закрытие позиции

        Args:
            position_id: ID позиции
            volume: Объем для закрытия (опционально)

        Returns:
            bool: Успешность операции
        """
        if not self._connected:
            raise TradingConnectionError("MT5", "Нет подключения", logger=self._logger)

        try:
            positions = mt5.positions_get(ticket=position_id)
            if not positions:
                raise OrderError(
                    message=f"Позиция #{position_id} не найдена",
                    logger=self._logger
                )

            position = positions[0]
            close_volume = volume if volume is not None else position.volume
            price = mt5.symbol_info_tick(position.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else \
                mt5.symbol_info_tick(position.symbol).ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": position_id,
                "symbol": position.symbol,
                "volume": close_volume,
                "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "price": price,
                "deviation": self._DEVIATION,
                "magic": self._MAGIC_NUMBER,
                "comment": "Закрытие позиции",
                "type_time": self._ORDER_TIME,
                "type_filling": self._ORDER_FILLING,
            }

            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                raise OrderError(
                    message=f"Ошибка закрытия позиции: {result.comment}",
                    order_id=position_id,
                    logger=self._logger
                )

            self._logger.info(f"Позиция #{position_id} закрыта по {price}")
            return True

        except Exception as e:
            if not isinstance(e, OrderError):
                raise OrderError(
                    message=f"Ошибка закрытия позиции: {str(e)}",
                    order_id=position_id,
                    logger=self._logger
                ) from e
            raise