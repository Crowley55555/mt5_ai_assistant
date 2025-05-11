import requests
from typing import Dict, List, Any
from utils.logger import TradingLogger
from datetime import datetime
from pathlib import Path
from PyPDF2 import PdfReader
import re
from utils.helpers import format_dict

class OllamaIntegration:
    def __init__(self, base_url: str, model: str, logger: TradingLogger):
        """
        Интеграция с LLM через Ollama

        :param base_url: Базовый URL Ollama API (например, http://localhost:11434)
        :param model: Название модели (например, 'llama2')
        :param logger: Логгер приложения
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.logger = logger  # <-- Теперь используем TradingLogger напрямую
        self.knowledge_base = []  # <-- хранение базы знаний

    def load_knowledge(self, file_path: str) -> bool:
        """Загрузка содержимого файла в базу знаний"""
        try:
            path = Path(file_path)
            if not path.exists():
                self.logger.error(f"Файл {file_path} не найден")
                return False

            # Загрузка из PDF
            if path.suffix.lower() == ".pdf":
                try:
                    with open(path, "rb") as f:
                        reader = PdfReader(f)
                        text = "\n".join([page.extract_text() for page in reader.pages])
                        self.knowledge_base.append({
                            "source": path.name,
                            "content": text
                        })
                    self.logger.info(f"База знаний загружена из {path.name}")
                    return True
                except ImportError:
                    self.logger.warning("Для чтения PDF требуется установить PyPDF2")
                    return False

            # Загрузка из текстовых файлов
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                self.knowledge_base.append({
                    "source": path.name,
                    "content": content
                })

            self.logger.info(f"База знаний загружена из {path.name}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка загрузки базы знаний: {str(e)}")
            return False

    def analyze_market(self, prompt: str) -> Dict[str, Any]:

        """
        Анализ рыночной ситуации с помощью Ollama

        :param prompt: Промпт для анализа
        :return: Словарь с результатами анализа
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_context": 2048,
                "max_tokens": 1024
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                self.logger.debug("Ответ от Ollama успешно получен")
                return self._parse_response(result.get("response", ""))
            elif response.status_code == 503:
                self.logger.warning("Ollama: сервис недоступен")
                return {"error": "Сервер Ollama недоступен"}
            elif response.status_code == 400:
                self.logger.warning("Ollama: невалидный запрос")
                return {"error": "Невалидный промпт или параметры запроса"}
            else:
                error_msg = f"Ollama: код {response.status_code}, ответ: {response.text[:100]}..."
                self.logger.error(error_msg)
                return {"error": error_msg}

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка подключения к Ollama: {str(e)}")
            return {"error": f"Ошибка подключения: {str(e)}"}

    def _prepare_prompt(self, symbol: str, data: Dict) -> str:
        """
        Формирует промпт для анализа на основе данных и базы знаний

        :param symbol: Торговая пара (например, EURUSD)
        :param data: Данные о рынке
        :return: Готовый промпт
        """
        relevant_info = self._get_relevant_knowledge(symbol)

        prompt = (
            f"Вы — профессиональный финансовый аналитик. Проанализируйте текущую ситуацию по {symbol}.\n\n"
            f"Данные:\n{format_dict(data)}\n\n"
            f"Релевантная информация из базы знаний:\n{relevant_info}\n\n"
            "Рекомендация: покупать, продавать или ждать?\n"
            "Обоснуйте рекомендацию и укажите ключевые уровни поддержки и сопротивления."
        )

        self.logger.debug(f"Промпт для {symbol} создан ({len(prompt)} символов)")
        return prompt

    def _get_relevant_knowledge(self, symbol: str) -> str:
        """
        Поиск информации в базе знаний по символу

        :param symbol: Торговая пара
        :return: Релевантные данные из знаний
        """
        results = []
        symbol_lower = symbol.lower()

        for item in self.knowledge_base:
            if symbol_lower in item["content"].lower():
                results.append(f"Из {item['source']}:\n{item['content'][:500]}...")

        return "\n\n".join(results) if results else "Нет релевантной информации"

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Парсинг ответа от LLM

        :param response: Ответ модели
        :return: Распарсенные данные
        """
        try:
            recommendation = self._extract_recommendation(response)
            support_levels = self._extract_levels(response, "поддержки")
            resistance_levels = self._extract_levels(response, "сопротивления")

            return {
                "recommendation": recommendation,
                "reasoning": response,
                "support_levels": support_levels,
                "resistance_levels": resistance_levels,
                "raw_response": response
            }
        except Exception as e:
            self.logger.error(f"Ошибка парсинга ответа: {str(e)}")
            return {
                "recommendation": "wait",
                "reasoning": f"Ошибка парсинга: {str(e)}",
                "support_levels": [],
                "resistance_levels": [],
                "raw_response": ""
            }

    def _extract_recommendation(self, text: str) -> str:
        """Извлечение торговой рекомендации из текста"""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["покупать", "buy", "long"]):
            return "buy"
        elif any(kw in text_lower for kw in ["продавать", "sell", "short"]):
            return "sell"
        elif any(kw in text_lower for kw in ["ждать", "wait", "hold"]):
            return "wait"
        else:
            self.logger.warning("Не удалось распознать рекомендацию")
            return "wait"

    def _extract_levels(self, text: str, level_type: str) -> List[float]:
        """
        Извлечение уровней поддержки/сопротивления

        :param text: Текст для анализа
        :param level_type: 'support' или 'resistance'
        :return: Список найденных уровней
        """
        patterns = [
            rf'{level_type}[\s\d\.]*?(\d+[\.,]\d+|\d+\s\d+)'
        ]

        if level_type == "support":
            patterns.extend([
                r'Поддержка.*?(\d+[\.,]\d+)',
                r'Уровень поддержки.*?(\d+[\.,]\d+)'
            ])
        elif level_type == "resistance":
            patterns.extend([
                r'Сопротивление.*?(\d+[\.,]\d+)',
                r'Уровень сопротивления.*?(\d+[\.,]\d+)'
            ])

        results = []
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                try:
                    value = float(match.replace(",", ".").replace(" ", ""))
                    results.append(value)
                except ValueError:
                    continue

        # Удаляем близкие значения
        unique_results = []
        for value in sorted(results):
            if not unique_results or abs(value - unique_results[-1]) > 0.0001:
                unique_results.append(round(value, 5))

        self.logger.debug(f"Найдено {len(unique_results)} уровней {level_type}: {unique_results}")
        return unique_results


    def get_analysis(self, symbol: str, data: Dict) -> Dict[str, Any]:
        """
        Получает анализ рынка через Ollama

        :param symbol: Символ для анализа
        :param data: Рыночные данные
        :return: Результат анализа
        """
        prompt = self._prepare_prompt(symbol, data)
        analysis_result = self.analyze_market(prompt)

        if analysis_result.get("error"):
            return analysis_result

        analysis_result.update({
            "model_used": self.model,
            "timestamp": datetime.now().isoformat(),
            "prompt_length": len(prompt),
        })

        self.logger.info(f"Получен анализ для {symbol}")
        return analysis_result