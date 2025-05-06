import requests
from typing import Optional, Dict, List
import json
from pathlib import Path
from utils.logger import TradingLogger


class OllamaIntegration:
    def __init__(self, base_url: str, model: str, logger: TradingLogger):
        self.base_url = base_url
        self.model = model
        self.logger = logger
        self.knowledge_base = []

    def load_knowledge(self, file_path: str) -> bool:
        """Загрузка базы знаний из файла"""
        try:
            path = Path(file_path)
            if not path.exists():
                self.logger.error(f"Файл {file_path} не найден")
                return False

            if path.suffix.lower() == '.pdf':
                # Для PDF используем дополнительную библиотеку
                try:
                    import PyPDF2
                    with open(path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        text = "\n".join([page.extract_text() for page in reader.pages])
                        self.knowledge_base.append({
                            'source': path.name,
                            'content': text
                        })
                except ImportError:
                    self.logger.error("Для чтения PDF требуется установка PyPDF2")
                    return False
            else:
                # Текстовые файлы
                with open(path, 'r', encoding='utf-8') as f:
                    self.knowledge_base.append({
                        'source': path.name,
                        'content': f.read()
                    })

            self.logger.info(f"Загружена база знаний из {path.name}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка загрузки базы знаний: {str(e)}")
            return False

    def analyze_market(self, symbol: str, data: Dict) -> Optional[Dict]:
        """Анализ рыночной ситуации с помощью Ollama"""
        prompt = self._prepare_prompt(symbol, data)
        if not prompt:
            return None

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'stream': False
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"Получен ответ от Ollama: {result['response']}")
                return self._parse_response(result['response'])
            else:
                self.logger.error(f"Ошибка запроса к Ollama: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Ошибка подключения к Ollama: {str(e)}")
            return None

    def _prepare_prompt(self, symbol: str, data: Dict) -> str:
        """Подготовка промта для анализа"""
        prompt = (
            f"Ты - профессиональный финансовый аналитик. Проанализируй текущую рыночную ситуацию для {symbol}.\n"
            f"Данные для анализа:\n{json.dumps(data, indent=2)}\n\n"
            f"Учитывай следующую информацию из базы знаний:\n"
            f"{self._get_relevant_knowledge(symbol)}\n\n"
            f"Дай рекомендацию: покупать, продавать или ждать. "
            f"Обоснуй свой ответ и укажи ключевые уровни поддержки и сопротивления."
        )
        return prompt

    def _get_relevant_knowledge(self, symbol: str) -> str:
        """Получение релевантной информации из базы знаний"""
        # Здесь можно реализовать более сложную логику поиска
        relevant = []
        for item in self.knowledge_base:
            if symbol.lower() in item['content'].lower():
                relevant.append(f"Из {item['source']}:\n{item['content'][:500]}...")

        return "\n\n".join(relevant) if relevant else "Нет релевантной информации в базе знаний."

    def _parse_response(self, response: str) -> Dict:
        """Парсинг ответа от Ollama"""
        # Здесь можно добавить более сложную логику парсинга
        return {
            'recommendation': self._extract_recommendation(response),
            'reasoning': response,
            'support_levels': self._extract_levels(response, 'поддержки'),
            'resistance_levels': self._extract_levels(response, 'сопротивления')
        }

    def _extract_recommendation(self, text: str) -> str:
        """Извлечение рекомендации из текста"""
        text_lower = text.lower()
        if 'покупать' in text_lower:
            return 'buy'
        elif 'продавать' in text_lower:
            return 'sell'
        return 'wait'

    def _extract_levels(self, text: str, level_type: str) -> List[float]:
        """Извлечение уровней поддержки/сопротивления"""
        # Упрощенная реализация - в реальном проекте нужен более сложный парсинг
        import re
        pattern = re.compile(rf'уров(ень|ни) {level_type}[:\s]+([\d\.]+)')
        matches = pattern.findall(text.lower())
        return [float(m[1]) for m in matches if m and m[1]]