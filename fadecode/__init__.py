import os
import time

import click
from flask import Flask, g, jsonify, render_template, request

from . import config, content, db, filters


def create_app(test_config=None):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config.load_env(os.path.join(root, ".env"))

    app = Flask(__name__, instance_path=os.path.join(root, "instance"))
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.from_mapping(config.default_config(app.instance_path))
    if os.environ.get("RENDER") or os.environ.get("TRUST_PROXY") == "1":
        # За прокси Render настоящий IP клиента приходит в X-Forwarded-For (нужно для лимита попыток входа)
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    filters.init_app(app)

    from . import api, auth, v1, views

    spa = bool(app.config.get("SERVE_SPA", os.environ.get("SERVE_SPA") == "1"))
    if spa:
        # Всё в одном сервисе: Flask отдаёт собранный Vue (frontend/dist) и JSON API. Старый сайт на Jinja не подключается.
        spa_dir = app.config.get("SPA_DIR") or os.path.join(root, "frontend", "dist")

        @app.before_request
        def spa_user():
            # токен в заголовке Authorization; куки и CSRF в этом режиме не используются
            g.user = auth.user_from_token(request.headers.get("Authorization", "")) if request.path.startswith("/api/v1/") else None
    else:
        app.register_blueprint(auth.bp)
        app.register_blueprint(views.bp)
        app.register_blueprint(api.bp, url_prefix="/api")
    app.register_blueprint(v1.bp, url_prefix="/api/v1")

    @app.after_request
    def cors(resp):
        origin = request.headers.get("Origin")
        if request.path.startswith("/api/v1/") and origin and origin in app.config["CORS_ORIGINS"]:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
            resp.headers["Access-Control-Max-Age"] = "600"
            resp.headers.add("Vary", "Origin")
        return resp

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify(error="Не найдено"), 404
        if spa:
            return "Not found", 404
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

    if spa:
        from flask import abort, send_from_directory

        @app.get("/about")
        def spa_about():
            return send_from_directory(spa_dir, "landing.html", max_age=0)

        @app.get("/", defaults={"path": ""})
        @app.get("/<path:path>")
        def spa_page(path):
            if path.startswith("api/") or path.startswith("assets/") and not os.path.isfile(os.path.join(spa_dir, path)):
                abort(404)
            if path and os.path.isfile(os.path.join(spa_dir, path)):
                # файлы в assets/ имеют хеш в имени, их можно кэшировать надолго
                age = 31536000 if path.startswith("assets/") else 3600
                return send_from_directory(spa_dir, path, max_age=age)
            # любой другой адрес отдаёт index.html, дальше маршрутизирует Vue Router
            return send_from_directory(spa_dir, "index.html", max_age=0)

    @app.cli.command("seed")
    @click.option("--force", is_flag=True, help="заменить контент в БД содержимым data/*.json")
    def seed_cmd(force):
        """Заливает уроки и пакеты из data/*.json в БД (без --force только в пустую)."""
        con = db.get_db()
        wrote = content.seed_from_json(con, force=force)
        con.commit()
        content.load(con)
        if wrote:
            click.echo("Готово: %d уроков, %d пакетов." % (len(content.LESSONS), len(content.PACKS)))
        else:
            click.echo("В базе уже есть контент. Чтобы перезаписать его из JSON: flask --app run seed --force")

    return app
