from typing import Dict, Tuple, Any, Optional
from utils.logger import TradingLogger
from exceptions import CredentialsValidationError, RiskValidationError


class CredentialsValidator:
    """Класс для валидации учетных данных MT5"""

    REQUIRED_FIELDS = ['login', 'password', 'server', 'path']
    MIN_PASSWORD_LENGTH = 4

    @classmethod
    def validate(cls, credentials: Dict[str, Any],
                 logger: Optional[TradingLogger] = None) -> Tuple[bool, str]:
        """
        Валидация учетных данных MT5

        Args:
            credentials: Словарь с учетными данными
            logger: Опциональный логгер для записи ошибок

        Returns:
            Tuple[bool, str]: (валидность, сообщение об ошибке)
        """
        try:
            cls._check_required_fields(credentials)
            cls._check_field_types(credentials)
            cls._check_field_values(credentials)
            return True, ""

        except CredentialsValidationError as e:
            if logger:
                e.log_error(logger)
            return False, str(e)
        except Exception as e:
            error = CredentialsValidationError(
                f"Неожиданная ошибка при валидации: {str(e)}",
                logger=logger
            )
            return False, str(error)

    @classmethod
    def _check_required_fields(cls, credentials: Dict[str, Any]) -> None:
        """Проверяет наличие обязательных полей"""
        missing_fields = [f for f in cls.REQUIRED_FIELDS if f not in credentials]
        if missing_fields:
            raise CredentialsValidationError(
                f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"
            )

    @classmethod
    def _check_field_types(cls, credentials: Dict[str, Any]) -> None:
        """Проверяет типы полей"""
        type_checks = {
            'login': (str, int),
            'password': str,
            'server': str,
            'path': str
        }

        for field, types in type_checks.items():
            if not isinstance(credentials[field], types):
                raise CredentialsValidationError(
                    f"Поле {field} должно быть типа {types}"
                )

    @classmethod
    def _check_field_values(cls, credentials: Dict[str, Any]) -> None:
        """Проверяет значения полей"""
        if not str(credentials['login']).strip():
            raise CredentialsValidationError("Логин не может быть пустым")

        if len(credentials['password']) < cls.MIN_PASSWORD_LENGTH:
            raise CredentialsValidationError(
                f"Пароль слишком короткий (мин. {cls.MIN_PASSWORD_LENGTH} символа)"
            )

        if not credentials['server'].strip():
            raise CredentialsValidationError("Сервер не может быть пустым")

        if not credentials['path'].strip():
            raise CredentialsValidationError("Путь к терминалу не может быть пустым")


class RiskParametersValidator:
    """Класс для валидации параметров риска"""

    REQUIRED_FIELDS = ['risk_per_trade', 'risk_all_trades', 'daily_risk']

    @classmethod
    def validate(cls, risks: Dict[str, Any],
                 logger: Optional[TradingLogger] = None) -> Tuple[bool, str]:
        """
        Валидация параметров риска

        Args:
            risks: Словарь с параметрами риска
            logger: Опциональный логгер для записи ошибок

        Returns:
            Tuple[bool, str]: (валидность, сообщение об ошибке)
        """
        try:
            cls._check_required_fields(risks)
            risk_values = cls._convert_and_validate_values(risks)
            cls._check_value_ranges(*risk_values)
            return True, ""

        except RiskValidationError as e:
            if logger:
                e.log_error(logger)
            return False, str(e)
        except Exception as e:
            error = RiskValidationError(
                message=f"Неожиданная ошибка при валидации рисков: {str(e)}",
                parameter="unknown",
                value=str(e),
                valid_range="valid configuration",
                logger=logger
            )
            return False, str(error)

    @classmethod
    def _check_required_fields(cls, risks: Dict[str, Any]) -> None:
        """Проверяет наличие обязательных полей"""
        missing_fields = [f for f in cls.REQUIRED_FIELDS if f not in risks]
        if missing_fields:
            raise RiskValidationError(
                message=f"Отсутствуют обязательные параметры: {', '.join(missing_fields)}",
                parameter="required_fields",
                value=missing_fields,
                valid_range=f"Требуемые поля: {cls.REQUIRED_FIELDS}"
            )

    @classmethod
    def _convert_and_validate_values(cls, risks: Dict[str, Any]) -> Tuple[float, float, float]:
        """Конвертирует и проверяет значения параметров риска"""
        try:
            return (
                float(risks['risk_per_trade']),
                float(risks['risk_all_trades']),
                float(risks['daily_risk'])
            )
        except (ValueError, TypeError) as e:
            raise RiskValidationError(
                message=f"Все параметры риска должны быть числами: {str(e)}",
                parameter="risk_values",
                value=risks,
                valid_range="numeric values"
            )


    @classmethod
    def _check_value_ranges(cls, risk_per_trade: float, risk_all: float, daily_risk: float) -> None:
        """Проверяет допустимые диапазоны значений"""
        if not (0.1 <= risk_per_trade <= 10):
            raise RiskValidationError(
                "Риск на сделку должен быть между 0.1% и 10%",
                parameter='risk_per_trade',
                value=risk_per_trade,
                valid_range='0.1-10%'
            )

        if not (risk_per_trade <= risk_all <= 50):
            raise RiskValidationError(
                "Общий риск должен быть >= риска на сделку и <= 50%",
                parameter='risk_all_trades',
                value=risk_all,
                valid_range=f'{risk_per_trade}-50%'
            )

        if not (risk_all <= daily_risk <= 100):
            raise RiskValidationError(
                "Дневной риск должен быть >= общего риска и <= 100%",
                parameter='daily_risk',
                value=daily_risk,
                valid_range=f'{risk_all}-100%'
            )


# Функции для обратной совместимости
def validate_login_credentials(credentials: Dict[str, Any]) -> Tuple[bool, str]:
    return CredentialsValidator.validate(credentials)


def validate_risk_parameters(risks: Dict[str, Any]) -> Tuple[bool, str]:
    return RiskParametersValidator.validate(risks)