"""Помощники для Jinja-шаблонов: фильтры и глобальные функции."""
import time

from . import content, core

_MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября",
           "ноября", "декабря"]


def ru_date(ms):
    t = time.localtime(ms / 1000)
    return "%d %s, %02d:%02d" % (t.tm_mday, _MONTHS[t.tm_mon - 1], t.tm_hour, t.tm_min)


def init_app(app):
    env = app.jinja_env
    env.filters["highlight"] = core.highlight
    env.filters["ru_date"] = ru_date
    env.globals.update(
        indent=content.indent,
        full_code=content.full_code,
        nlines=content.nlines,
        slot_rows=content.slot_rows,
    )
