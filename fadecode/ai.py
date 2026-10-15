"""ИИ-наставник через OpenRouter: промпты, запасные модели, дневные квоты, кэш и защита от «слива» решения."""
import hashlib
import json
import time
import urllib.error
import urllib.request

from flask import current_app

from . import content, db

URL = "https://openrouter.ai/api/v1/chat/completions"
LEAK_MSG = ("Я чуть не выдал готовое решение, а так тренировка не работает. "
            "Спроси иначе: про идею, формы массивов или какую функцию искать, и я наведу.")

TUTOR_SYSTEM = (
    "Ты наставник в тренажёре Fadecode. Ученик учит наизусть код алгоритмов (Python, numpy): "
    "разбирает, копирует поверх призрачного текста, потом вспоминает методы, которые исчезают.\n"
    "Правила: отвечай по-русски, коротко (до 6 предложений), по делу. "
    "НЕ пиши готовый код пропавшего метода и не пересказывай его строка за строкой: "
    "давай наводящие вопросы, называй идею, формы массивов, нужные функции. "
    "Если спрашивают «что не так», покажи, в каком месте расхождение, и подскажи, как исправить, "
    "но не дописывай решение за ученика. Если ответа нет в данных, так и скажи."
)

ADVICE_SYSTEM = (
    "Ты помогаешь ученику Fadecode спланировать повторение кода. Тебе дают сводку по методам: "
    "коробка 0-4 (чем меньше, тем хуже запомнено), число провалов и просмотров. "
    "Ответь по-русски: 3-5 коротких пунктов, что повторить первым и почему, "
    "называй урок и метод. Без общих советов и без кода."
)


class AIError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.message = message
        self.status = status


def today():
    return time.strftime("%Y-%m-%d", time.gmtime())


def _post(payload, key, timeout):
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "X-Title": "Fadecode",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def complete(messages):
    """Пробует модели из AI_MODELS по очереди и возвращает первый непустой ответ."""
    cfg = current_app.config
    key = cfg["OPENROUTER_API_KEY"]
    if not key:
        raise AIError("ИИ не настроен: впиши OPENROUTER_API_KEY в файл .env и перезапусти сервер.", 503)
    reason = "не удалось получить ответ от модели"
    rate_limited = False
    for model in cfg["AI_MODELS"]:
        payload = {"model": model, "messages": messages, "max_tokens": cfg["AI_MAX_TOKENS"], "temperature": 0.3}
        try:
            data = _post(payload, key, cfg["AI_TIMEOUT"])
            msg = ((data.get("choices") or [{}])[0].get("message")) or {}
            text = (msg.get("content") or "").strip()
            if text:
                return text
            reason = "модель вернула пустой ответ"
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise AIError("OpenRouter не принял ключ: проверь OPENROUTER_API_KEY.", 502)
            if e.code == 429:
                rate_limited = True
            reason = "модель %s ответила ошибкой %d" % (model, e.code)
        except (OSError, ValueError) as e:
            reason = "нет ответа от OpenRouter (%s)" % type(e).__name__
    if rate_limited:
        raise AIError("Лимит бесплатных моделей OpenRouter исчерпан или они перегружены. Попробуй через минуту.", 502)
    raise AIError("ИИ сейчас недоступен: " + reason + ".", 502)


def leaks(reply, target):
    """Похоже, что в ответе воспроизведено решение (≥60% значимых строк эталона)?"""
    lines = [l.strip() for l in target.split("\n") if len(l.strip()) >= 14]
    if len(lines) < 2:
        return False
    hit = sum(1 for l in lines if l in reply)
    return hit >= max(2, int(len(lines) * 0.6 + 0.5))


def _left(uid, day):
    cfg = current_app.config
    user_n, total_n = db.ai_counts(day, uid)
    return max(0, min(cfg["AI_DAILY_USER"] - user_n, cfg["AI_DAILY_GLOBAL"] - total_n))


def ask(uid, material, messages, target=None):
    """Кэш -> квоты -> запрос. Повторный одинаковый вопрос лимит не тратит."""
    cfg = current_app.config
    h = hashlib.sha256(json.dumps(material, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    day = today()
    cached = db.cache_get(h)
    if cached is not None:
        return {"text": cached, "cached": True, "left": _left(uid, day)}
    user_n, total_n = db.ai_counts(day, uid)
    if user_n >= cfg["AI_DAILY_USER"]:
        raise AIError("Твой дневной лимит ИИ-запросов (%d) исчерпан. Завтра обновится." % cfg["AI_DAILY_USER"], 429)
    if total_n >= cfg["AI_DAILY_GLOBAL"]:
        raise AIError("Общий дневной лимит бесплатных запросов исчерпан. Попробуй завтра.", 429)
    db.ai_bump(day, uid)
    text = complete(messages)
    if target and leaks(text, target):
        return {"text": LEAK_MSG, "cached": False, "left": _left(uid, day)}
    db.cache_put(h, text)
    return {"text": text, "cached": False, "left": _left(uid, day)}


def tutor_messages(L, focus, missing_names, attempt, history, message):
    ctx = ["Урок: %s." % L["title"]]
    if L.get("task"):
        ctx.append("Задача: %s" % L["task"])
    if missing_names:
        ctx.append("Сейчас пропали методы: %s." % ", ".join(missing_names))
    system = TUTOR_SYSTEM + "\n\n" + "\n".join(ctx)
    if focus:
        ref = content.slot_target(L, focus)
        system += ("\n\nЭТАЛОН метода, над которым ученик работает (только для тебя, не показывай его "
                   "целиком и не цитируй подряд):\n" + ref)
    if attempt.strip():
        system += "\n\nТЕКУЩАЯ ПОПЫТКА УЧЕНИКА:\n" + attempt
    return [{"role": "system", "content": system}] + history + [{"role": "user", "content": message}]


def advice_messages(summary):
    return [
        {"role": "system", "content": ADVICE_SYSTEM},
        {"role": "user", "content": "Моя сводка:\n" + summary + "\n\nЧто повторить в первую очередь?"},
    ]
