import time
from functools import wraps
from typing import Callable, Any, TypeVar, Optional, Type
from utils.logger import TradingLogger
from exceptions import TradingError

F = TypeVar('F', bound=Callable[..., Any])


def log_execution_time(logger: Optional[TradingLogger] = None) -> Callable[[F], F]:
    """
    Декоратор для логирования времени выполнения функции с использованием TradingLogger.

    Args:
        logger: Опциональный логгер. Если не указан, будет создан новый.

    Returns:
        Декорированную функцию с логированием времени выполнения.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time

            used_logger = logger or TradingLogger(name=func.__module__)
            used_logger.debug(
                f"Функция {func.__qualname__} выполнена за {elapsed:.4f} сек"
            )
            return result

        return wrapper

    return decorator


def handle_errors(
        *error_types: Type[Exception],
        logger: Optional[TradingLogger] = None,
        re_raise: bool = True
) -> Callable[[F], F]:
    """
    Декоратор для обработки и логирования ошибок с возможностью настройки.

    Args:
        *error_types: Типы ошибок для перехвата. Если не указаны, перехватываются все.
        logger: Опциональный логгер. Если не указан, будет создан новый.
        re_raise: Флаг, указывающий нужно ли пробрасывать ошибку после логирования.

    Returns:
        Декорированную функцию с обработкой ошибок.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except error_types if error_types else Exception as e:
                used_logger = logger or TradingLogger(name=func.__module__)
                error_msg = f"Ошибка в функции {func.__qualname__}: {str(e)}"

                if isinstance(e, TradingError):
                    used_logger.error(error_msg)
                else:
                    used_logger.error(error_msg)

                if re_raise:
                    raise
                return None

        return wrapper

    return decorator


def retry(
        max_attempts: int = 3,
        delay: float = 1.0,
        logger: Optional[TradingLogger] = None,
        *error_types: Type[Exception]
) -> Callable[[F], F]:
    """
    Декоратор для повторного выполнения функции при ошибках.

    Args:
        max_attempts: Максимальное количество попыток.
        delay: Задержка между попытками в секундах.
        logger: Опциональный логгер.
        *error_types: Типы ошибок, при которых следует повторять попытку.

    Returns:
        Декорированную функцию с механизмом повторных попыток.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except error_types if error_types else Exception as e:
                    last_error = e
                    used_logger = logger or TradingLogger(name=func.__module__)
                    used_logger.warning(
                        f"Попытка {attempt}/{max_attempts} не удалась для {func.__qualname__}: {str(e)}"
                    )
                    if attempt < max_attempts:
                        time.sleep(delay)
            raise last_error

        return wrapper

    return decorator