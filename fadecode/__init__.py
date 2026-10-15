import os
import time

from flask import Flask, jsonify, render_template, request

from . import config, db, filters


def create_app(test_config=None):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config.load_env(os.path.join(root, ".env"))

    app = Flask(__name__, instance_path=os.path.join(root, "instance"))
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.from_mapping(config.default_config(app.instance_path))
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    filters.init_app(app)

    from . import api, auth, views

    app.register_blueprint(auth.bp)
    app.register_blueprint(views.bp)
    app.register_blueprint(api.bp, url_prefix="/api")

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify(error="Не найдено"), 404
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        if request.path.startswith("/api/"):
            return jsonify(error="Слишком большой запрос"), 413
        return "Слишком большой запрос", 413

    def db_unavailable(e):
        """Neon просыпается или соединение оборвалось: честный 503 вместо голого 500."""
        app.logger.warning("БД недоступна: %s", type(e).__name__)
        msg = "База данных просыпается. Повтори через пару секунд."
        if request.path.startswith("/api/"):
            resp = jsonify(error=msg)
        else:
            resp = app.response_class(
                '<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="3">'
                '<body style="font:16px system-ui;background:#0d100e;color:#e8eee6;padding:48px">'
                "<h2>" + msg + "</h2><p>Страница обновится сама.</p></body>",
                mimetype="text/html",
            )
        resp.status_code = 503
        resp.headers["Retry-After"] = "3"
        return resp

    try:
        from psycopg import OperationalError
        from psycopg_pool import PoolTimeout
    except ImportError:  # psycopg нужен только для Postgres
        pass
    else:
        app.register_error_handler(OperationalError, db_unavailable)
        app.register_error_handler(PoolTimeout, db_unavailable)

    @app.get("/healthz")
    def healthz():
        """Пинг для n8n/аптайм-мониторов: будит и бэк (Render), и базу (Neon).

        200 {"status":"ok"} если приложение живо и SELECT 1 прошёл; иначе 503.
        Без авторизации, без куки, ничего секретного не отдаёт.
        """
        t0 = time.monotonic()
        err = None
        for attempt in range(2):  # Neon может просыпаться: одна повторная попытка
            try:
                db.get_db().execute("SELECT 1").fetchone()
                err = None
                break
            except Exception as e:  # noqa: BLE001 - здесь важен любой отказ базы
                err = type(e).__name__
                try:
                    db.get_db().rollback()
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(1.5)
        body = {
            "status": "ok" if err is None else "db_down",
            "db": "postgres" if db.use_postgres() else "sqlite",
            "ms": int((time.monotonic() - t0) * 1000),
        }
        if err:
            app.logger.warning("healthz: БД не ответила: %s", err)
        resp = jsonify(body)
        resp.status_code = 200 if err is None else 503
        resp.headers["Cache-Control"] = "no-store"
        return resp

    return app
