import pandas as pd
import numpy as np
from typing import Optional, Dict
from .base import BaseStrategy
from config.constants import TradeAction
from utils.logger import TradingLogger

class SmartMoneyStrategy(BaseStrategy):
    def __init__(self, name: str, mt5_client, logger: TradingLogger, database=None,
                 sma_period: int = 50,
                 ema_period: int = 20,
                 rsi_period: int = 14,
                 stoch_k_period: int = 14,
                 stoch_d_period: int = 3,
                 atr_period: int = 14,
                 adx_period: int = 14,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_signal: int = 9,
                 volume_ma_period: int = 20,
                 pinbar_threshold: float = 2.0,
                 engulfing_ratio: float = 1.5):
        super().__init__(
            name=name,
            mt5_client=mt5_client,
            logger=logger,
            database=database,
            sma_fast_period=sma_period,
            sma_slow_period=ema_period,
            rsi_period=rsi_period,
            stoch_k_period=stoch_k_period,
            stoch_d_period=stoch_d_period,
            atr_period=atr_period,
            adx_period=adx_period,
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
            stoch_slowing=3
        )
        self.sma_period = sma_period
        self.ema_period = ema_period
        self.volume_ma_period = volume_ma_period
        self.pinbar_threshold = pinbar_threshold
        self.engulfing_ratio = engulfing_ratio
        self.logger.debug("Инициализирована стратегия Smart Money")

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Расчет индикаторов для стратегии Смарт Мани"""
        try:
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
                     (data['lower_shadow'] / data['body_size'] > self.pinbar_threshold)) &
                    (data['body_size'] > 0)
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

            self.logger.debug(f"Индикаторы рассчитаны для {len(data)} баров")
            return data

        except Exception as e:
            self.logger.error(f"Ошибка расчета индикаторов: {str(e)}")
            return data

    def analyze(self, symbol: str, timeframe: int, data: pd.DataFrame) -> Optional[Dict]:
        """Анализ рыночной ситуации с учетом свечных паттернов и объемов"""

        if not self.enabled:
            self.logger.debug(f"Стратегия {self.name} отключена")
            return None

        if len(data) < self.get_required_history_size():
            self.logger.warning(f"Недостаточно данных для анализа ({len(data)} баров)")
            return None

        try:
            # Получаем последнюю цену
            last = data.iloc[-1]
            prev = data.iloc[-2]

            # Расчет ключевых уровней
            support = data['low'].rolling(20).min().iloc[-1]
            resistance = data['high'].rolling(20).max().iloc[-1]

            # Определение тренда
            trend_up = last['close'] > last['ema'] > last['sma']
            trend_down = last['close'] < last['ema'] < last['sma']

            # Анализ объема
            high_volume = last['volume_ratio'] > 1.5

            # Проверка нахождения у ключевого уровня
            near_support = abs(last['low'] - support) < 2 * last['atr']
            near_resistance = abs(last['high'] - resistance) < 2 * last['atr']

            # Анализ на покупку
            buy_signal = (
                    (trend_up or near_support) and
                    high_volume and
                    (
                            (last['is_pinbar'] and last['lower_shadow'] > last['upper_shadow']) or  # Бычий пин-бар
                            (last['is_engulfing'] and last['close'] > last['open']) or  # Бычье поглощение
                            (last['close'] > last['open'] and prev['close'] < prev['open'] and  # Проникновение
                             last['close'] > (prev['open'] + prev['close']) / 2)
                    ) and
                    30 < last['rsi'] < 70
            )

            # Анализ на продажу
            sell_signal = (
                    (trend_down or near_resistance) and
                    high_volume and
                    (
                            (last['is_pinbar'] and last['upper_shadow'] > last['lower_shadow']) or  # Медвежий пин-бар
                            (last['is_engulfing'] and last['close'] < last['open']) or  # Медвежье поглощение
                            (last['close'] < last['open'] and prev['close'] > prev['open'] and  # Проникновение
                             last['close'] < (prev['open'] + prev['close']) / 2)
                    ) and
                    30 < last['rsi'] < 70
            )

            # Формирование сигналов
            if buy_signal:
                stop_loss = min(last['low'], support) - 2 * last['atr']
                take_profit = last['close'] + 4 * last['atr']

                self.logger.info(f"Обнаружен сигнал на покупку по {symbol}")
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
                take_profit = last['close'] - 4 * last['atr']

                self.logger.info(f"Обнаружен сигнал на продажу по {symbol}")
                return {
                    'action': TradeAction.SELL,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'price': last['close'],
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'comment': f"Стратегия: {self.name}, Паттерн: {self._get_pattern_name(last)}"
                }

            self.logger.debug(f"Нет сигнала по {symbol}_{timeframe}")
            return None

        except Exception as e:
            self.logger.error(f"Ошибка анализа рынка по {symbol}: {str(e)}")
            return None

    @staticmethod
    def _get_pattern_name(candle: Dict) -> str:
        """Определение названия свечного паттерна"""
        if candle['is_pinbar']:
            return "Бычий пин-бар" if candle['lower_shadow'] > candle['upper_shadow'] else "Медвежий пин-бар"
        elif candle['is_engulfing']:
            return "Бычье поглощение" if candle['close'] > candle['open'] else "Медвежье поглощение"
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
        ) + 50  # Добавляем запас для надежности