import MetaTrader5 as mt5
from typing import Optional, Dict, List
from datetime import datetime
import pandas as pd
from utils.logger import TradingLogger
from config.constants import TradeAction
from core.database import MarketDatabase
from pathlib import Path

class MT5Client:
    def __init__(self, logger: TradingLogger, database: Optional[MarketDatabase] = None):
        """
        Инициализация клиента MT5

        :param logger: Объект логгера
        :param database: Объект базы данных (опционально)
        """
        self.database = database
        self.logger = logger
        self.connected = False

    def connect(self, login: int, password: str, server: str, path: str) -> bool:
        """Подключение к терминалу MT5"""
        if not all([login, password, server, path]):
            self.logger.warning("Попытка подключения с неполными данными")
            return False

        try:
            # Проверяем, запущен ли терминал по указанному пути
            if not Path(path).exists():
                self.logger.error(f"Файл терминала не найден: {path}")
                return False

            # Подключаемся к аккаунту
            if not mt5.initialize(login=login, password=password, server=server, path=path):
                error_code = mt5.last_error()
                self.logger.error(f"Ошибка подключения к MT5: {error_code}")
                return False

            self.connected = True
            self.logger.info(f"Успешное подключение к MT5: {login}")
            return True

        except Exception as e:
            self.logger.error(f"Критическая ошибка при подключении: {str(e)}")
            return False

    def disconnect(self):
        """Отключение от терминала MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            self.logger.info("Отключение от MT5")

    def get_account_info(self) -> Optional[Dict]:
        """Получение информации о счете"""
        if not self.connected:
            self.logger.warning("Попытка получить информацию о счете без подключения к MT5")
            return None

        account_info = mt5.account_info()
        if account_info is None:
            error_code = mt5.last_error()
            self.logger.error(f"Ошибка получения информации о счете: {error_code}")
            return None

        return {
            'login': account_info.login,
            'balance': account_info.balance,
            'equity': account_info.equity,
            'margin': account_info.margin,
            'free_margin': account_info.margin_free,
            'leverage': account_info.leverage
        }

    def get_symbols(self) -> List[str]:
        """Получение списка доступных символов"""
        if not self.connected:
            self.logger.warning("Попытка получить список символов без подключения к MT5")
            return []

        try:
            symbols = mt5.symbols_get()
            return [s.name for s in symbols]
        except Exception as e:
            self.logger.error(f"Ошибка получения списка символов: {str(e)}")
            return []



    def get_historical_data(self, symbol: str, timeframe: int, count: int) -> Optional[pd.DataFrame]:
        """Получение исторических данных сначала из БД, затем с сервера"""
        if not self.connected:
            self.logger.warning("Попытка получить исторические данные без подключения к MT5")
            return None

        if not symbol or timeframe <= 0 or count <= 0:
            self.logger.warning(f"Некорректные параметры запроса данных: {symbol}, {timeframe}, {count}")
            return None

        try:
            # Сначала пробуем получить из БД
            if self.database:
                cached_data = self.database.get_market_data(symbol, timeframe, count)
                if cached_data is not None and len(cached_data) >= count * 0.8:
                    self.logger.debug(f"Использованы кэшированные данные для {symbol}_{timeframe}")
                    return cached_data

            # Если в БД нет данных, получаем из MT5
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)

            if rates is None or len(rates) == 0:
                error_code = mt5.last_error()
                self.logger.warning(f"Не удалось получить данные из MT5 для {symbol}: {error_code}")
                return None

            # Преобразуем данные в DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)

            # Сохраняем в БД если она доступна
            if self.database:
                self.database.save_market_data(symbol, timeframe, df)

            return df

        except Exception as e:
            self.logger.error(f"Ошибка получения исторических данных: {str(e)}")
            return None

    def place_order(self, symbol: str, action: str, volume: float,
                    stop_loss: float = 0.0, take_profit: float = 0.0,
                    comment: str = "") -> Optional[int]:
        """Размещение ордера"""
        if not self.connected:
            self.logger.warning(f"Попытка разместить ордер без подключения к MT5")
            return None

        if not symbol or volume <= 0:
            self.logger.warning(f"Некорректные параметры ордера: {symbol}, {volume}")
            return None

        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                self.logger.error(f"Не найден символ {symbol} в MT5")
                return None

            point = symbol_info.point
            price = mt5.symbol_info_tick(symbol).ask if action == TradeAction.BUY else mt5.symbol_info_tick(symbol).bid

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_BUY if action == TradeAction.BUY else mt5.ORDER_TYPE_SELL,
                "price": price,
                "sl": stop_loss if stop_loss > 0 else 0,
                "tp": take_profit if take_profit > 0 else 0,
                "deviation": 10,
                "magic": 123456,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)

            if result is None:
                error_code = mt5.last_error()
                self.logger.error(f"Не удалось отправить ордер: {error_code}")
                return None

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Ошибка размещения ордера на {symbol}: {result.comment}")
                return None

            self.logger.info(f"Успешно размещен ордер #{result.order} на {symbol} {action} {volume} по цене {price}")
            return result.order

        except Exception as e:
            self.logger.error(f"Ошибка размещения ордера: {str(e)}")
            return None

    def close_position(self, position_id: int, volume: float = None) -> bool:
        """Закрытие позиции"""
        if not self.connected:
            self.logger.warning(f"Попытка закрыть позицию без подключения к MT5")
            return False

        try:
            position = mt5.positions_get(ticket=position_id)
            if not position:
                self.logger.warning(f"Позиция #{position_id} не найдена")
                return False

            position = position[0]
            symbol = position.symbol
            volume = volume if volume is not None else position.volume
            price = mt5.symbol_info_tick(symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(
                symbol).ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": position_id,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "price": price,
                "deviation": 10,
                "magic": 123456,
                "comment": "Закрытие позиции",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)

            if result is None:
                error_code = mt5.last_error()
                self.logger.error(f"Не удалось закрыть позицию #{position_id}: {error_code}")
                return False

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Ошибка закрытия позиции #{position_id}: {result.comment}")
                return False

            self.logger.info(f"Успешно закрыта позиция #{position_id} на {symbol} по цене {price}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка закрытия позиции: {str(e)}")
            return False

    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Получение информации о символе"""
        if not self.connected:
            self.logger.warning(f"Попытка получить информацию о символе без подключения к MT5")
            return None

        try:
            info = mt5.symbol_info(symbol)
            if not info:
                self.logger.warning(f"Неизвестный символ: {symbol}")
                return None

            return {
                'name': info.name,
                'point': info.point,
                'spread': info.spread,
                'trade_allowed': info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL,
                'currency_base': info.currency_base,
                'currency_profit': info.currency_profit,
                'volume_min': info.volume_min,
                'volume_max': info.volume_max,
                'volume_step': info.volume_step,
                'trade_tick_value': info.trade_tick_value
            }
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о символе {symbol}: {str(e)}")
            return None