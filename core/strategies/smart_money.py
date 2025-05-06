import pandas as pd
import numpy as np
from typing import Optional, Dict
from .base import BaseStrategy
from utils.logger import TradingLogger
from config.constants import Timeframes, TradeAction


class SmartMoneyStrategy(BaseStrategy):
    def __init__(self, mt5_client, logger: TradingLogger):
        super().__init__("Смарт Мани", mt5_client, logger)
        # Параметры индикаторов
        self.sma_period = 20
        self.ema_period = 50
        self.rsi_period = 14
        self.atr_period = 14
        self.volume_ma_period = 20
        self.pinbar_threshold = 0.7  # Минимальное соотношение тени к телу для пин-бара
        self.engulfing_ratio = 1.5  # Минимальное соотношение тел для поглощения

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Расчет индикаторов для стратегии Смарт Мани"""
        # Скользящие средние
        data['sma'] = data['close'].rolling(self.sma_period).mean()
        data['ema'] = data['close'].ewm(span=self.ema_period, adjust=False).mean()

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

        # Анализ объема
        data['volume_ma'] = data['real_volume'].rolling(self.volume_ma_period).mean()
        data['volume_ratio'] = data['real_volume'] / data['volume_ma']

        # Определение свечных паттернов
        data['body_size'] = np.abs(data['close'] - data['open'])
        data['upper_shadow'] = data['high'] - data[['open', 'close']].max(axis=1)
        data['lower_shadow'] = data[['open', 'close']].min(axis=1) - data['low']
        data['total_shadow'] = data['upper_shadow'] + data['lower_shadow']

        # Пин-бар (длинная тень с маленьким телом)
        data['is_pinbar'] = (
                ((data['upper_shadow'] / data['body_size'] > self.pinbar_threshold) |
                 (data['lower_shadow'] / data['body_size'] > self.pinbar_threshold))
                & (data['body_size'] > 0)
        )

        # Поглощение (текущая свеча полностью перекрывает предыдущую)
        prev_body = data['body_size'].shift(1)
        data['is_engulfing'] = (
                (data['body_size'] > prev_body * self.engulfing_ratio) &
                (
                        ((data['close'] > data['open']) &
                         (data['close'] > data['open'].shift(1)) &
                         (data['open'] < data['close'].shift(1))) |  # Бычье поглощение
                        ((data['close'] < data['open']) &
                         (data['close'] < data['open'].shift(1)) &
                         (data['open'] > data['close'].shift(1)))  # Медвежье поглощение
                )
        )

        return data

    def analyze(self, symbol: str, timeframe: int, data: pd.DataFrame) -> Optional[Dict]:
        """Анализ рыночной ситуации с учетом свечных паттернов и объемов"""
        if not self.enabled:
            return None

        if len(data) < 50:
            self.logger.warning(f"Недостаточно данных для анализа ({len(data)} баров)")
            return None

        data = self.calculate_indicators(data)
        last = data.iloc[-1]
        prev = data.iloc[-2]

        # Определение ключевых уровней (упрощенная версия)
        support = data['low'].rolling(20).min().iloc[-1]
        resistance = data['high'].rolling(20).max().iloc[-1]

        # Определение тренда
        trend_up = last['close'] > last['ema'] and last['ema'] > last['sma']
        trend_down = last['close'] < last['ema'] and last['ema'] < last['sma']

        # Анализ объема
        high_volume = last['volume_ratio'] > 1.5

        # Проверка нахождения у ключевого уровня
        near_support = abs(last['low'] - support) < 2 * last['atr']
        near_resistance = abs(last['high'] - resistance) < 2 * last['atr']

        # Анализ на покупку (бычьи паттерны у уровня поддержки в восходящем тренде)
        buy_signal = (
                (trend_up or near_support) and
                high_volume and
                (
                        (last['is_pinbar'] and last['lower_shadow'] > last['upper_shadow']) or  # Бычий пин-бар
                        (last['is_engulfing'] and last['close'] > last['open']) or  # Бычье поглощение
                        (last['close'] > last['open'] and prev['close'] < prev['open'] and  # Проникновение
                         last['close'] > (prev['open'] + prev['close']) / 2)
                ) and
                last['rsi'] > 30 and last['rsi'] < 70
        )

        # Анализ на продажу (медвежьи паттерны у уровня сопротивления в нисходящем тренде)
        sell_signal = (
                (trend_down or near_resistance) and
                high_volume and
                (
                        (last['is_pinbar'] and last['upper_shadow'] > last['lower_shadow']) or  # Медвежий пин-бар
                        (last['is_engulfing'] and last['close'] < last['open']) or  # Медвежье поглощение
                        (last['close'] < last['open'] and prev['close'] > prev['open'] and  # Проникновение
                         last['close'] < (prev['open'] + prev['close']) / 2)
                ) and
                last['rsi'] > 30 and last['rsi'] < 70
        )

        # Формирование сигналов
        if buy_signal:
            stop_loss = min(last['low'], support) - 2 * last['atr']
            take_profit = last['close'] + 4 * last['atr']  # Более высокий TP для трендовых сделок
            return {
                'action': TradeAction.BUY,
                'symbol': symbol,
                'timeframe': timeframe,
                'price': last['close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'comment': f"Стратегия: {self.name}, Паттерн: {self._get_pattern_name(last)}"
            }

        if sell_signal:
            stop_loss = max(last['high'], resistance) + 2 * last['atr']
            take_profit = last['close'] - 4 * last['atr']  # Более высокий TP для трендовых сделок
            return {
                'action': TradeAction.SELL,
                'symbol': symbol,
                'timeframe': timeframe,
                'price': last['close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'comment': f"Стратегия: {self.name}, Паттерн: {self._get_pattern_name(last)}"
            }

        return None

    def _get_pattern_name(self, candle) -> str:
        """Определение названия свечного паттерна"""
        if candle['is_pinbar']:
            if candle['lower_shadow'] > candle['upper_shadow']:
                return "Бычий пин-бар"
            else:
                return "Медвежий пин-бар"
        elif candle['is_engulfing']:
            if candle['close'] > candle['open']:
                return "Бычье поглощение"
            else:
                return "Медвежье поглощение"
        elif candle['close'] > candle['open']:
            return "Бычья свеча"
        else:
            return "Медвежья свеча"

    def get_required_history_size(self) -> int:
        """Возвращает необходимое количество баров для анализа"""
        return max(
            self.sma_period,
            self.ema_period,
            self.rsi_period,
            self.atr_period,
            self.volume_ma_period,
            20  # Для уровней поддержки/сопротивления
        ) + 50