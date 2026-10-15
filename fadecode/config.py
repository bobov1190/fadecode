import os
import secrets
from datetime import timedelta


def load_env(path):
    """Мини-загрузчик .env: KEY=VALUE, уже заданные переменные окружения не перезаписываются."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                    v = v[1:-1]
                os.environ.setdefault(k, v)
    except FileNotFoundError:
        pass


def _secret_key(instance_path):
    env = os.environ.get("SECRET_KEY", "").strip()
    if env:
        return env
    path = os.path.join(instance_path, "secret.key")
    try:
        with open(path, encoding="utf-8") as f:
            key = f.read().strip()
            if key:
                return key
    except FileNotFoundError:
        pass
    key = secrets.token_hex(32)
    os.makedirs(instance_path, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(key)
    return key


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def default_config(instance_path):
    models = [m.strip() for m in os.environ.get("AI_MODELS", "openrouter/free").split(",") if m.strip()]
    return dict(
        SECRET_KEY=_secret_key(instance_path),
        # DATABASE_URL (Postgres/Neon) главнее; без неё работает SQLite-файл (локально и в тестах)
        DATABASE_URL=os.environ.get("DATABASE_URL", "").strip(),
        DATABASE_SCHEMA=os.environ.get("DATABASE_SCHEMA", "").strip(),
        DB_POOL_MAX=_int("DB_POOL_MAX", 5),
        DATABASE=os.environ.get("FADECODE_DB") or os.path.join(instance_path, "fadecode.db"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SECURE_COOKIES") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        MAX_CONTENT_LENGTH=256 * 1024,
        MAX_ANSWER_CHARS=6000,
        OPENROUTER_API_KEY=os.environ.get("OPENROUTER_API_KEY", "").strip(),
        AI_MODELS=models,
        AI_DAILY_GLOBAL=_int("AI_DAILY_GLOBAL", 45),
        AI_DAILY_USER=_int("AI_DAILY_USER", 30),
        AI_TIMEOUT=_int("AI_TIMEOUT", 45),
        AI_MAX_TOKENS=_int("AI_MAX_TOKENS", 700),
    )
