from abc import ABC, abstractmethod
from typing import Optional, Dict, List
import pandas as pd
from utils.logger import TradingLogger
from config.constants import TradeAction, Timeframes
from core.mt5_client import MT5Client
from core.database import MarketDatabase


class BaseStrategy(ABC):
    def __init__(self, name: str, mt5_client: MT5Client, logger: TradingLogger,
                 database: Optional[MarketDatabase] = None,
                 sma_fast_period: int = 20,
                 sma_slow_period: int = 50,
                 rsi_period: int = 14,
                 stoch_k_period: int = 14,
                 stoch_d_period: int = 3,
                 atr_period: int = 14,
                 adx_period: int = 14,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_signal: int = 9,
                 stoch_slowing: int = 3,
                 pinbar_threshold: float = 2.0,
                 engulfing_ratio: float = 1.5,
                 volume_ma_period: int = 20):
        """
        Базовый класс для всех торговых стратегий

        :param name: Название стратегии
        :param mt5_client: Клиент для работы с MT5
        :param logger: Ваш кастомный логгер
        :param database: База данных (опционально)

        :param sma_fast_period: Период быстрого SMA
        :param sma_slow_period: Период медленного SMA
        :param rsi_period: Период RSI
        :param stoch_k_period: Период Stochastic K
        :param stoch_d_period: Период Stochastic D
        :param atr_period: Период ATR
        :param adx_period: Период ADX
        :param macd_fast: Быстрая EMA для MACD
        :param macd_slow: Медленная EMA для MACD
        :param macd_signal: Signal для MACD
        :param stoch_slowing: Сглаживание Stochastic
        :param pinbar_threshold: Порог для пин-бара
        :param engulfing_ratio: Порог для поглощения
        :param volume_ma_period: Период скользящего объема
        """
        if not mt5_client:
            raise ValueError("MT5 клиент должен быть инициализирован")

        self.name = name
        self.mt5_client = mt5_client
        self.logger = logger.logger  # Получаем корневой логгер из TradingLogger
        self.database = database
        self.enabled = False

        # Периоды индикаторов
        self.sma_fast_period = sma_fast_period
        self.sma_slow_period = sma_slow_period
        self.rsi_period = rsi_period
        self.stoch_k_period = stoch_k_period
        self.stoch_d_period = stoch_d_period
        self.stoch_slowing = stoch_slowing
        self.atr_period = atr_period
        self.adx_period = adx_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.pinbar_threshold = pinbar_threshold
        self.engulfing_ratio = engulfing_ratio
        self.volume_ma_period = volume_ma_period

        # Списки символов и таймфреймов
        self.symbols = []  # type: List[str]
        self.timeframes = []  # type: List[int]

        # Валидация периодов
        if not all([
            sma_fast_period > 0,
            sma_slow_period > 0,
            rsi_period > 0,
            stoch_k_period > 0,
            stoch_d_period > 0,
            atr_period > 0,
            adx_period > 0,
            macd_fast > 0,
            macd_slow > 0,
            macd_signal > 0,
            volume_ma_period > 0
        ]):
            raise ValueError("Все периоды индикаторов должны быть положительными числами")

        self._log_init_params(logger)

    def _log_init_params(self, logger: TradingLogger):
        """Логирование начальных параметров"""
        logger.debug(f"Инициализирована {self.__class__.__name__} с параметрами:")
        logger.debug(f"SMA Fast: {self.sma_fast_period}, SMA Slow: {self.sma_slow_period}")
        logger.debug(f"RSI Period: {self.rsi_period}, Stochastic: {self.stoch_k_period}/{self.stoch_d_period}")
        logger.debug(f"ATR Period: {self.atr_period}, ADX Period: {self.adx_period}")
        logger.debug(f"MACD: {self.macd_fast}/{self.macd_slow}/{self.macd_signal}")

    def save_indicator(self, symbol: str, timeframe: int, timestamp: pd.Timestamp, name: str, value: float):
        """Сохранение значения индикатора в кэше"""
        if not self.database:
            return

        try:
            unix_time = int(timestamp.timestamp())
            self.database.cache_indicator(symbol, timeframe, unix_time, name, value)
        except Exception as e:
            self.logger.warning(f"Ошибка сохранения индикатора {name}: {str(e)}")

    def get_cached_indicator(self, symbol: str, timeframe: int, timestamp: pd.Timestamp, name: str) -> Optional[float]:
        """Получение кэшированного значения индикатора"""
        if not self.database:
            return None

        try:
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
        Анализ рыночных данных и генерация сигналов

        :param symbol: Символ (EURUSD, GBPUSD и т.д.)
        :param timeframe: Таймфрейм (в минутах)
        :param data: OHLCV DataFrame
        :return: Словарь с сигналом или None
        """
        pass

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Расчет технических индикаторов

        :param data: OHLCV данные
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
        """Установка списка торгуемых символов"""
        if not isinstance(symbols, list) or not all(isinstance(s, str) for s in symbols):
            raise ValueError("Символы должны быть списком строк")

        self.symbols = symbols
        self.logger.info(f"Для {self.name} установлены символы: {', '.join(symbols)}")

    def set_timeframes(self, timeframes: List[int]):
        """Установка списка таймфреймов"""
        if not isinstance(timeframes, list) or not all(isinstance(tf, int) and tf > 0 for tf in timeframes):
            raise ValueError("Таймфреймы должны быть списком положительных целых чисел")

        self.timeframes = timeframes
        self.logger.info(f"Для {self.name} установлены таймфреймы: {', '.join(str(tf) for tf in timeframes)}")

    def get_required_history_size(self) -> int:
        """Минимальное количество баров для анализа"""
        return max(
            self.sma_fast_period,
            self.sma_slow_period,
            self.rsi_period,
            self.stoch_k_period + self.stoch_d_period + self.stoch_slowing,
            self.atr_period,
            self.adx_period * 2,
            self.macd_slow + self.macd_signal
        ) + 50  # Запас на всякий случай

    def load_market_data(self, symbol: str, timeframe: int, count: int) -> Optional[pd.DataFrame]:
        """Загрузка исторических данных"""
        if not self.mt5_client.connected:
            self.logger.warning("Попытка загрузить данные без подключения к MT5")
            return None

        try:
            data = self.mt5_client.get_historical_data(symbol, timeframe, count)
            if data is None or len(data) < count * 0.8:
                self.logger.warning(f"Недостаточно данных ({len(data) if data else 0} баров)")
                return None
            return data
        except Exception as e:
            self.logger.error(f"Ошибка загрузки данных: {str(e)}")
            return None