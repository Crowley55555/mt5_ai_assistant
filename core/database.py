import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Any, Union, TypedDict
import pandas as pd
from utils.logger import TradingLogger
from utils.exceptions import DatabaseError
from datetime import datetime

class TradeDict(TypedDict):
    id: int
    strategy: str
    symbol: str
    action: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    volume: float
    profit: float
    comment: str


class MarketDatabase:
    """Класс для работы с базой данных рыночной информации и сделок."""

    def __init__(self, connection_string: str, logger: TradingLogger):
        """
        Инициализация базы данных.

        Args:
            connection_string: Строка подключения (например, 'sqlite:///data.db')
            logger: Объект логгера TradingLogger

        Raises:
            DatabaseError: Если строка подключения невалидна
        """
        self.logger = logger
        self.connection_string = connection_string

        try:
            self._validate_connection_string()
            self._init_db()
            self.logger.info(f"Инициализирована база данных: {connection_string}")
        except Exception as e:
            self.logger.error(f"Ошибка инициализации БД: {str(e)}")
            raise DatabaseError(f"Ошибка инициализации БД: {str(e)}") from e

    def _validate_connection_string(self) -> None:
        """Проверка валидности строки подключения.

        Raises:
            ValueError: Если строка подключения не соответствует ожидаемому формату
        """
        if not isinstance(self.connection_string, str) or len(self.connection_string) < 7:
            raise ValueError("Неверная строка подключения")

        if not self.connection_string.startswith(('sqlite:///', 'postgresql://', 'mysql://')):
            raise ValueError("Поддерживается только SQLite, PostgreSQL и MySQL")

    def _get_connection(self) -> Union[sqlite3.Connection, Any]:
        """Создает и возвращает соединение с БД.

        Returns:
            Объект соединения с базой данных

        Raises:
            NotImplementedError: Для неподдерживаемых СУБД
            DatabaseError: При ошибках подключения
        """
        try:
            if self.connection_string.startswith('sqlite:///'):
                db_path = self.connection_string.replace('sqlite:///', '')
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                return sqlite3.connect(db_path)
            else:
                raise NotImplementedError("Поддержка Postgres/MySQL еще не реализована")
        except Exception as e:
            self.logger.error(f"Ошибка подключения к БД: {str(e)}")
            raise DatabaseError(f"Ошибка подключения: {str(e)}") from e

    def _init_db(self) -> None:
        """Инициализирует структуру базы данных (создает таблицы при первом запуске)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # SQL для создания таблиц
            tables_sql = [
                """
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
                """,
                """
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
                """,
                """
                CREATE TABLE IF NOT EXISTS indicators_cache (
                    symbol TEXT,
                    timeframe INTEGER,
                    timestamp INTEGER,
                    indicator_name TEXT,
                    value REAL,
                    PRIMARY KEY (symbol, timeframe, timestamp, indicator_name)
                )
                """
            ]

            for sql in tables_sql:
                cursor.execute(sql)

            conn.commit()
            self.logger.debug("Структура БД создана или проверена")

    def save_market_data(self, symbol: str, timeframe: int, data: pd.DataFrame) -> None:
        """
        Сохраняет рыночные данные в базу.

        Args:
            symbol: Тикер инструмента
            timeframe: Таймфрейм (в минутах)
            data: DataFrame с данными OHLCV

        Raises:
            DatabaseError: При ошибках сохранения
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
                cursor.executemany(
                    "INSERT OR REPLACE INTO market_data VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    records
                )
                conn.commit()
                self.logger.debug(f"Сохранено {len(records)} записей для {symbol}_{timeframe}")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения рыночных данных: {str(e)}")
            raise DatabaseError(f"Ошибка сохранения рыночных данных: {str(e)}") from e

    def get_market_data(self, symbol: str, timeframe: int, limit: int = 1000) -> Optional[pd.DataFrame]:
        """
        Получает исторические данные из базы.

        Args:
            symbol: Тикер инструмента
            timeframe: Таймфрейм (в минутах)
            limit: Ограничение на количество записей

        Returns:
            DataFrame с данными или None, если данных нет

        Raises:
            DatabaseError: При ошибках загрузки
        """
        try:
            query = """
                SELECT timestamp, open, high, low, close, volume 
                FROM market_data 
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """

            with self._get_connection() as conn:
                df = pd.read_sql(
                    query,
                    conn,
                    params=(symbol, timeframe, limit),
                    index_col='timestamp',
                    parse_dates=['timestamp']
                )

                if df.empty:
                    self.logger.debug(f"Нет данных для {symbol}_{timeframe}")
                    return None

                return df.sort_index()
        except Exception as e:
            self.logger.error(f"Ошибка загрузки рыночных данных: {str(e)}")
            raise DatabaseError(f"Ошибка загрузки рыночных данных: {str(e)}") from e

    def save_trade(self, trade_data: Dict[str, Any]) -> None:
        """
        Сохраняет информацию о сделке.

        Args:
            trade_data: Словарь с данными сделки:
                - strategy: Название стратегии
                - symbol: Тикер инструмента
                - action: Тип сделки ('buy'/'sell')
                - entry_time: Время входа (datetime)
                - exit_time: Время выхода (datetime, опционально)
                - entry_price: Цена входа
                - exit_price: Цена выхода (опционально)
                - volume: Объем
                - profit: Прибыль
                - comment: Комментарий (опционально)

        Raises:
            DatabaseError: При ошибках сохранения
            ValueError: Если отсутствуют обязательные поля
        """
        required_fields = {'strategy', 'symbol', 'action', 'entry_time', 'entry_price', 'volume', 'profit'}
        if not required_fields.issubset(trade_data.keys()):
            raise ValueError(f"Отсутствуют обязательные поля: {required_fields - trade_data.keys()}")

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
                    int(trade_data['exit_time'].timestamp()) if trade_data.get('exit_time') else None,
                    trade_data['entry_price'],
                    trade_data.get('exit_price'),
                    trade_data['volume'],
                    trade_data['profit'],
                    trade_data.get('comment', '')
                ))
                conn.commit()
                self.logger.info(f"Сохранена сделка по {trade_data['symbol']}")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения сделки: {str(e)}")
            raise DatabaseError(f"Ошибка сохранения сделки: {str(e)}") from e

    def get_trades(self, strategy: Optional[str] = None,
                   symbol: Optional[str] = None,
                   limit: int = 100) -> List[Dict[str, Union[str, float, datetime, None]]]:
        """
        Возвращает список сделок с фильтрацией.

        Args:
            strategy: Фильтр по стратегии
            symbol: Фильтр по символу
            limit: Ограничение выборки

        Returns:
            Список словарей с данными сделок, где значения могут быть:
            - str: для текстовых полей
            - float: для числовых значений
            - datetime: для временных меток
            - None: для необязательных полей

        Raises:
            DatabaseError: При ошибках загрузки
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

                result = []
                for row in cursor.fetchall():
                    trade = dict(row)
                    # Конвертируем timestamp обратно в datetime
                    trade['entry_time'] = datetime.fromtimestamp(trade['entry_time'])
                    if trade['exit_time'] is not None:
                        trade['exit_time'] = datetime.fromtimestamp(trade['exit_time'])
                    result.append(trade)

                self.logger.debug(f"Загружено {len(result)} сделок")
                return result
        except Exception as e:
            self.logger.error(f"Ошибка загрузки сделок: {str(e)}")
            raise DatabaseError(f"Ошибка загрузки сделок: {str(e)}") from e

    def cache_indicator(self, symbol: str, timeframe: int,
                        timestamp: pd.Timestamp, indicator_name: str, value: float) -> None:
        """
        Кэширует значение индикатора.

        Args:
            symbol: Символ инструмента
            timeframe: Таймфрейм
            timestamp: Временная метка
            indicator_name: Название индикатора
            value: Значение индикатора

        Raises:
            DatabaseError: При ошибках сохранения
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO indicators_cache 
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    symbol,
                    timeframe,
                    int(timestamp.timestamp()),
                    indicator_name,
                    value
                ))
                conn.commit()
                self.logger.debug(f"Кэширован индикатор {indicator_name} для {symbol}_{timeframe}")
        except Exception as e:
            self.logger.error(f"Ошибка кэширования индикатора: {str(e)}")
            raise DatabaseError(f"Ошибка кэширования индикатора: {str(e)}") from e

    def get_cached_indicator(self, symbol: str, timeframe: int,
                             timestamp: pd.Timestamp, indicator_name: str) -> Optional[float]:
        """
        Получает кэшированное значение индикатора.

        Args:
            symbol: Символ инструмента
            timeframe: Таймфрейм
            timestamp: Временная метка
            indicator_name: Название индикатора

        Returns:
            Значение индикатора или None, если не найдено

        Raises:
            DatabaseError: При ошибках загрузки
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT value FROM indicators_cache 
                    WHERE symbol = ? AND timeframe = ? 
                    AND timestamp = ? AND indicator_name = ?
                """, (
                    symbol,
                    timeframe,
                    int(timestamp.timestamp()),
                    indicator_name
                ))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Ошибка получения кэша индикатора: {str(e)}")
            raise DatabaseError(f"Ошибка получения кэша индикатора: {str(e)}") from e