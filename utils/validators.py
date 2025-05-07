from typing import Dict, Tuple, Any
import logging


def validate_login_credentials(credentials: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Валидация учетных данных MT5

    :param credentials: Словарь с полями 'login', 'password', 'server', 'path'
    :return: Кортеж (успех, сообщение об ошибке)
    """
    required_fields = ['login', 'password', 'server', 'path']

    # Проверяем наличие всех обязательных полей
    missing_fields = [field for field in required_fields if field not in credentials]
    if missing_fields:
        msg = f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"
        return False, msg

    # Проверяем типы данных
    if not isinstance(credentials['login'], (str, int)):
        return False, "Логин должен быть числом или строкой"

    if not isinstance(credentials['password'], str):
        return False, "Пароль должен быть строкой"

    if not isinstance(credentials['server'], str):
        return False, "Сервер должен быть строкой"

    if not isinstance(credentials['path'], str):
        return False, "Путь к терминалу должен быть строкой"

    # Проверяем содержимое
    if not str(credentials['login']).strip():
        return False, "Логин не может быть пустым"

    if len(str(credentials['password'])) < 4:
        return False, "Пароль слишком короткий"

    if not str(credentials['server']).strip():
        return False, "Сервер не может быть пустым"

    if not str(credentials['path']).strip():
        return False, "Путь к терминалу не может быть пустым"

    return True, ""


def validate_risk_parameters(risks: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Валидация параметров риска

    :param risks: Словарь с полями 'risk_per_trade', 'risk_all_trades', 'daily_risk'
    :return: Кортеж (успех, сообщение об ошибке)
    """
    required_fields = ['risk_per_trade', 'risk_all_trades', 'daily_risk']

    # Проверяем наличие всех обязательных полей
    missing_fields = [field for field in required_fields if field not in risks]
    if missing_fields:
        msg = f"Отсутствуют обязательные параметры: {', '.join(missing_fields)}"
        return False, msg

    try:
        risk_per_trade = float(risks['risk_per_trade'])
        risk_all = float(risks['risk_all_trades'])
        daily_risk = float(risks['daily_risk'])
    except ValueError as e:
        return False, f"Все параметры риска должны быть числами: {str(e)}"

    # Проверяем диапазоны значений
    if not (0.1 <= risk_per_trade <= 10):
        return False, "Риск на сделку должен быть между 0.1% и 10%"

    if not (risk_per_trade <= risk_all <= 50):
        return False, "Общий риск должен быть >= риска на сделку и <= 50%"

    if not (risk_all <= daily_risk <= 100):
        return False, "Дневной риск должен быть >= общего риска и <= 100%"

    return True, ""