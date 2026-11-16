"""Gemini API: структурована JSON-відповідь за схемою."""
import json

import httpx

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

VACANCY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "company": {"type": "STRING", "nullable": True},
        "role": {"type": "STRING", "nullable": True},
        "stack": {"type": "ARRAY", "items": {"type": "STRING"}},
        "salary": {"type": "STRING", "nullable": True},
        "work_format": {"type": "STRING", "nullable": True},
        "level": {"type": "STRING", "nullable": True},
    },
    "required": ["company", "role", "stack", "salary", "work_format", "level"],
}

MATCH_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "match_percent": {"type": "INTEGER"},
        "matched": {"type": "ARRAY", "items": {"type": "STRING"}},
        "missing": {"type": "ARRAY", "items": {"type": "STRING"}},
        "advice": {"type": "STRING"},
    },
    "required": ["match_percent", "matched", "missing", "advice"],
}

EXTRACT_PROMPT = """Ти розбираєш текст вакансії. Поверни JSON:
- company: назва компанії
- role: назва посади
- stack: список технологій і інструментів з вимог (короткі назви, без дублікатів)
- salary: зарплата як у тексті (наприклад "$1500-2000"), без вигадок
- work_format: одне з "віддалено", "офіс", "гібрид"
- level: одне з "Intern", "Junior", "Middle", "Senior", "Lead"
Якщо чогось у тексті немає, став null (для stack порожній список). Нічого не вигадуй."""

MATCH_PROMPT = """Порівняй стек кандидата з вимогами вакансії. Поверни JSON:
- match_percent: наскільки кандидат підходить, 0-100
- matched: навички кандидата, які потрібні у вакансії
- missing: навички з вакансії, яких кандидату бракує
- advice: одна-дві фрази українською, що підтягнути в першу чергу
Вважай синоніми однією навичкою (React і React.js, Postgres і PostgreSQL)."""


class AIError(Exception):
    pass


class Gemini:
    def __init__(self, api_key: str, model: str):
        self.url = API.format(model=model)
        self.http = httpx.AsyncClient(headers={"x-goog-api-key": api_key}, timeout=60)

    async def close(self) -> None:
        await self.http.aclose()

    async def _json(self, system: str, user: str, schema: dict) -> dict:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "temperature": 0.1,
            },
        }
        r = await self.http.post(self.url, json=body)
        if r.status_code != 200:
            raise AIError(f"Gemini API {r.status_code}: {r.text[:300]}")
        try:
            parts = r.json()["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            return json.loads(text)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
            raise AIError(f"Не вдалося розібрати відповідь Gemini: {e}") from e

    async def extract_vacancy(self, text: str) -> dict:
        data = await self._json(EXTRACT_PROMPT, text, VACANCY_SCHEMA)
        return {
            "company": data.get("company"),
            "role": data.get("role"),
            "stack": [s for s in (data.get("stack") or []) if isinstance(s, str)],
            "salary": data.get("salary"),
            "work_format": data.get("work_format"),
            "level": data.get("level"),
        }

    async def match(self, vacancy: dict, my_stack: list[str]) -> dict:
        user = (
            f"Стек кандидата: {', '.join(my_stack)}\n\n"
            f"Вакансія: {vacancy.get('role')} у {vacancy.get('company')}\n"
            f"Стек вакансії: {', '.join(vacancy.get('stack') or [])}\n\n"
            f"Текст вакансії:\n{(vacancy.get('raw_text') or '')[:8000]}"
        )
        return await self._json(MATCH_PROMPT, user, MATCH_SCHEMA)
