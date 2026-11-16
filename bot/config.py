"""Налаштування з env-змінних. Жодних ключів у коді."""
import os

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Не задано env-змінну {name}. Дивись bot/.env.example")
    return value


TELEGRAM_TOKEN = _required("TELEGRAM_TOKEN")
GEMINI_API_KEY = _required("GEMINI_API_KEY")
SUPABASE_URL = _required("SUPABASE_URL")
SUPABASE_KEY = _required("SUPABASE_KEY")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()
# Запасна модель, якщо основна перевантажена (503) або не відповідає.
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-flash-lite-latest").strip()

# Твій стек для /match, через кому: "Python, SQL, React"
MY_STACK = [s.strip() for s in os.getenv("MY_STACK", "").split(",") if s.strip()]

# Telegram ID, яким дозволено користуватись ботом (через кому). Порожньо = всім.
ALLOWED_USER_IDS = {
    int(s) for s in os.getenv("ALLOWED_USER_IDS", "").replace(" ", "").split(",") if s
}

# Вебхук: на Render адреса підставляється сама (RENDER_EXTERNAL_URL).
# Якщо адреси немає, бот працює через polling (зручно локально).
WEBHOOK_URL = (os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")
PORT = int(os.getenv("PORT", "8080"))
