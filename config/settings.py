import json
from pathlib import Path
from typing import Dict, List, Optional


class Settings:
    def __init__(self, config_path: str = "config/config.json"):
        self.config_path = Path(config_path)
        self._settings = self._load_settings()
        self.logger = None  # Будет установлен извне

    def get_database_config(self) -> Dict:
        """Возвращает конфиг БД с проверкой обязательных полей"""
        db_config = self._settings.get('database', {})
        if not db_config.get('connection_string'):
            db_config['connection_string'] = 'sqlite:///data/trading.db'
        return db_config

    def set_logger(self, logger):
        self.logger = logger

    def _load_settings(self) -> Dict:
        default = {
            "accounts": [],
            "current_account_index": 0,
            "telegram": {"token": "", "chat_id": ""},
            "database": {"type": "sqlite", "connection_string": "sqlite:///data/trading.db"},
            "ollama": {"base_url": "http://localhost:11434", "model": "llama2"},
            "risk_management": {"risk_per_trade": 1.0, "risk_all_trades": 5.0, "daily_risk": 10.0}
        }

        try:
            if not self.config_path.exists():
                if self.logger:
                    self.logger.info("Конфиг не найден, создан новый с настройками по умолчанию")
                return default

            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)

                # Совместимость с предыдущей версией
                if "mt5" in loaded and loaded["mt5"]:
                    if self.logger:
                        self.logger.info("Обнаружен старый формат настроек MT5, конвертируем в новый")
                    default["accounts"].append({
                        "login": loaded["mt5"].get("login", ""),
                        "password": loaded["mt5"].get("password", ""),
                        "server": loaded["mt5"].get("server", ""),
                        "path": loaded["mt5"].get("path", "")
                    })

                return {**default, **loaded}
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка загрузки конфига: {str(e)}")
            return default

    def save(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
            if self.logger:
                self.logger.debug("Настройки успешно сохранены")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка сохранения настроек: {str(e)}")

    @property
    def accounts(self) -> List[Dict]:
        return self._settings.get("accounts", [])

    @property
    def current_account(self) -> Dict:
        idx = self._settings.get("current_account_index", 0)
        return self.accounts[idx] if self.accounts else {
            "login": "", "password": "", "server": "", "path": ""
        }

    def add_account(self, login: str, password: str, server: str, path: str):
        if not any(acc["login"] == login for acc in self.accounts):
            self._settings["accounts"].append({
                "login": login,
                "password": password,
                "server": server,
                "path": path
            })
            self.save()

    def set_current_account(self, index: int):
        if 0 <= index < len(self.accounts):
            self._settings["current_account_index"] = index
            self.save()