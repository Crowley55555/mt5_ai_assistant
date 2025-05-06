import MetaTrader5 as mt5
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import pandas as pd
from utils.logger import TradingLogger
from config.constants import Timeframes, TradeAction, OrderType
from tkinter import messagebox
from .database import MarketDatabase

class MT5Client:
    def __init__(self, logger: TradingLogger, database: Optional[MarketDatabase] = None):
        self.database = database
        self.logger = logger
        self.connected = False

    def connect(self, login: int, password: str, server: str, path: str) -> bool:
        """Подключение к терминалу MT5"""
        try:
            account_data = {
                "login": self.login_entry.get(),
                "password": self.password_entry.get(),
                "server": self.server_entry.get(),
                "path": self.path_entry.get()
            }

            if not all(account_data.values()):
                self.logger.warning("Попытка подключения с неполными данными")
                messagebox.showerror("Ошибка", "Заполните все поля для подключения")
                return

            self.logger.info(f"Попытка подключения к MT5: {account_data['login']}")

            if self.mt5_client.connect(**account_data):
                self.settings.add_account(**account_data)  # Сохраняем в историю
                self._update_accounts_dropdown()
                messagebox.showinfo("Успех", "Подключение установлено")
                self.logger.info(f"Успешное подключение к MT5: {account_data['login']}")
            else:
                error_msg = mt5.last_error()
                self.logger.error(f"Ошибка подключения к MT5: {error_msg}")
                messagebox.showerror("Ошибка", f"Не удалось подключиться: {error_msg}")
        except Exception as e:
            self.logger.error(f"Критическая ошибка при подключении: {str(e)}")
            messagebox.showerror("Ошибка", f"Системная ошибка: {str(e)}")

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
            self.logger.error(f"Ошибка получения информации о счете: {mt5.last_error()}")
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

        symbols = mt5.symbols_get()
        return [s.name for s in symbols]

    def get_historical_data(self, symbol: str, timeframe: int, count: int) -> Optional[pd.DataFrame]:
        """Сначала пробуем получить данные из БД"""
        if self.database:
            cached_data = self.database.get_market_data(symbol, timeframe, count)
            if cached_data is not None and len(cached_data) >= count * 0.8:  # 80% данных достаточно
                self.logger.debug(f"Используем кэшированные данные для {symbol}_{timeframe}")
                return cached_data

        # Если в БД нет данных, получаем из MT5
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)

        if rates is not None and self.database:
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            self.database.save_market_data(symbol, timeframe, df.set_index('time'))

        return rates

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        return df

    def place_order(self, symbol: str, action: str, volume: float,
                    stop_loss: float = 0.0, take_profit: float = 0.0,
                    comment: str = "") -> Optional[int]:
        """Размещение ордера"""
        if not self.connected:
            self.logger.warning(f"Попытка разместить ордер на {symbol} без подключения к MT5")
            return None

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            self.logger.error(f"Ошибка получения информации о символе {symbol}: {mt5.last_error()}")
            return None

        point = symbol_info.point
        price = mt5.symbol_info_tick(symbol).ask if action == TradeAction.BUY else mt5.symbol_info_tick(symbol).bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if action == TradeAction.BUY else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 10,
            "magic": 123456,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            self.logger.error(f"Ошибка размещения ордера на {symbol}: {result.comment}")
            return None

        self.logger.info(f"Успешно размещен ордер #{result.order} на {symbol} {action} {volume} по цене {price}")
        return result.order

    def close_position(self, position_id: int, volume: float = None) -> bool:
        """Закрытие позиции"""
        if not self.connected:
            self.logger.warning(f"Попытка закрыть позицию #{position_id} без подключения к MT5")
            return False

        position = mt5.positions_get(ticket=position_id)
        if not position:
            self.logger.error(f"Позиция #{position_id} не найдена: {mt5.last_error()}")
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
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            self.logger.error(f"Ошибка закрытия позиции #{position_id}: {result.comment}")
            return False

        self.logger.info(f"Успешно закрыта позиция #{position_id} на {symbol} по цене {price}")
        return True