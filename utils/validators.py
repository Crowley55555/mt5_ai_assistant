from typing import Dict, Tuple


def validate_login_credentials(credentials: Dict) -> Tuple[bool, str]:
    """
    Валидация учетных данных MT5

    :param credentials: Словарь с полями 'login', 'password', 'server', 'path'
    :return: Кортеж (успех, сообщение об ошибке)
    """
    if not all(key in credentials for key in ['login', 'password', 'server', 'path']):
        return False, "Не все обязательные поля заполнены"

    if not str(credentials['login']).isdigit():
        return False, "Логин должен быть числом"

    if len(credentials['password']) < 4:
        return False, "Пароль слишком короткий"

    return True, ""


def validate_risk_parameters(risks: Dict) -> Tuple[bool, str]:
    """
    Валидация параметров риска

    :param risks: Словарь с полями 'risk_per_trade', 'risk_all_trades', 'daily_risk'
    :return: Кортеж (успех, сообщение об ошибке)
    """
    try:
        risk_per_trade = float(risks['risk_per_trade'])
        risk_all = float(risks['risk_all_trades'])
        daily_risk = float(risks['daily_risk'])

        if not (0.1 <= risk_per_trade <= 5):
            return False, "Риск на сделку должен быть между 0.1% и 5%"

        if not (risk_per_trade <= risk_all <= 20):
            return False, "Риск на все сделки должен быть >= риска на сделку и <= 20%"

        if not (risk_all <= daily_risk <= 50):
            return False, "Дневной риск должен быть >= риска всех сделок и <= 50%"

        return True, ""
    except (ValueError, KeyError):
        return False, "Некорректные значения рисков"