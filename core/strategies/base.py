from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, List
import pandas as pd
from utils.logger import TradingLogger
from config.constants import Timeframe
from core.mt5_client import MT5Client
from core.database import MarketDatabase
from utils.exceptions import StrategyError


@dataclass
class IndicatorParams:
    """Параметры индикаторов стратегии"""
    sma_fast_period: int = 20
    sma_slow_period: int = 50
    rsi_period: int = 14
    stoch_k_period: int = 14
    stoch_d_period: int = 3
    atr_period: int = 14
    adx_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    stoch_slowing: int = 3
    pinbar_threshold: float = 2.0
    engulfing_ratio: float = 1.5
    volume_ma_period: int = 20


class BaseStrategy(ABC):
    """Абстрактный базовый класс для всех торговых стратегий"""

    def __init__(
        self,
        name: str,
        mt5_client: MT5Client,
        logger: TradingLogger,
        database: Optional[MarketDatabase] = None,
        indicator_params: Optional[IndicatorParams] = None
    ):
        """
        Инициализация базовой стратегии

        Args:
            name: Название стратегии
            mt5_client: Клиент MT5 (должен быть инициализирован)
            logger: Логгер для записи событий
            database: База данных для кэширования (опционально)
            indicator_params: Параметры индикаторов (если None - будут значения по умолчанию)
        """
        if not mt5_client.is_connected:
            raise StrategyError(f"MT5 клиент не подключен для стратегии {name}")

        self.name = name
        self.mt5_client = mt5_client
        self.logger = logger.getChild(f"strategy.{name}")
        self.database = database
        self.enabled = False
        self.symbols: List[str] = []
        self.timeframes: List[Timeframe] = []

        # Параметры индикаторов
        self.params = indicator_params if indicator_params else IndicatorParams()
        self._validate_indicator_params()

        self._log_initialization()

    def _validate_indicator_params(self) -> None:
        """Валидация параметров индикаторов"""
        params = [
            self.params.sma_fast_period,
            self.params.sma_slow_period,
            self.params.rsi_period,
            self.params.stoch_k_period,
            self.params.stoch_d_period,
            self.params.atr_period,
            self.params.adx_period,
            self.params.macd_fast,
            self.params.macd_slow,
            self.params.macd_signal,
            self.params.volume_ma_period
        ]

        if not all(p > 0 for p in params):
            raise ValueError("Все периоды индикаторов должны быть положительными числами")

    def _log_initialization(self) -> None:
        """Логирование параметров инициализации"""
        self.logger.debug(
            f"Инициализирована стратегия {self.name} с параметрами:\n"
            f"SMA: {self.params.sma_fast_period}/{self.params.sma_slow_period}\n"
            f"RSI: {self.params.rsi_period}, Stochastic: {self.params.stoch_k_period}/{self.params.stoch_d_period}\n"
            f"ATR: {self.params.atr_period}, ADX: {self.params.adx_period}\n"
            f"MACD: {self.params.macd_fast}/{self.params.macd_slow}/{self.params.macd_signal}"
        )

    def cache_indicator(
        self,
        symbol: str,
        timeframe: Timeframe,
        timestamp: pd.Timestamp,
        name: str,
        value: float
    ) -> None:
        """Кэширование значения индикатора"""
        if self.database:
            try:
                self.database.cache_indicator(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=int(timestamp.timestamp()),
                    indicator_name=name,
                    value=value
                )
            except Exception as e:
                self.logger.warning(f"Ошибка кэширования индикатора {name}: {str(e)}")

    def get_cached_indicator(
        self,
        symbol: str,
        timeframe: Timeframe,
        timestamp: pd.Timestamp,
        name: str
    ) -> Optional[float]:
        """Получение кэшированного значения индикатора"""
        if not self.database:
            return None

        try:
            value = self.database.get_cached_indicator(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=int(timestamp.timestamp()),
                indicator_name=name
            )
            if value is not None:
                self.logger.debug(f"Индикатор {name} загружен из кэша")
            return value
        except Exception as e:
            self.logger.warning(f"Ошибка получения индикатора {name}: {str(e)}")
            return None

    @abstractmethod
    def analyze(self, symbol: str, timeframe: Timeframe, data: pd.DataFrame) -> Optional[Dict]:
        """
        Анализ рыночных данных и генерация сигналов

        Args:
            symbol: Торговый символ (например, "EURUSD")
            timeframe: Таймфрейм из констант Timeframe
            data: DataFrame с OHLCV данными

        Returns:
            Словарь с сигналом или None если сигнала нет
        """
        pass

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Расчет технических индикаторов

        Args:
            data: DataFrame с OHLCV данными

        Returns:
            DataFrame с добавленными колонками индикаторов
        """
        pass

    def enable(self) -> None:
        """Активация стратегии"""
        if not self.mt5_client.is_connected:
            self.logger.warning("Не удалось активировать стратегию - нет подключения к MT5")
            return

        self.enabled = True
        self.logger.info(f"Стратегия {self.name} активирована")

    def disable(self) -> None:
        """Деактивация стратегии"""
        self.enabled = False
        self.logger.info(f"Стратегия {self.name} деактивирована")

    def set_symbols(self, symbols: List[str]) -> None:
        """Установка списка торгуемых символов"""
        if not isinstance(symbols, list) or not all(isinstance(s, str) for s in symbols):
            raise ValueError("Символы должны быть списком строк")

        self.symbols = symbols
        self.logger.info(f"Установлены символы: {', '.join(symbols)}")

    def set_timeframes(self, timeframes: List[Timeframe]) -> None:
        """Установка списка таймфреймов"""
        if not isinstance(timeframes, list) or not all(isinstance(tf, Timeframe) for tf in timeframes):
            raise ValueError("Таймфреймы должны быть списком значений Timeframe")

        self.timeframes = timeframes
        self.logger.info(f"Установлены таймфреймы: {', '.join(str(tf) for tf in timeframes)}")

    def get_required_history_size(self) -> int:
        """
        Расчет минимального количества баров для анализа

        Returns:
            Количество баров с запасом для расчета всех индикаторов
        """
        max_period = max(
            self.params.sma_fast_period,
            self.params.sma_slow_period,
            self.params.rsi_period,
            self.params.stoch_k_period + self.params.stoch_d_period + self.params.stoch_slowing,
            self.params.atr_period,
            self.params.adx_period * 2,
            self.params.macd_slow + self.params.macd_signal
        )
        return max_period + 50  # Запас на всякий случай

    def load_market_data(self, symbol: str, timeframe: Timeframe, count: int) -> Optional[pd.DataFrame]:
        """
        Загрузка исторических данных

        Args:
            symbol: Торговый символ
            timeframe: Таймфрейм
            count: Требуемое количество баров

        Returns:
            DataFrame с данными или None при ошибке
        """
        try:
            data = self.mt5_client.get_historical_data(symbol, timeframe, count)
            if data is None or len(data) < count * 0.8:
                self.logger.warning(f"Недостаточно данных ({len(data) if data else 0} из {count} баров)")
                return None
            return data
        except Exception as e:
            self.logger.error(f"Ошибка загрузки данных: {str(e)}")
            return None