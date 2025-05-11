import pandas as pd
import numpy as np
from typing import Optional, Dict
from .base import BaseStrategy
from config.constants import TradeAction
from utils.logger import TradingLogger


class SniperStrategy(BaseStrategy):
    def __init__(self, name: str, mt5_client, logger: TradingLogger, database=None,
                 sma_fast_period: int = 10,
                 sma_slow_period: int = 20,
                 rsi_period: int = 14,
                 stoch_k_period: int = 14,
                 stoch_d_period: int = 3,
                 atr_period: int = 14,
                 adx_period: int = 14,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_signal: int = 9,
                 stoch_slowing: int = 3):
        """
        Инициализация стратегии "Снайпер"

        :param name: Название стратегии
        :param mt5_client: Клиент для работы с MT5
        :param logger: Логгер
        :param database: База данных (опционально)
        """
        super().__init__(
            name=name,
            mt5_client=mt5_client,
            logger=logger,
            database=database,
            sma_fast_period=sma_fast_period,
            sma_slow_period=sma_slow_period,
            rsi_period=rsi_period,
            stoch_k_period=stoch_k_period,
            stoch_d_period=stoch_d_period,
            atr_period=atr_period,
            adx_period=adx_period,
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
            stoch_slowing=stoch_slowing
        )
        self.logger.debug("Инициализирована стратегия Снайпер")

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Расчет всех индикаторов для стратегии Снайпер"""
        try:
            # Скользящие средние
            data['sma_fast'] = data['close'].rolling(self.sma_fast_period).mean()
            data['sma_slow'] = data['close'].rolling(self.sma_slow_period).mean()

            # RSI
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
            rs = gain / loss
            data['rsi'] = 100 - (100 / (1 + rs))

            # Stochastic
            low_min = data['low'].rolling(self.stoch_k_period).min()
            high_max = data['high'].rolling(self.stoch_k_period).max()
            data['stoch_k'] = 100 * ((data['close'] - low_min) / (high_max - low_min))
            data['stoch_d'] = data['stoch_k'].rolling(self.stoch_d_period).mean()

            # ATR
            high_low = data['high'] - data['low']
            high_close = np.abs(data['high'] - data['close'].shift())
            low_close = np.abs(data['low'] - data['close'].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            data['atr'] = true_range.rolling(self.atr_period).mean()

            # ADX
            plus_dm = data['high'].diff()
            minus_dm = -data['low'].diff()
            plus_dm[(plus_dm <= 0) | (plus_dm < minus_dm)] = 0
            minus_dm[(minus_dm <= 0) | (minus_dm < plus_dm)] = 0

            tr = true_range
            plus_di = 100 * (plus_dm.ewm(alpha=1 / self.adx_period).mean() / tr.ewm(alpha=1 / self.adx_period).mean())
            minus_di = 100 * (minus_dm.ewm(alpha=1 / self.adx_period).mean() / tr.ewm(alpha=1 / self.adx_period).mean())
            data['adx'] = 100 * np.abs((plus_di - minus_di) / (plus_di + minus_di)).ewm(
                alpha=1 / self.adx_period).mean()

            # MACD
            exp1 = data['close'].ewm(span=self.macd_fast, adjust=False).mean()
            exp2 = data['close'].ewm(span=self.macd_slow, adjust=False).mean()
            data['macd'] = exp1 - exp2
            data['macd_signal'] = data['macd'].ewm(span=self.macd_signal, adjust=False).mean()
            data['macd_hist'] = data['macd'] - data['macd_signal']

            self.logger.debug(f"Индикаторы рассчитаны для {len(data)} баров")
            return data

        except Exception as e:
            self.logger.error(f"Ошибка расчета индикаторов: {str(e)}")
            return data

    def analyze(self, symbol: str, timeframe: int, data: pd.DataFrame) -> Optional[Dict]:
        """Анализ по стратегии и генерация сигналов"""
        if not self.enabled:
            self.logger.debug(f"Стратегия {self.name} отключена")
            return None

        if len(data) < self.get_required_history_size():
            self.logger.warning(f"Недостаточно данных для анализа ({len(data)} баров)")
            return None

        try:
            last = data.iloc[-1]
            prev = data.iloc[-2]

            trend_up = (last['sma_fast'] > last['sma_slow']) and (last['close'] > last['sma_slow'])
            trend_down = (last['sma_fast'] < last['sma_slow']) and (last['close'] < last['sma_slow'])

            strong_trend = last['adx'] > 25
            high_volume = last['real_volume'] > last['volume_ma']

            # Условия покупки
            buy_signal = (
                    trend_up and
                    strong_trend and
                    high_volume and
                    last['stoch_k'] > last['stoch_d'] and prev['stoch_k'] < prev['stoch_d'] and
                    last['macd_hist'] > 0 and last['macd_hist'] > prev['macd_hist']
            )

            # Условия продажи
            sell_signal = (
                    trend_down and
                    strong_trend and
                    high_volume and
                    last['stoch_k'] < last['stoch_d'] and prev['stoch_k'] > prev['stoch_d'] and
                    last['macd_hist'] < 0 and last['macd_hist'] < prev['macd_hist']
            )

            if buy_signal:
                stop_loss = last['low'] - 2 * last['atr']
                take_profit = last['close'] + 3 * last['atr']
                self.logger.info(f"Обнаружен сигнал на покупку по {symbol}")
                return {
                    'action': TradeAction.BUY,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'price': last['close'],
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'comment': f"Стратегия: {self.name}"
                }

            if sell_signal:
                stop_loss = last['high'] + 2 * last['atr']
                take_profit = last['close'] - 3 * last['atr']
                self.logger.info(f"Обнаружен сигнал на продажу по {symbol}")
                return {
                    'action': TradeAction.SELL,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'price': last['close'],
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'comment': f"Стратегия: {self.name}"
                }

            self.logger.debug(f"Нет сигнала по {symbol}_{timeframe}")
            return None

        except Exception as e:
            self.logger.error(f"Ошибка анализа рынка по {symbol}: {str(e)}")
            return None

    def get_required_history_size(self) -> int:
        """Возвращает необходимое количество баров для анализа"""
        return max(
            self.sma_slow_period,
            self.rsi_period,
            self.stoch_k_period + self.stoch_d_period + self.stoch_slowing,
            self.atr_period,
            self.adx_period * 2,
            self.macd_slow + self.macd_signal
        ) + 50  # Добавляем запас для надежности