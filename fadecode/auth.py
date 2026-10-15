"""Аккаунты: регистрация, вход, выход, CSRF-защита и декоратор login_required."""
import functools
import hmac
import re
import secrets
import time

from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from . import db

bp = Blueprint("auth", __name__)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,32}$")
HASH_METHOD = "pbkdf2:sha256"
_fails = {}  # ip -> [время неудачных входов]


def csrf_token():
    token = session.get("csrf")
    if not token:
        token = session["csrf"] = secrets.token_hex(16)
    return token


def _is_api():
    return request.path.startswith("/api/")


@bp.before_app_request
def load_user():
    uid = session.get("uid")
    g.user = db.get_user(uid) if uid else None
    if uid and g.user is None:
        session.pop("uid", None)
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        expected = session.get("csrf") or ""
        sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
        if not expected or not hmac.compare_digest(sent.encode("utf-8"), expected.encode("utf-8")):
            if _is_api():
                return jsonify(error="Сессия устарела, обнови страницу."), 400
            return "Ошибка защиты формы (CSRF). Вернись назад и обнови страницу.", 400


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            if _is_api():
                return jsonify(error="Нужно войти."), 401
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped


def _safe_next(target):
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return None


def _blocked(ip):
    now = time.time()
    fails = [t for t in _fails.get(ip, []) if now - t < 600]
    _fails[ip] = fails
    return len(fails) >= 8


def _start_session(uid):
    session.clear()
    session["uid"] = uid
    session.permanent = True


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("views.home"))
    nxt = _safe_next(request.values.get("next"))
    if request.method == "POST":
        ip = request.remote_addr or "?"
        if _blocked(ip):
            flash("Слишком много неудачных попыток. Подожди несколько минут.", "bad")
            return render_template("auth.html", mode="login", next=nxt), 429
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.get_user_by_name(username)
        if user and check_password_hash(user["pw_hash"], password):
            _fails.pop(ip, None)
            _start_session(user["id"])
            return redirect(nxt or url_for("views.home"))
        _fails.setdefault(ip, []).append(time.time())
        flash("Неверный логин или пароль.", "bad")
    return render_template("auth.html", mode="login", next=nxt)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("views.home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        error = None
        if not USERNAME_RE.match(username):
            error = "Логин: 3–32 символа, только латиница, цифры и _ . -"
        elif len(password) < 6:
            error = "Пароль должен быть не короче 6 символов."
        elif len(password) > 200:
            error = "Пароль слишком длинный."
        if not error:
            uid = db.create_user(username, generate_password_hash(password, method=HASH_METHOD))
            if uid is None:
                error = "Такой логин уже занят."
            else:
                _start_session(uid)
                flash("Аккаунт создан. Добро пожаловать!", "ok")
                return redirect(url_for("views.home"))
        flash(error, "bad")
    return render_template("auth.html", mode="register", next=None)


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
