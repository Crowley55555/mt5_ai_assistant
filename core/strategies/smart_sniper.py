import pandas as pd
import numpy as np
from typing import Optional, Dict
from .base import BaseStrategy
from utils.logger import TradingLogger
from config.constants import Timeframes, TradeAction


class SmartSniperStrategy(BaseStrategy):
    def __init__(self, mt5_client, logger: TradingLogger):
        super().__init__("Смарт Снайпер", mt5_client, logger)
        # Параметры индикаторов
        self.vwap_period = 20
        self.sma_fast_period = 5
        self.sma_slow_period = 20
        self.rsi_period = 14
        self.atr_period = 14
        self.stoch_k_period = 5
        self.stoch_d_period = 3
        self.stoch_slowing = 3
        self.adx_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Расчет всех индикаторов для стратегии Смарт Снайпер"""
        # VWAP (Volume Weighted Average Price)
        data['typical_price'] = (data['high'] + data['low'] + data['close']) / 3
        data['cumulative_volume'] = data['real_volume'].cumsum()
        data['cumulative_typical'] = (data['typical_price'] * data['real_volume']).cumsum()
        data['vwap'] = data['cumulative_typical'] / data['cumulative_volume']

        # Скользящие средние
        data['sma_fast'] = data['close'].rolling(self.sma_fast_period).mean()
        data['sma_slow'] = data['close'].rolling(self.sma_slow_period).mean()

        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))

        # ATR
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = true_range.rolling(self.atr_period).mean()

        # Stochastic
        low_min = data['low'].rolling(self.stoch_k_period).min()
        high_max = data['high'].rolling(self.stoch_k_period).max()
        data['stoch_k'] = 100 * ((data['close'] - low_min) / (high_max - low_min))
        data['stoch_d'] = data['stoch_k'].rolling(self.stoch_d_period).mean()

        # ADX
        plus_dm = data['high'].diff()
        minus_dm = -data['low'].diff()
        plus_dm[(plus_dm <= 0) | (plus_dm < minus_dm)] = 0
        minus_dm[(minus_dm <= 0) | (minus_dm < plus_dm)] = 0

        tr = true_range
        plus_di = 100 * (plus_dm.ewm(alpha=1 / self.adx_period).mean() / tr.ewm(alpha=1 / self.adx_period).mean())
        minus_di = 100 * (minus_dm.ewm(alpha=1 / self.adx_period).mean() / tr.ewm(alpha=1 / self.adx_period).mean())
        data['adx'] = 100 * np.abs((plus_di - minus_di) / (plus_di + minus_di)).ewm(alpha=1 / self.adx_period).mean()

        # MACD
        exp1 = data['close'].ewm(span=self.macd_fast, adjust=False).mean()
        exp2 = data['close'].ewm(span=self.macd_slow, adjust=False).mean()
        data['macd'] = exp1 - exp2
        data['macd_signal'] = data['macd'].ewm(span=self.macd_signal, adjust=False).mean()
        data['macd_hist'] = data['macd'] - data['macd_signal']

        # Volume Analysis
        data['volume_ma'] = data['real_volume'].rolling(20).mean()
        data['volume_ratio'] = data['real_volume'] / data['volume_ma']

        return data

    def analyze(self, symbol: str, timeframe: int, data: pd.DataFrame) -> Optional[Dict]:
        """Анализ рыночной ситуации и генерация торговых сигналов"""
        if not self.enabled:
            return None

        if len(data) < 100:  # Нужно больше данных для VWAP
            self.logger.warning(f"Недостаточно данных для анализа ({len(data)} баров)")
            return None

        data = self.calculate_indicators(data)
        last = data.iloc[-1]
        prev = data.iloc[-2]

        # Определение тренда
        price_above_vwap = last['close'] > last['vwap']
        price_below_vwap = last['close'] < last['vwap']

        trend_up = (last['sma_fast'] > last['sma_slow']) and price_above_vwap
        trend_down = (last['sma_fast'] < last['sma_slow']) and price_below_vwap

        # Проверка силы тренда
        strong_trend = last['adx'] > 25

        # Анализ объема
        high_volume = last['volume_ratio'] > 1.5

        # Анализ на покупку
        buy_signal = (
                trend_up and
                strong_trend and
                high_volume and
                last['rsi'] > 50 and last['rsi'] < 70 and
                last['stoch_k'] > last['stoch_d'] and prev['stoch_k'] < prev['stoch_d'] and
                last['macd_hist'] > 0 and last['macd_hist'] > prev['macd_hist']
        )

        # Анализ на продажу
        sell_signal = (
                trend_down and
                strong_trend and
                high_volume and
                last['rsi'] < 50 and last['rsi'] > 30 and
                last['stoch_k'] < last['stoch_d'] and prev['stoch_k'] > prev['stoch_d'] and
                last['macd_hist'] < 0 and last['macd_hist'] < prev['macd_hist']
        )

        # Формирование сигналов
        if buy_signal:
            stop_loss = min(last['low'], last['vwap']) - 2 * last['atr']
            take_profit = last['close'] + 3 * last['atr']
            return {
                'action': TradeAction.BUY,
                'symbol': symbol,
                'timeframe': timeframe,
                'price': last['close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'comment': f"Стратегия: {self.name}, Таймфрейм: {timeframe}"
            }

        if sell_signal:
            stop_loss = max(last['high'], last['vwap']) + 2 * last['atr']
            take_profit = last['close'] - 3 * last['atr']
            return {
                'action': TradeAction.SELL,
                'symbol': symbol,
                'timeframe': timeframe,
                'price': last['close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'comment': f"Стратегия: {self.name}, Таймфрейм: {timeframe}"
            }

        return None

    def get_required_history_size(self) -> int:
        """Возвращает необходимое количество баров для анализа"""
        return max(
            self.vwap_period * 2,
            self.sma_slow_period,
            self.rsi_period,
            self.stoch_k_period + self.stoch_d_period + self.stoch_slowing,
            self.atr_period,
            self.adx_period * 2,
            self.macd_slow + self.macd_signal
        ) + 50