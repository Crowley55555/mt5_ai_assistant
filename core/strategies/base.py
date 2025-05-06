from abc import ABC, abstractmethod
from typing import Optional, Dict, List
import pandas as pd
from utils.logger import TradingLogger
from config.constants import Timeframes, TradeAction
from typing import Optional
from core.database import MarketDatabase

class BaseStrategy(ABC):
    def __init__(self, name: str, mt5_client, logger, database: Optional[MarketDatabase] = None):
        self.database = database  # Добавляем ссылку на БД
        self.name = name
        self.mt5_client = mt5_client
        self.logger = logger
        self.enabled = False
        self.symbols = []
        self.timeframes = []

    def save_indicator(self, symbol: str, timeframe: int, timestamp, name: str, value: float):
        """Сохранение индикатора в кэш БД"""
        if self.database:
            self.database.cache_indicator(symbol, timeframe, timestamp, name, value)

    def get_cached_indicator(self, symbol: str, timeframe: int, timestamp, name: str):
        """Получение кэшированного индикатора"""
        return self.database.get_cached_indicator(symbol, timeframe, timestamp, name) if self.database else None

    @abstractmethod
    def analyze(self, symbol: str, timeframe: int, data: pd.DataFrame) -> Optional[Dict]:
        """Анализ рыночных данных и генерация торговых сигналов"""
        pass

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Расчет индикаторов для стратегии"""
        pass

    def enable(self):
        """Активация стратегии"""
        self.enabled = True
        self.logger.info(f"Стратегия {self.name} активирована")

    def disable(self):
        """Деактивация стратегии"""
        self.enabled = False
        self.logger.info(f"Стратегия {self.name} деактивирована")

    def set_symbols(self, symbols: List[str]):
        """Установка списка символов для торговли"""
        self.symbols = symbols
        self.logger.info(f"Для стратегии {self.name} установлены символы: {', '.join(symbols)}")

    def set_timeframes(self, timeframes: List[int]):
        """Установка таймфреймов для анализа"""
        self.timeframes = timeframes
        self.logger.info(f"Для стратегии {self.name} установлены таймфреймы: {', '.join(str(tf) for tf in timeframes)}")

    def get_required_history_size(self) -> int:
        """Возвращает необходимое количество баров для анализа"""
        return 100  # По умолчанию 100 баров