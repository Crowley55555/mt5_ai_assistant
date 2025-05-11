import requests
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path
import re
from utils.logger import TradingLogger
from utils.exceptions import OllamaError, KnowledgeBaseError
from utils.helpers import format_dict
from dataclasses import dataclass
import json

PdfReader: Optional[Any] = None
PDF_SUPPORT = False

try:
    from PyPDF2 import PdfReader

    PDF_SUPPORT = True
except ImportError:
    class DummyPdfReader:
        """Заглушка для PdfReader при отсутствии PyPDF2"""

        def __init__(self, *args, **kwargs):
            raise ImportError("PyPDF2 не установлен. Установите его через: pip install pypdf2")

        @property
        def pages(self):
            raise ImportError("PyPDF2 не установлен. Установите его через: pip install pypdf2")


    PdfReader = DummyPdfReader
    PDF_SUPPORT = False


@dataclass
class KnowledgeItem:
    """Элемент базы знаний"""
    source: str
    content: str
    last_updated: datetime


@dataclass
class AnalysisResult:
    """Результат анализа рынка"""
    recommendation: str  # buy/sell/wait
    reasoning: str
    support_levels: List[float]
    resistance_levels: List[float]
    model_used: str
    timestamp: str
    prompt_length: int
    raw_response: Optional[str] = None
    error: Optional[str] = None


class OllamaIntegration:
    """Класс для интеграции с Ollama API и анализа рыночных данных."""

    DEFAULT_TIMEOUT = 60
    MAX_PROMPT_LENGTH = 8000

    def __init__(self, base_url: str, model: str, logger: TradingLogger):
        """
        Инициализация интеграции с Ollama.

        Args:
            base_url: URL API Ollama (например, "http://localhost:11434")
            model: Название модели (например, "llama2")
            logger: Логгер приложения
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.logger = logger
        self.knowledge_base: List[KnowledgeItem] = []

    def load_knowledge(self, file_path: Union[str, Path]) -> bool:
        """
        Загружает файл в базу знаний.

        Args:
            file_path: Путь к файлу (PDF или текстовый)

        Returns:
            bool: True если загрузка успешна, иначе False

        Raises:
            KnowledgeBaseError: При критических ошибках загрузки
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Файл {path} не найден")

            content = self._read_file_content(path)
            if not content:
                return False

            self.knowledge_base.append(KnowledgeItem(
                source=path.name,
                content=content,
                last_updated=datetime.now()
            ))
            self.logger.info(f"Загружен файл {path.name} в базу знаний")
            return True

        except Exception as e:
            error_msg = f"Ошибка загрузки базы знаний: {str(e)}"
            self.logger.error(error_msg)
            raise KnowledgeBaseError(error_msg) from e

    def _read_file_content(self, path: Path) -> Optional[str]:
        """Читает содержимое файла в зависимости от его типа."""
        if path.suffix.lower() == ".pdf":
            if not PDF_SUPPORT:
                self.logger.warning("Для чтения PDF требуется PyPDF2")
                return None
            return self._read_pdf(path)
        return self._read_text_file(path)

    def _read_pdf(self, path: Path) -> str:
        """Читает текст из PDF файла."""
        if not PDF_SUPPORT:
            self.logger.warning("Для чтения PDF требуется установить PyPDF2")
            raise ImportError("PyPDF2 не установлен")

        try:
            with open(path, "rb") as f:
                if PdfReader is None:
                    raise ImportError("PdfReader не доступен")

                reader = PdfReader(f)
                if not hasattr(reader, 'pages'):
                    raise AttributeError("Объект PdfReader не имеет атрибута pages")

                return "\n".join(
                    page.extract_text() or ""
                    for page in reader.pages  # Теперь pages точно существует
                    if hasattr(page, 'extract_text')
                )
        except Exception as e:
            self.logger.error(f"Ошибка чтения PDF: {str(e)}")
            raise

    def _read_text_file(self, path: Path) -> str:
        """Читает текст из текстового файла."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Ошибка чтения файла: {str(e)}")
            raise

    def get_analysis(self, symbol: str, market_data: Dict) -> AnalysisResult:
        """
        Получает анализ рыночной ситуации.

        Args:
            symbol: Торговый символ (например, "EURUSD")
            market_data: Рыночные данные для анализа

        Returns:
            AnalysisResult: Результат анализа
        """
        try:
            prompt = self._prepare_prompt(symbol, market_data)
            if len(prompt) > self.MAX_PROMPT_LENGTH:
                prompt = prompt[:self.MAX_PROMPT_LENGTH]
                self.logger.warning(f"Промпт сокращен до {self.MAX_PROMPT_LENGTH} символов")

            response = self._send_ollama_request(prompt)
            return self._parse_response(response, prompt)

        except Exception as e:
            error_msg = f"Ошибка анализа для {symbol}: {str(e)}"
            self.logger.error(error_msg)
            return AnalysisResult(
                recommendation="wait",
                reasoning=error_msg,
                support_levels=[],
                resistance_levels=[],
                model_used=self.model,
                timestamp=datetime.now().isoformat(),
                prompt_length=0,
                error=error_msg
            )

    def _send_ollama_request(self, prompt: str) -> Dict:
        """Отправляет запрос к Ollama API."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_ctx": 4096,
                "max_tokens": 1024
            }
        }

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка запроса к Ollama: {str(e)}"
            self.logger.error(error_msg)
            raise OllamaError(error_msg) from e

    def _prepare_prompt(self, symbol: str, data: Dict) -> str:
        """Формирует промпт для анализа."""
        context = self._get_relevant_context(symbol)
        return (
            f"Ты профессиональный финансовый аналитик. Проанализируй {symbol}.\n\n"
            f"Данные:\n{format_dict(data)}\n\n"
            f"Контекст:\n{context}\n\n"
            "Рекомендация (buy/sell/wait)? Обоснуй и укажи уровни поддержки/сопротивления."
        )

    def _get_relevant_context(self, symbol: str) -> str:
        """Возвращает релевантный контекст из базы знаний."""
        symbol_lower = symbol.lower()
        relevant = [
            f"Из {item.source}:\n{item.content[:1000]}..."
            for item in self.knowledge_base
            if symbol_lower in item.content.lower()
        ]
        return "\n\n".join(relevant) if relevant else "Нет релевантного контекста"

    def _parse_response(self, response: Dict, prompt: str) -> AnalysisResult:
        """Парсит ответ от Ollama."""
        response_text = response.get("response", "")

        return AnalysisResult(
            recommendation=self._parse_recommendation(response_text),
            reasoning=response_text,
            support_levels=self._parse_levels(response_text, "support"),
            resistance_levels=self._parse_levels(response_text, "resistance"),
            model_used=self.model,
            timestamp=datetime.now().isoformat(),
            prompt_length=len(prompt),
            raw_response=json.dumps(response)
        )
    @staticmethod
    def _parse_recommendation(text: str) -> str:
        """Извлекает рекомендацию из текста."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["покупать", "buy", "long"]):
            return "buy"
        if any(kw in text_lower for kw in ["продавать", "sell", "short"]):
            return "sell"
        return "wait"
    @staticmethod
    def _parse_levels(text: str, level_type: str) -> List[float]:
        """Извлекает уровни поддержки/сопротивления."""
        patterns = {
            "support": [
                r'поддержк[а-я]*\s*[\d\.,]+\s*(\d+[\.,]\d+)',
                r'support\s*[\d\.,]+\s*(\d+[\.,]\d+)'
            ],
            "resistance": [
                r'сопротивлени[а-я]*\s*[\d\.,]+\s*(\d+[\.,]\d+)',
                r'resistance\s*[\d\.,]+\s*(\d+[\.,]\d+)'
            ]
        }

        levels = set()
        for pattern in patterns.get(level_type, []):
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    value = float(match.group(1).replace(",", "."))
                    levels.add(round(value, 5))
                except (ValueError, AttributeError):
                    continue

        return sorted(levels)