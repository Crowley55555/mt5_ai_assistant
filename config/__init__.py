"""
Модуль конфигурации торгового ассистента

Содержит:
- Классы для работы с настройками и конфигурацией
- Константы и перечисления для торговых операций
- Вспомогательные функции управления конфигурацией
"""

from .settings import Settings
from .constants import (
    Timeframe,
    TradeAction,
    OrderType,
    StrategyName
)
from typing import List
from pathlib import Path
import json
import json.decoder

__all__ = [
    'Settings',
    'Timeframe',
    'TradeAction',
    'OrderType',
    'StrategyName',
    'get_version',
    'validate_config',
    'create_default_config',
    'get_available_configs'
]

def get_version() -> str:
    """Возвращает версию конфигурационного модуля

    Returns:
        str: Строка версии в формате 'MAJOR.MINOR.PATCH'
    """
    return '1.2.1'

def validate_config(config_path: Path) -> bool:
    """Проверяет валидность конфигурационного файла

    Args:
        config_path: Путь к файлу конфигурации

    Returns:
        bool: True если конфиг валиден, False в противном случае

    Raises:
        FileNotFoundError: Если файл не существует
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        required_sections = ['accounts', 'telegram', 'risk_management']
        return all(section in config for section in required_sections)

    except json.decoder.JSONDecodeError:
        return False
    except UnicodeDecodeError:
        return False
    except PermissionError:
        return False

def create_default_config(config_path: Path) -> None:
    """Создает конфигурационный файл с настройками по умолчанию

    Args:
        config_path: Путь для создания файла конфигурации

    Raises:
        PermissionError: Если нет прав для записи
        IsADirectoryError: Если путь является директорией
        json.JSONEncodeError: При ошибках кодирования JSON
    """
    default_config = {
        "version": 1,
        "accounts": [],
        "telegram": {
            "token": "",
            "chat_id": ""
        },
        "ollama": {
            "base_url": "http://localhost:11434",
            "model": ""
        },
        "risk_management": {
            "risk_per_trade": 1.0,
            "risk_all_trades": 5.0,
            "daily_risk": 10.0
        },
        "strategies": {
            "sniper": True,
            "smart_sniper": False,
            "smart_money": False
        }
    }

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
    except (PermissionError, IsADirectoryError) as e:
        raise PermissionError(f"Cannot write config to {config_path}: {str(e)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid configuration data: {str(e)}")

def get_available_configs(config_dir: Path) -> List[str]:
    """Возвращает список доступных конфигураций в директории

    Args:
        config_dir: Директория с конфигурационными файлами

    Returns:
        List[str]: Список имен файлов конфигураций

    Raises:
        NotADirectoryError: Если путь не является директорией
    """
    if not config_dir.is_dir():
        raise NotADirectoryError(f"Config directory not found: {config_dir}")

    return [f.name for f in config_dir.glob('*.json') if f.is_file()]