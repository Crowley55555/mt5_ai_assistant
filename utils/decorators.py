import time
import logging
from functools import wraps
from typing import Callable, Any


def log_execution_time(func: Callable) -> Callable:
    """
    Декоратор для логирования времени выполнения функции

    :param func: Декорируемая функция
    :return: Обернутая функция
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time

        logger = logging.getLogger(func.__module__)
        logger.debug(
            f"Функция {func.__name__} выполнена за {elapsed:.3f} сек"
        )
        return result

    return wrapper


def handle_errors(func: Callable) -> Callable:
    """
    Декоратор для обработки и логирования ошибок

    :param func: Декорируемая функция
    :return: Обернутая функция
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger(func.__module__)
            logger.error(
                f"Ошибка в функции {func.__name__}: {str(e)}",
                exc_info=True
            )
            raise

    return wrapper