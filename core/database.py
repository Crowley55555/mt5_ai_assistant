"""
Модуль для работы с базой данных торгового ассистента

Поддерживает:
- Хранение исторических данных
- Сохранение сделок
- Кэширование индикаторов
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List
import pandas as pd
from utils.logger import TradingLogger


class MarketDatabase:
    def __init__(self, connection_string: str, logger: TradingLogger):
        """
        :param connection_string: Строка подключения (например, 'sqlite:///data.db')
        :param logger: Логгер приложения
        """
        self.logger = logger
        self.connection_string = connection_string

        if connection_string.startswith('sqlite:///'):
            db_path = connection_string.replace('sqlite:///', '')
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_db()
        self.logger.info(f"Инициализирована база данных: {connection_string}")

    def _init_db(self):
        """Создает таблицы при первом запуске"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Таблица исторических данных
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    symbol TEXT,
                    timeframe INTEGER,
                    timestamp INTEGER,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    PRIMARY KEY (symbol, timeframe, timestamp)
                )
            """)

            # Таблица сделок
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy TEXT,
                    symbol TEXT,
                    action TEXT,
                    entry_time INTEGER,
                    exit_time INTEGER,
                    entry_price REAL,
                    exit_price REAL,
                    volume REAL,
                    profit REAL,
                    comment TEXT
                )
            """)

            # Таблица кэша индикаторов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS indicators_cache (
                    symbol TEXT,
                    timeframe INTEGER,
                    timestamp INTEGER,
                    indicator_name TEXT,
                    value REAL,
                    PRIMARY KEY (symbol, timeframe, timestamp, indicator_name)
                )
            """)

            conn.commit()

    def _get_connection(self):
        """Возвращает соединение с базой данных"""
        if self.connection_string.startswith('sqlite:///'):
            db_path = self.connection_string.replace('sqlite:///', '')
            return sqlite3.connect(db_path)
        raise ValueError("Неподдерживаемый тип базы данных")

    def save_market_data(self, symbol: str, timeframe: int, data: pd.DataFrame):
        """
        Сохраняет рыночные данные в базу
        :param symbol: Тикер инструмента
        :param timeframe: Таймфрейм (в минутах)
        :param data: DataFrame с колонками ['open', 'high', 'low', 'close', 'volume']
        """
        try:
            records = []
            for ts, row in data.iterrows():
                records.append((
                    symbol,
                    timeframe,
                    int(ts.timestamp()),
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row.get('volume', 0)
                ))

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany("""
                    INSERT OR REPLACE INTO market_data 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, records)
                conn.commit()

            self.logger.debug(f"Сохранено {len(records)} записей для {symbol}_{timeframe}")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения рыночных данных: {str(e)}")

    def get_market_data(self, symbol: str, timeframe: int, limit: int = 1000) -> Optional[pd.DataFrame]:
        """
        Получает исторические данные из базы
        :return: DataFrame с индексом datetime и колонками OHLCV
        """
        try:
            with self._get_connection() as conn:
                query = """
                    SELECT timestamp, open, high, low, close, volume 
                    FROM market_data 
                    WHERE symbol = ? AND timeframe = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """
                df = pd.read_sql(query, conn,
                                 params=(symbol, timeframe, limit),
                                 index_col='timestamp',
                                 parse_dates=['timestamp'])
                return df.sort_index()
        except Exception as e:
            self.logger.error(f"Ошибка загрузки данных: {str(e)}")
            return None

    def save_trade(self, trade_data: Dict):
        """
        Сохраняет сделку в базу
        :param trade_data: {
            'strategy': str,
            'symbol': str,
            'action': 'buy'/'sell',
            'entry_time': datetime,
            'exit_time': datetime,
            'entry_price': float,
            'exit_price': float,
            'volume': float,
            'profit': float,
            'comment': str
        }
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO trades 
                    VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_data['strategy'],
                    trade_data['symbol'],
                    trade_data['action'],
                    int(trade_data['entry_time'].timestamp()),
                    int(trade_data['exit_time'].timestamp()) if trade_data['exit_time'] else None,
                    trade_data['entry_price'],
                    trade_data['exit_price'],
                    trade_data['volume'],
                    trade_data['profit'],
                    trade_data['comment']
                ))
                conn.commit()
                self.logger.info(f"Сохранена сделка по {trade_data['symbol']}")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения сделки: {str(e)}")

    def get_trades(self, strategy: str = None, symbol: str = None, limit: int = 100) -> List[Dict]:
        """
        Возвращает список сделок с фильтрацией
        :return: Список словарей с данными сделок
        """
        try:
            query = "SELECT * FROM trades WHERE 1=1"
            params = []

            if strategy:
                query += " AND strategy = ?"
                params.append(strategy)

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)

            query += " ORDER BY entry_time DESC LIMIT ?"
            params.append(limit)

            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Ошибка загрузки сделок: {str(e)}")
            return []

    def cache_indicator(self, symbol: str, timeframe: int, timestamp: pd.Timestamp,
                        indicator_name: str, value: float):
        """Кэширует значение индикатора"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO indicators_cache 
                    VALUES (?, ?, ?, ?, ?)
                """, (symbol, timeframe, int(timestamp.timestamp()), indicator_name, value))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Ошибка кэширования индикатора: {str(e)}")

    def get_cached_indicator(self, symbol: str, timeframe: int,
                             timestamp: pd.Timestamp, indicator_name: str) -> Optional[float]:
        """Получает кэшированное значение индикатора"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT value FROM indicators_cache 
                    WHERE symbol = ? AND timeframe = ? 
                    AND timestamp = ? AND indicator_name = ?
                """, (symbol, timeframe, int(timestamp.timestamp()), indicator_name))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Ошибка получения кэша индикатора: {str(e)}")
            return None