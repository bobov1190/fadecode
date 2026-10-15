import json
import os
import re
import secrets
import tempfile
import time
import unittest
from unittest import mock

from fadecode import ai, content, core, create_app, db

LID = "linreg"


def csrf(client):
    with client.session_transaction() as s:
        return s.get("csrf")


class AppCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cfg = {
            "TESTING": True,
            "DATABASE": os.path.join(self.tmp.name, "t.db"),
            "DATABASE_URL": "",  # тесты никогда не трогают боевую базу из .env
            "DATABASE_SCHEMA": "",
            "OPENROUTER_API_KEY": "",
        }
        pg = os.environ.get("TEST_DATABASE_URL", "").strip()
        if pg:  # прогон на Postgres: своя временная схема на каждый тест
            cfg["DATABASE_URL"] = pg.replace("-pooler", "")  # SET search_path не дружит с pgbouncer
            cfg["DATABASE_SCHEMA"] = "t_" + secrets.token_hex(6)
        self.app = create_app(cfg)
        self.c = self.app.test_client()

    def tearDown(self):
        db.shutdown(self.app, drop_schema=True)
        self.tmp.cleanup()

    def register(self, name="alice", pw="secret1"):
        self.c.get("/register")
        return self.c.post("/register", data={"username": name, "password": pw, "csrf_token": csrf(self.c)})

    def post(self, path, **data):
        return self.c.post(path, json=data, headers={"X-CSRF-Token": csrf(self.c)})

    def form(self, path, **data):
        return self.c.post(path, data=dict(data, csrf_token=csrf(self.c)))

    def login_ready(self):
        self.assertEqual(self.register().status_code, 302)
        self.c.get("/")

    def srs(self, name="alice"):
        with self.app.app_context():
            return db.srs_all(db.get_user_by_name(name)["id"])

    def block(self, lid=LID, bid=None):
        L = content.BY_ID[lid]
        bid = bid or content.order_ids(L, "small")[0]
        return L, bid, content.slot_target(L, bid)

    def check(self, value, bid=None, **extra):
        L, bid, _ = self.block(bid=bid)
        return self.post("/api/check", lesson=L["id"], block=bid, value=value, attempts=1, hints=0, ms=1000, **extra)


# ---------- ядро: токены, подсветка, сравнение ----------

class CoreTests(unittest.TestCase):
    def test_tokenize_roundtrip_all_lessons(self):
        for L in content.LESSONS:
            code = content.full_code(L)
            self.assertEqual("".join(t.v for t in core.tokenize(code)), code, L["id"])

    def test_highlight_escapes_html(self):
        h = str(core.highlight("a < b and '<script>'"))
        self.assertIn("&lt;", h)
        self.assertNotIn("<script>", h)

    def test_statuses(self):
        target = "def f(self, X):\n    total = X.sum()\n    return total / len(X)"
        self.assertEqual(core.compare_code(target, target)["status"], "perfect")
        self.assertEqual(core.compare_code(target, "")["status"], "empty")
        spaced = "def f(self,X):\n  total=X.sum()\n  return total/len(X)"
        self.assertEqual(core.compare_code(target, spaced)["status"], "perfect")
        renamed = target.replace("total", "s")
        self.assertEqual(core.compare_code(target, renamed)["status"], "renamed")
        no_len = "def f(self, X):\n    total = X.sum()\n    return total / X"
        self.assertEqual(core.compare_code(target, no_len)["status"], "close")
        self.assertEqual(core.compare_code(target, "pass")["status"], "wrong")

    def test_renaming_def_params_is_not_allowed(self):
        target = "def f(self, X):\n    return X.sum()"
        self.assertNotEqual(core.compare_code(target, "def f(self, A):\n    return A.sum()")["status"], "renamed")

    def test_biggest_lesson_whole_class_is_fast(self):
        L = max(content.LESSONS, key=lambda l: len(content.class_body(l)))
        target = content.class_body(L)
        wrong = target.replace("np.", "numpy.", 3)
        t = time.time()
        r = core.compare_code(target, wrong)
        self.assertLess(time.time() - t, 3)
        self.assertIn(r["status"], ("close", "wrong"))

    def test_content_is_consistent(self):
        for L in content.LESSONS:
            ids = [b["id"] for b in L["blocks"]]
            self.assertEqual(len(ids), len(set(ids)), L["id"])
            for b in L["blocks"]:
                why = b.get("why")
                if why:
                    self.assertTrue(0 <= why["ok"] < len(why["opts"]), (L["id"], b["id"]))


# ---------- страницы ----------

class PageTests(AppCase):
    def test_anonymous_is_redirected_but_landing_is_public(self):
        r = self.c.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])
        landing = self.c.get("/about")
        self.assertEqual(landing.status_code, 200)
        self.assertIn("/static/logo-dark.svg", landing.get_data(as_text=True))
        self.assertEqual(self.c.get("/static/css/style.css").status_code, 200)

    def test_register_login_logout(self):
        self.assertEqual(self.register().status_code, 302)
        home = self.c.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn("ML алгоритмы", home.get_data(as_text=True))
        self.form("/logout")
        self.assertEqual(self.c.get("/").status_code, 302)
        self.c.get("/login")
        bad = self.form("/login", username="alice", password="nope")
        self.assertIn("Неверный логин", bad.get_data(as_text=True))
        ok = self.form("/login", username="ALICE", password="secret1")
        self.assertEqual(ok.status_code, 302)
        self.assertEqual(self.c.get("/").status_code, 200)

    def test_register_validation(self):
        self.c.get("/register")
        short = self.form("/register", username="al", password="secret1")
        self.assertIn("Логин", short.get_data(as_text=True))
        weak = self.form("/register", username="alice", password="123")
        self.assertIn("6 символов", weak.get_data(as_text=True))
        self.assertEqual(self.form("/register", username="alice", password="secret1").status_code, 302)
        self.c.get("/")
        self.form("/logout")
        self.c.get("/register")
        dup = self.form("/register", username="Alice", password="secret1")
        self.assertIn("занят", dup.get_data(as_text=True))

    def test_open_redirect_is_blocked(self):
        self.register()
        self.c.get("/")
        self.form("/logout")
        self.c.get("/login")
        r = self.form("/login", username="alice", password="secret1", next="//evil.example")
        self.assertEqual(r.headers["Location"], "/")

    def test_all_lesson_pages_render(self):
        self.login_ready()
        self.assertEqual(self.c.get("/pack/ml").status_code, 200)
        self.assertEqual(self.c.get("/pack/nope").status_code, 404)
        for L in content.LESSONS:
            lid, N = L["id"], len(L["blocks"])
            self.assertEqual(self.c.get("/lesson/" + lid).status_code, 200, lid)
            self.assertEqual(self.c.get("/lesson/%s/copy" % lid).status_code, 200, lid)
            for r in range(1, N + 2):
                page = self.c.get("/lesson/%s/recall?round=%d" % (lid, r))
                self.assertEqual(page.status_code, 200, (lid, r))
                html = page.get_data(as_text=True)
                self.assertEqual(len(re.findall(r'class="slot(?: whole)?"', html)), 1 if r > N else r, (lid, r))
            self.assertEqual(self.c.get("/lesson/%s/done" % lid).status_code, 200, lid)
        self.assertEqual(self.c.get("/lesson/nope").status_code, 404)

    def test_recall_order_follows_setting(self):
        self.login_ready()
        L = content.BY_ID[LID]
        small = content.order_ids(L, "small")
        self.c.get("/lesson/" + LID)
        html = self.c.get("/lesson/%s/recall?round=1" % LID).get_data(as_text=True)
        self.assertIn('data-block="%s"' % small[0], html)
        self.form("/settings", order="small", rounds="one", research="on")
        html = self.c.get("/lesson/%s/recall?round=2" % LID).get_data(as_text=True)
        self.assertEqual(len(re.findall(r'class="slot(?: whole)?"', html)), 1)
        self.assertIn('data-block="%s"' % small[1], html)

    def test_csrf_is_enforced(self):
        self.login_ready()
        r = self.c.post("/api/check", json={"lesson": LID, "block": "predict", "value": "x"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.c.post("/settings", data={"order": "random"}).status_code, 400)

    def test_api_requires_login(self):
        self.c.get("/login")
        r = self.post("/api/check", lesson=LID, block="predict", value="x")
        self.assertEqual(r.status_code, 401)

    def test_settings_export_reset(self):
        self.login_ready()
        self.form("/settings", order="random", rounds="all")  # research не отмечен -> журнал выключен
        self.assertTrue(self.check("pass").get_json()["status"] in ("wrong", "close"))
        data = json.loads(self.c.get("/export.json").get_data(as_text=True))
        self.assertEqual(data["log"], [])
        self.form("/settings", order="small", rounds="all", research="on")
        self.check("pass")
        data = json.loads(self.c.get("/export.json").get_data(as_text=True))
        self.assertTrue(any(e["type"] == "check" for e in data["log"]))
        _, bid, target = self.block()
        self.check(target)
        self.assertTrue(self.srs())
        self.form("/reset")
        self.assertEqual(self.srs(), {})


# ---------- проверка ответов ----------

class CheckTests(AppCase):
    def setUp(self):
        super().setUp()
        self.login_ready()

    def test_perfect_first_try_is_good_and_saved(self):
        L, bid, target = self.block()
        j = self.check(target).get_json()
        self.assertTrue(j["resolved"])
        self.assertEqual(j["grade"], "good")
        self.assertIn("с первого раза", j["html"])
        row = self.srs()["%s::%s" % (L["id"], bid)]
        self.assertEqual((row["box"], row["seen"], row["lapses"]), (1, 1, 0))
        self.assertGreater(row["due"], db.now_ms() + 20 * 3600 * 1000)

    def test_why_question_comes_with_resolution_and_hides_answer(self):
        _, _, target = self.block()
        j = self.check(target).get_json()
        self.assertIn('class="why"', j["why_html"])
        self.assertEqual(j["why_html"].count('class="opt"'), 3)
        self.assertNotIn("right", j["why_html"])

    def test_renamed_local_variable(self):
        L = content.BY_ID[LID]
        fit = content.find_block(L, "fit")["code"]
        defs = {t.line for t in core.tokenize(fit) if t.v == "def"}
        toks = core.tokenize(fit)
        name = None
        for i, t in enumerate(toks):
            if t.t == "id" and t.v not in core.PROTECTED and t.line not in defs and (i == 0 or toks[i - 1].v != "."):
                name = t.v
                break
        self.assertIsNotNone(name)
        value = "".join("renamed_var" if (t.t == "id" and t.v == name) else t.v for t in toks)
        j = self.check(value, bid="fit").get_json()
        self.assertTrue(j["resolved"])
        self.assertIn("названия переменных другие", j["html"])

    def test_close_then_accept_is_hard(self):
        L, bid, target = self.block(bid="fit")
        toks = core.sig(core.tokenize(target))
        t = toks[len(toks) // 2]
        value = target[:t.s] + target[t.e:]
        j = self.check(value, bid="fit").get_json()
        self.assertFalse(j["resolved"])
        self.assertEqual(j["status"], "close")
        self.assertIn("Почти", j["html"])
        self.assertIn('class="miss"', j["html"])  # сервер подсветил, чего не хватает
        acc = self.post("/api/accept", lesson=LID, block="fit", value=value, attempts=2, hints=0, ms=1).get_json()
        self.assertEqual(acc["grade"], "hard")
        self.assertEqual(self.srs()["%s::fit" % LID]["box"], 0)

    def test_accept_only_works_for_close(self):
        r = self.post("/api/accept", lesson=LID, block="fit", value="pass")
        self.assertEqual(r.status_code, 400)

    def test_wrong_and_empty(self):
        j = self.check("pass").get_json()
        self.assertEqual(j["status"], "wrong")
        self.assertFalse(j["resolved"])
        self.assertIn("Не совпало", j["html"])
        self.assertEqual(self.check("   ").get_json()["status"], "empty")
        self.assertEqual(self.srs(), {})

    def test_hint_clamps_and_reveal_resets_box(self):
        L, bid, target = self.block()
        total = len(target.split("\n"))
        j = self.post("/api/hint", lesson=LID, block=bid, n=2).get_json()
        self.assertEqual((j["n"], j["total"]), (min(2, total), total))
        self.assertEqual(self.post("/api/hint", lesson=LID, block=bid, n=999).get_json()["n"], total)
        rev = self.post("/api/reveal", lesson=LID, block=bid, value="pass", attempts=3, hints=2, ms=5).get_json()
        self.assertEqual(rev["grade"], "again")
        self.assertTrue(rev["failed"])
        self.assertIn("Эталон", rev["html"])
        row = self.srs()["%s::%s" % (LID, bid)]
        self.assertEqual((row["box"], row["lapses"]), (0, 1))

    def test_why_answers(self):
        L, bid, _ = self.block(bid="init")
        ok = L["blocks"][0]["why"]["ok"]
        right = self.post("/api/why", lesson=LID, block="init", i=ok).get_json()
        self.assertTrue(right["right"])
        wrong = self.post("/api/why", lesson=LID, block="init", i=(ok + 1) % 3).get_json()
        self.assertFalse(wrong["right"])
        self.assertTrue(wrong["exp"])

    def test_bad_input(self):
        self.assertEqual(self.post("/api/check", lesson="nope", block="x", value="a").status_code, 404)
        self.assertEqual(self.post("/api/check", lesson=LID, block="nope", value="a").status_code, 404)
        long = "x" * (self.app.config["MAX_ANSWER_CHARS"] + 1)
        self.assertEqual(self.post("/api/check", lesson=LID, block="init", value=long).status_code, 413)

    def test_whole_class_has_no_srs(self):
        L = content.BY_ID[LID]
        target = content.class_body(L)
        j = self.post("/api/check", lesson=LID, block="whole", value=target, attempts=1, hints=0).get_json()
        self.assertTrue(j["resolved"])
        self.assertEqual(j["why_html"], "")
        self.assertEqual(self.srs(), {})

    def test_lesson_done_and_summary(self):
        self.c.get("/lesson/" + LID)
        _, bid, target = self.block()
        self.check(target)
        self.assertTrue(self.post("/api/lesson_done", lesson=LID).get_json()["ok"])
        page = self.c.get("/lesson/%s/done" % LID).get_data(as_text=True)
        self.assertIn("с первого раза", page)
        self.assertIn("пройдено 1", self.c.get("/").get_data(as_text=True))


# ---------- повторение ----------

class ReviewTests(AppCase):
    def setUp(self):
        super().setUp()
        self.login_ready()

    def test_review_flow(self):
        html = self.c.get("/review").get_data(as_text=True)
        self.assertIn("Пока нечего повторять", html)
        _, bid, _ = self.block()
        self.post("/api/reveal", lesson=LID, block=bid, value="", attempts=1, hints=0)  # again -> due через ~10 минут
        self.assertIn("Пока нечего повторять", self.c.get("/review").get_data(as_text=True))
        self.form("/review/all")
        html = self.c.get("/review").get_data(as_text=True)
        self.assertIn("1 из 1", html)
        self.assertIn('data-mode="review"', html)
        self.form("/review/next")
        self.assertIn("Готово", self.c.get("/review").get_data(as_text=True))

    def test_due_card_appears_after_time_passes(self):
        _, bid, _ = self.block()
        self.post("/api/reveal", lesson=LID, block=bid, value="", attempts=1, hints=0)
        with self.app.app_context():
            con = db.get_db()
            con.execute("UPDATE srs SET due = ?", (db.now_ms() - 1000,))
            con.commit()
        html = self.c.get("/review").get_data(as_text=True)
        self.assertIn("осталось 1", html)
        self.assertIn("badge", self.c.get("/").get_data(as_text=True))
        self.check(content.slot_target(content.BY_ID[LID], bid), bid=bid, mode="review")
        self.assertIn("Пока нечего повторять", self.c.get("/review").get_data(as_text=True))


# ---------- ИИ ----------

class AITests(AppCase):
    def setUp(self):
        super().setUp()
        self.login_ready()
        self.app.config["OPENROUTER_API_KEY"] = "test-key"

    def chat(self, message="как начать?", **extra):
        return self.post("/api/ai/chat", lesson=LID, message=message, **extra)

    def test_not_configured(self):
        self.app.config["OPENROUTER_API_KEY"] = ""
        r = self.chat()
        self.assertEqual(r.status_code, 503)
        self.assertIn("OPENROUTER_API_KEY", r.get_json()["error"])

    def test_chat_context_cache_and_quota(self):
        seen = []

        def fake(messages):
            seen.append(messages)
            return "Подумай про форму X."

        _, bid, target = self.block()
        with mock.patch.object(ai, "complete", side_effect=fake):
            r = self.chat(block=bid, attempt="return 42", missing=[bid]).get_json()
            self.assertEqual(r["text"], "Подумай про форму X.")
            self.assertFalse(r["cached"])
            system = seen[0][0]["content"]
            self.assertIn("return 42", system)
            self.assertIn(target, system)  # эталон есть только в системном промпте
            self.assertEqual(seen[0][-1], {"role": "user", "content": "как начать?"})
            again = self.chat(block=bid, attempt="return 42", missing=[bid]).get_json()
            self.assertTrue(again["cached"])
            self.assertEqual(len(seen), 1)
            self.assertEqual(again["left"], r["left"])

    def test_no_reference_without_focus_block(self):
        seen = []
        with mock.patch.object(ai, "complete", side_effect=lambda m: seen.append(m) or "ок"):
            self.chat()
        _, _, target = self.block()
        self.assertNotIn(target, seen[0][0]["content"])

    def test_daily_user_limit(self):
        self.app.config["AI_DAILY_USER"] = 1
        with mock.patch.object(ai, "complete", return_value="ответ"):
            self.assertEqual(self.chat("первый вопрос").status_code, 200)
            r = self.chat("второй вопрос")
        self.assertEqual(r.status_code, 429)
        self.assertIn("лимит", r.get_json()["error"])

    def test_leak_guard(self):
        _, bid, target = self.block()
        with mock.patch.object(ai, "complete", return_value="Вот решение:\n" + target):
            r = self.chat("дай ответ", block=bid).get_json()
        self.assertEqual(r["text"], ai.LEAK_MSG)

    def test_provider_failure_is_reported(self):
        with mock.patch.object(ai, "_post", side_effect=OSError("boom")):
            r = self.chat("вопрос")
        self.assertEqual(r.status_code, 502)
        self.assertIn("недоступен", r.get_json()["error"])

    def test_model_fallback(self):
        self.app.config["AI_MODELS"] = ["bad/model", "good/model"]
        calls = []

        def fake_post(payload, key, timeout):
            calls.append(payload["model"])
            if payload["model"] == "bad/model":
                raise OSError("down")
            return {"choices": [{"message": {"content": "ответ второй модели"}}]}

        with mock.patch.object(ai, "_post", side_effect=fake_post):
            r = self.chat("вопрос").get_json()
        self.assertEqual(calls, ["bad/model", "good/model"])
        self.assertEqual(r["text"], "ответ второй модели")

    def test_advice(self):
        r = self.post("/api/ai/advice")
        self.assertEqual(r.status_code, 400)
        _, bid, _ = self.block()
        self.post("/api/reveal", lesson=LID, block=bid, value="", attempts=1, hints=0)
        seen = []
        with mock.patch.object(ai, "complete", side_effect=lambda m: seen.append(m) or "1. Повтори predict"):
            j = self.post("/api/ai/advice").get_json()
        self.assertIn("Повтори", j["text"])
        self.assertIn("коробка 0", seen[0][1]["content"])


if __name__ == "__main__":
    unittest.main()


# ---------- healthz ----------

class HealthTests(AppCase):
    def test_ok_without_login(self):
        r = self.c.get("/healthz")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["status"], "ok")

    def test_503_when_db_down(self):
        with mock.patch("fadecode.time.sleep"), mock.patch.object(db, "get_db", side_effect=RuntimeError("boom")):
            r = self.c.get("/healthz")
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.get_json()["status"], "db_down")


# ---------- контент в БД ----------

class ContentDbTests(AppCase):
    @staticmethod
    def _json(name):
        with open(os.path.join(content._DATA, name), encoding="utf-8") as f:
            return json.load(f)

    def test_loaded_from_db_equals_json(self):
        self.assertEqual(content.LESSONS, self._json("lessons.json"))
        self.assertEqual(content.PACKS, self._json("packs.json"))

    def test_content_really_comes_from_db(self):
        with self.app.app_context():
            con = db.get_db()
            con.execute("UPDATE lessons SET title=? WHERE id=?", ("Новый заголовок", LID))
            con.commit()
            content.load(con)
        self.assertEqual(content.BY_ID[LID]["title"], "Новый заголовок")

    def test_seed_fills_only_empty_db(self):
        with self.app.app_context():
            con = db.get_db()
            self.assertFalse(content.seed_from_json(con))
            self.assertTrue(content.seed_from_json(con, force=True))
            con.commit()
            content.load(con)
        self.assertEqual(content.LESSONS, self._json("lessons.json"))


# ---------- JSON API v1 (для SPA) ----------

class V1Tests(AppCase):
    def api(self, method, path, token=None, **body):
        headers = {"Authorization": "Bearer " + token} if token else {}
        return self.c.open("/api/v1" + path, method=method, json=body or None, headers=headers)

    def signup(self, name="alice", pw="secret1"):
        r = self.api("POST", "/auth/register", username=name, password=pw)
        self.assertEqual(r.status_code, 201)
        return r.get_json()["token"]

    def test_auth_flow(self):
        tok = self.signup()
        me = self.api("GET", "/me", tok).get_json()
        self.assertEqual(me["user"]["username"], "alice")
        self.assertEqual(self.api("GET", "/me").status_code, 401)
        self.assertEqual(self.api("GET", "/me", "garbage").status_code, 401)
        self.assertEqual(self.api("POST", "/auth/register", username="alice", password="secret1").status_code, 409)
        self.assertEqual(self.api("POST", "/auth/register", username="bob", password="123").status_code, 400)
        self.assertEqual(self.api("POST", "/auth/login", username="alice", password="nope").status_code, 401)
        ok = self.api("POST", "/auth/login", username="ALICE", password="secret1")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(self.api("GET", "/me", ok.get_json()["token"]).status_code, 200)

    def test_token_dies_when_password_changes(self):
        tok = self.signup()
        with self.app.app_context():
            con = db.get_db()
            con.execute("UPDATE users SET pw_hash=? WHERE username=?", ("x" * 40 + "changed123", "alice"))
            con.commit()
        self.assertEqual(self.api("GET", "/me", tok).status_code, 401)

    def test_no_csrf_and_no_cookies_needed(self):
        tok = self.signup()
        r = self.api("POST", "/lesson_done", tok, lesson=LID)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("Set-Cookie", r.headers)

    def test_catalog(self):
        tok = self.signup()
        packs = self.api("GET", "/packs", tok).get_json()["packs"]
        self.assertEqual([p["id"] for p in packs], [p["id"] for p in content.PACKS])
        self.assertEqual(packs[0]["total"], len(content.PACKS[0]["items"]))
        pk = self.api("GET", "/packs/" + packs[0]["id"], tok).get_json()
        self.assertEqual(len(pk["items"]), len(content.PACKS[0]["items"]))
        self.assertEqual(self.api("GET", "/packs/nope", tok).status_code, 404)
        L = self.api("GET", "/lessons/" + LID, tok).get_json()
        self.assertEqual(L["code"], content.full_code(content.BY_ID[LID]))
        self.assertEqual(len(L["blocks"]), len(content.BY_ID[LID]["blocks"]))
        for b in L["blocks"]:
            self.assertEqual(set(b["why"]), {"q", "opts"})  # правильный ответ клиенту не уходит
        self.assertEqual(self.api("GET", "/lessons/nope", tok).status_code, 404)
        op = self.api("POST", "/lessons/%s/open" % LID, tok).get_json()
        self.assertEqual(sorted(op["order"]), sorted(b["id"] for b in content.BY_ID[LID]["blocks"]))

    def test_check_flow(self):
        tok = self.signup()
        L, bid, target = self.block()
        base = {"lesson": LID, "block": bid}
        self.assertEqual(self.api("POST", "/check", tok, value="  ", **base).get_json()["status"], "empty")
        bad = self.api("POST", "/check", tok, value="x = 1", **base).get_json()
        self.assertFalse(bad["resolved"])
        self.assertIn(bad["status"], ("wrong", "close"))
        self.assertIsInstance(bad["extra"], list)
        self.assertIsInstance(bad["ins"], list)
        hint = self.api("POST", "/hint", tok, n=2, **base).get_json()
        self.assertEqual(hint["lines"], target.split("\n")[:2])
        ok = self.api("POST", "/check", tok, value=target, attempts=1, hints=0, **base).get_json()
        self.assertTrue(ok["resolved"])
        self.assertEqual((ok["how"], ok["grade"], ok["failed"]), ("ok", "good", False))
        self.assertIn("%s::%s" % (LID, bid), self.srs())
        rv = self.api("POST", "/reveal", tok, value="x", **base).get_json()
        self.assertEqual((rv["target"], rv["failed"]), (target, True))
        self.assertEqual(self.api("POST", "/check", tok, value="x", lesson="nope", block=bid).status_code, 404)

    def test_why_review_stats_done(self):
        tok = self.signup()
        L, bid, target = self.block()
        b = content.find_block(L, bid)
        w = self.api("POST", "/why", tok, lesson=LID, block=bid, i=b["why"]["ok"]).get_json()
        self.assertTrue(w["right"])
        self.api("POST", "/check", tok, value=target, lesson=LID, block=bid)
        rv = self.api("GET", "/review?all=1", tok).get_json()
        self.assertEqual([(i["lesson"], i["block"]) for i in rv["items"]], [(LID, bid)])
        self.assertTrue(rv["has_cards"])
        done = self.api("POST", "/lesson_done", tok, lesson=LID).get_json()
        self.assertTrue(done["ok"])
        self.assertEqual(done["next"]["id"], content.PACKS[0]["items"][1]["lesson"])
        st = self.api("GET", "/stats", tok).get_json()
        self.assertEqual(len(st["rows"]), len(content.LESSONS))
        self.assertEqual(st["cards"]["done"], 1)
        self.assertEqual(st["cards"]["accuracy"], 100)

    def test_settings_reset_export(self):
        tok = self.signup()
        s = self.api("PUT", "/settings", tok, order="random", rounds="one", research=False).get_json()["settings"]
        self.assertEqual((s["order"], s["rounds"], s["research"]), ("random", "one", False))
        s = self.api("PUT", "/settings", tok, order="zzz").get_json()["settings"]
        self.assertEqual(s["order"], "small")
        self.api("POST", "/lesson_done", tok, lesson=LID)
        self.assertEqual(list(self.api("GET", "/export", tok).get_json()["done"]), [LID])
        self.assertTrue(self.api("POST", "/reset", tok).get_json()["ok"])
        self.assertEqual(self.api("GET", "/export", tok).get_json()["done"], {})

    def test_cors(self):
        origin = "http://localhost:5173"
        pre = self.c.options("/api/v1/me", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
        self.assertEqual(pre.headers.get("Access-Control-Allow-Origin"), origin)
        self.assertIn("Authorization", pre.headers.get("Access-Control-Allow-Headers", ""))
        evil = self.c.get("/api/v1/me", headers={"Origin": "https://evil.example"})
        self.assertEqual(evil.status_code, 401)
        self.assertNotIn("Access-Control-Allow-Origin", evil.headers)
        denied = self.c.get("/api/v1/me", headers={"Origin": origin})
        self.assertEqual(denied.headers.get("Access-Control-Allow-Origin"), origin)  # заголовок есть и у ответа 401


# ---------- algorithms ----------

class AlgoTests(AppCase):
    def api(self, method, path, token=None, **body):
        headers = {"Authorization": "Bearer " + token} if token else {}
        return self.c.open("/api/v1" + path, method=method, json=body or None, headers=headers)

    def signup(self, name="alice"):
        r = self.api("POST", "/auth/register", username=name, password="secret1")
        self.assertEqual(r.status_code, 201)
        return r.get_json()["token"]

    def test_db_matches_json(self):
        path = os.path.join(os.path.dirname(content.__file__), "data", "algos.json")
        data = json.load(open(path, encoding="utf-8"))
        from fadecode import algos
        self.assertEqual([a["id"] for a in algos.ALGOS], [a["id"] for a in data])
        for a, b in zip(algos.ALGOS, data):
            self.assertEqual([p["id"] for p in a["problems"]], [p["id"] for p in b["problems"]])
            self.assertEqual(a["problems"][0]["reference"], b["problems"][0]["reference"])
            self.assertEqual(a["template"], b["template"])

    def test_requires_login(self):
        self.assertEqual(self.api("GET", "/algos/bsearch").status_code, 401)
        self.assertEqual(self.api("GET", "/problems/bs_704").status_code, 401)

    def test_overview_and_pack(self):
        tok = self.signup()
        a = self.api("GET", "/algos/bsearch", tok).get_json()
        self.assertEqual(a["template"]["id"], "bs_template")
        self.assertFalse(a["template"]["done"])
        self.assertEqual(len(a["problems"]), 10)
        self.assertTrue(all(p["status"] == "new" for p in a["problems"]))
        self.assertIsNone(a["resume"])
        self.assertEqual(self.api("GET", "/algos/nope", tok).status_code, 404)
        pk = self.api("GET", "/packs/algo", tok).get_json()
        self.assertEqual([x["id"] for x in pk["algos"]], ["bsearch", "twoptr"])
        self.assertEqual(pk["items"], [])
        packs = {p["id"]: p for p in self.api("GET", "/packs", tok).get_json()["packs"]}
        self.assertEqual(packs["algo"]["total"], 2)
        L = self.api("GET", "/lessons/bs_template", tok).get_json()
        self.assertEqual(L["algo"], {"id": "bsearch", "title": a["title"], "role": "template"})
        self.assertIsNone(self.api("GET", "/lessons/" + LID, tok).get_json()["algo"])

    def test_problem_flow(self):
        tok = self.signup()
        p = self.api("GET", "/problems/bs_704", tok).get_json()
        self.assertNotIn("reference", p)
        self.assertNotIn("solution", p)
        self.assertEqual(p["hints"], [])
        self.assertEqual(p["hints_total"], 2)
        self.assertEqual(p["status"], "new")
        self.assertTrue(p["tests"] and p["starter"])
        self.assertIsNone(p["prev"])
        self.assertEqual(self.api("PUT", "/problems/bs_704/draft", tok, code="x = 1").status_code, 200)
        p = self.api("GET", "/problems/bs_704", tok).get_json()
        self.assertEqual(p["draft"], "x = 1")
        self.assertEqual(p["status"], "open")
        h = self.api("POST", "/problems/bs_704/hint", tok, n=1).get_json()
        self.assertEqual(len(h["hints"]), 1)
        self.api("POST", "/problems/bs_704/hint", tok, n=2)
        self.assertEqual(len(self.api("GET", "/problems/bs_704", tok).get_json()["hints"]), 2)
        self.assertEqual(self.api("POST", "/problems/bs_704/result", tok, status="boom").status_code, 400)
        r = self.api("POST", "/problems/bs_704/result", tok, status="fail").get_json()
        self.assertEqual((r["solved"], r["attempts"]), (False, 1))
        r = self.api("POST", "/problems/bs_704/result", tok, status="ok").get_json()
        self.assertEqual((r["solved"], r["attempts"]), (True, 2))
        s = self.api("POST", "/problems/bs_704/solution", tok).get_json()
        self.assertEqual(s["status"], "solved")
        self.assertTrue(s["reference"] and s["insight"])
        s2 = self.api("POST", "/problems/bs_35/solution", tok).get_json()
        self.assertEqual(s2["status"], "given_up")
        rows = {x["id"]: x["status"] for x in self.api("GET", "/algos/bsearch", tok).get_json()["problems"]}
        self.assertEqual((rows["bs_704"], rows["bs_35"], rows["bs_278"]), ("solved", "given_up", "new"))
        self.assertEqual(self.api("GET", "/problems/nope", tok).status_code, 404)
        self.api("POST", "/reset", tok)
        self.assertEqual(self.api("GET", "/problems/bs_704", tok).get_json()["status"], "new")

    def test_resume_state(self):
        tok = self.signup()
        self.assertEqual(self.api("PUT", "/algos/bsearch/state", tok, stage="lesson-copy", ref="bs_template").status_code, 200)
        self.assertEqual(self.api("GET", "/algos/bsearch", tok).get_json()["resume"], {"stage": "lesson-copy", "ref": "bs_template"})
        self.assertEqual(self.api("PUT", "/algos/bsearch/state", tok, stage="nope", ref="x").status_code, 400)
        self.assertEqual(self.api("PUT", "/algos/bsearch/state", tok, stage="lesson-read", ref="tp_template").status_code, 400)
        self.assertEqual(self.api("PUT", "/algos/bsearch/state", tok, stage="problem", ref="tp_283").status_code, 400)
        self.api("PUT", "/problems/bs_35/draft", tok, code="pass")
        self.assertEqual(self.api("GET", "/algos/bsearch", tok).get_json()["resume"], {"stage": "problem", "ref": "bs_35"})

    def test_ai_problem(self):
        tok = self.signup()
        self.assertEqual(self.api("POST", "/ai/problem", tok, problem="bs_704", message="помоги").status_code, 503)
        self.assertEqual(self.api("POST", "/ai/problem", tok, problem="bs_704", message="").status_code, 400)
        self.assertEqual(self.api("POST", "/ai/problem", tok, problem="nope", message="a").status_code, 404)
        from fadecode import algos
        msgs = ai.problem_messages(algos.PROBLEMS["bs_704"], "code", "err", [], "вопрос")
        self.assertIn("code", msgs[0]["content"])
        self.assertIn(algos.PROBLEMS["bs_704"]["reference"], msgs[0]["content"])
