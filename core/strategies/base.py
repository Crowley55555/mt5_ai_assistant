from abc import ABC, abstractmethod
from typing import Optional, Dict, List
import pandas as pd
from utils.logger import TradingLogger
from config.constants import Timeframes, TradeAction
from core.database import MarketDatabase


class BaseStrategy(ABC):
    def __init__(self, name: str, mt5_client, logger: TradingLogger, database: Optional[MarketDatabase] = None):
        """
        Базовый класс для всех торговых стратегий

        :param name: Название стратегии
        :param mt5_client: Клиент для работы с MT5
        :param logger: Объект логгера
        :param database: Опционально, объект базы данных для кэширования индикаторов
        """
        if not mt5_client:
            raise ValueError("MT5 клиент должен быть инициализирован")

        self.name = name
        self.mt5_client = mt5_client
        self.logger = logger.logger  # Получаем корневой логгер
        self.database = database
        self.enabled = False
        self.symbols = []  # Список символов для торговли
        self.timeframes = []  # Список таймфреймов для анализа

    def save_indicator(self, symbol: str, timeframe: int, timestamp: pd.Timestamp, name: str, value: float):
        """Сохранение значения индикатора в кэше"""
        if not self.database:
            return

        try:
            # Преобразуем Timestamp в Unix время
            unix_time = int(timestamp.timestamp())
            self.database.cache_indicator(symbol, timeframe, unix_time, name, value)
        except Exception as e:
            self.logger.warning(f"Ошибка сохранения индикатора {name}: {str(e)}")

    def get_cached_indicator(self, symbol: str, timeframe: int, timestamp: pd.Timestamp, name: str) -> Optional[float]:
        """Получение кэшированного индикатора"""
        if not self.database:
            return None

        try:
            # Преобразуем Timestamp в Unix время
            unix_time = int(timestamp.timestamp())
            result = self.database.get_cached_indicator(symbol, timeframe, unix_time, name)
            if result is not None:
                self.logger.debug(f"Индикатор {name} найден в кэше")
            return result
        except Exception as e:
            self.logger.warning(f"Ошибка получения индикатора {name}: {str(e)}")
            return None

    @abstractmethod
    def analyze(self, symbol: str, timeframe: int, data: pd.DataFrame) -> Optional[Dict]:
        """
        Анализ рыночных данных и генерация торговых сигналов

        :param symbol: Символ (например, 'EURUSD')
        :param timeframe: Таймфрейм (в минутах)
        :param data: DataFrame с OHLCV данными
        :return: Словарь с сигналом или None
        """
        pass

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Расчет технических индикаторов

        :param data: Исходные данные
        :return: DataFrame с добавленными индикаторами
        """
        pass

    def enable(self):
        """Активация стратегии"""
        if not self.mt5_client.connected:
            self.logger.warning("Попытка активировать стратегию без подключения к MT5")
            return

        self.enabled = True
        self.logger.info(f"Стратегия {self.name} активирована")

    def disable(self):
        """Деактивация стратегии"""
        self.enabled = False
        self.logger.info(f"Стратегия {self.name} деактивирована")

    def set_symbols(self, symbols: List[str]):
        """Установка списка символов для торговли"""
        if not isinstance(symbols, list) or not all(isinstance(s, str) for s in symbols):
            raise ValueError("Символы должны быть списком строк")

        self.symbols = symbols
        self.logger.info(f"Для стратегии {self.name} установлены символы: {', '.join(symbols)}")

    def set_timeframes(self, timeframes: List[int]):
        """Установка таймфреймов для анализа"""
        if not isinstance(timeframes, list) or not all(isinstance(tf, int) and tf > 0 for tf in timeframes):
            raise ValueError("Таймфреймы должны быть списком положительных целых чисел")

        self.timeframes = timeframes
        self.logger.info(f"Для стратегии {self.name} установлены таймфреймы: {', '.join(str(tf) for tf in timeframes)}")

    def get_required_history_size(self) -> int:
        """Возвращает необходимое количество баров для анализа"""
        return 100  # По умолчанию 100 баров

    def load_market_data(self, symbol: str, timeframe: int, count: int) -> Optional[pd.DataFrame]:
        """Загрузка исторических данных"""
        if not self.mt5_client.connected:
            self.logger.warning("Попытка загрузить данные без подключения к MT5")
            return None

        try:
            # Сначала пробуем получить из кэша
            data = self.mt5_client.get_historical_data(symbol, timeframe, count)

            if data is None or len(data) < count * 0.8:  # Если данных недостаточно
                self.logger.warning(f"Недостаточно данных для анализа ({len(data) if data else 0} баров)")
                return None

            return data

        except Exception as e:
            self.logger.error(f"Ошибка загрузки исторических данных: {str(e)}")
            return None