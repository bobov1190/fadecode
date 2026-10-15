import os

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

    return app
