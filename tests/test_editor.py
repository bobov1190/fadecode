import unittest

from fadecode import algos, content, db

from tests.test_app import AppCase, LID

METHOD = "def hello(self):\n    return 1"
INIT = "def __init__(self):\n    self.x = 0"


def lesson_body(**kw):
    d = {
        "title": "Мой класс", "tag": "тест", "desc": "Описание", "task": "Сделай класс", "imports": "import math",
        "cls": "class Box:", "change": "",
        "blocks": [
            {"name": "__init__", "note": "Старт", "code": INIT, "why": {"q": "", "opts": [], "ok": 0, "exp": ""}},
            {"name": "hello", "note": "Привет", "code": METHOD,
             "why": {"q": "Почему?", "opts": ["А", "Б"], "ok": 1, "exp": "Потому что Б"}},
        ],
    }
    d.update(kw)
    return d


class EditorTests(AppCase):
    def api(self, method, path, token=None, **body):
        headers = {"Authorization": "Bearer " + token} if token else {}
        return self.c.open("/api/v1" + path, method=method, json=body or None, headers=headers)

    def signup(self, name="alice"):
        r = self.api("POST", "/auth/register", username=name, password="secret1")
        self.assertEqual(r.status_code, 201)
        return r.get_json()["token"], r.get_json()["user"]["id"]

    def admin(self, name="boss"):
        tok, uid = self.signup(name)
        with self.app.app_context():
            db.make_admin(uid)
        return tok

    def test_only_admin(self):
        tok, _ = self.signup()
        self.assertEqual(self.api("GET", "/admin/content", tok).status_code, 403)
        self.assertEqual(self.api("POST", "/admin/lessons", tok, **lesson_body()).status_code, 403)
        self.assertEqual(self.api("POST", "/admin/packs", tok, title="x").status_code, 403)
        self.assertEqual(self.api("GET", "/admin/content").status_code, 401)

    def test_existing_content_has_author_bahodir(self):
        tok, _ = self.signup()
        packs = self.api("GET", "/packs", tok).get_json()["packs"]
        self.assertTrue(packs and all(p["author"] == "Bahodir" for p in packs))
        self.assertEqual(self.api("GET", "/lessons/" + LID, tok).get_json()["author"], "Bahodir")
        self.assertEqual(self.api("GET", "/packs/" + packs[0]["id"], tok).get_json()["author"], "Bahodir")

    def test_create_lesson_in_new_pack_and_learn_it(self):
        adm = self.admin()
        pid = self.api("POST", "/admin/packs", adm, title="Мой пак", desc="d", items=[]).get_json()["id"]
        r = self.api("POST", "/admin/lessons", adm, pack=pid, **lesson_body())
        self.assertEqual(r.status_code, 201)
        L = r.get_json()["lesson"]
        self.assertEqual(L["author"], "boss")  # автор новой карточки: тот, кто её создал
        self.assertEqual([b["id"] for b in L["blocks"]], ["init", "hello"])
        # карточка сразу видна ученику в уроках
        tok, _ = self.signup("bob")
        pk = self.api("GET", "/packs/" + pid, tok).get_json()
        self.assertEqual(pk["author"], "boss")
        self.assertEqual([i["lesson"] for i in pk["items"]], [L["id"]])
        les = self.api("GET", "/lessons/" + L["id"], tok).get_json()
        self.assertEqual(les["author"], "boss")
        self.assertEqual(set(les["blocks"][1]["why"]), {"q", "opts"})  # верный ответ ученику не отдаём
        # и проверяется как обычный урок
        ok = self.api("POST", "/check", tok, lesson=L["id"], block="hello", value=METHOD).get_json()
        self.assertTrue(ok["resolved"])
        why = self.api("POST", "/why", tok, lesson=L["id"], block="hello", i=1).get_json()
        self.assertTrue(why["right"])
        # у метода без вопроса нет блока «зачем так»
        self.assertEqual(les["blocks"][0]["why"]["opts"], [])

    def test_validation(self):
        adm = self.admin()
        bad = lambda **kw: self.api("POST", "/admin/lessons", adm, **lesson_body(**kw)).status_code
        self.assertEqual(bad(title="  "), 400)
        self.assertEqual(bad(cls="Box"), 400)
        self.assertEqual(bad(blocks=[]), 400)
        self.assertEqual(bad(blocks=[{"name": "m", "code": "def (:"}]), 400)
        self.assertEqual(bad(blocks=[{"name": "m", "code": METHOD, "id": "whole"}]), 400)
        self.assertEqual(bad(blocks=[{"name": "m", "code": METHOD, "id": "A b"}]), 400)
        self.assertEqual(bad(blocks=[{"name": "a", "code": METHOD, "id": "x"}, {"name": "b", "code": METHOD, "id": "x"}]), 400)
        self.assertEqual(bad(blocks=[{"name": "m", "code": METHOD, "why": {"q": "?", "opts": ["один"], "ok": 0}}]), 400)
        self.assertEqual(bad(blocks=[{"name": "m", "code": METHOD, "why": {"q": "?", "opts": ["а", "б"], "ok": 5}}]), 400)
        self.assertEqual(bad(blocks=[{"name": "m", "code": METHOD, "why": {"q": "", "opts": ["а", "б"], "ok": 0}}]), 400)
        self.assertEqual(self.api("POST", "/admin/lessons", adm, pack="nope", **lesson_body()).status_code, 404)
        self.assertEqual(bad(), 201)

    def test_update_keeps_ids_and_progress(self):
        adm = self.admin()
        L = self.api("POST", "/admin/lessons", adm, **lesson_body()).get_json()["lesson"]
        lid = L["id"]
        tok, uid = self.signup("bob")
        self.api("POST", "/check", tok, lesson=lid, block="hello", value=METHOD)
        self.assertIn(lid + "::hello", self.srs("bob"))
        body = lesson_body(title="Новое имя", author="Другой", blocks=[
            {"id": "hello", "name": "hello", "code": "def hello(self):\n    return 2"},
            {"name": "hello", "code": METHOD},  # то же имя, id выдаётся уникальный
        ])
        r = self.api("PUT", "/admin/lessons/" + lid, adm, **body)
        self.assertEqual(r.status_code, 200)
        L2 = r.get_json()["lesson"]
        self.assertEqual((L2["title"], L2["author"]), ("Новое имя", "Другой"))
        self.assertEqual([b["id"] for b in L2["blocks"]], ["hello", "hello_2"])
        self.assertIn(lid + "::hello", self.srs("bob"))
        # пустой автор при правке не затирает прежнего
        r = self.api("PUT", "/admin/lessons/" + lid, adm, **dict(body, author=""))
        self.assertEqual(r.get_json()["lesson"]["author"], "Другой")
        self.assertEqual(self.api("PUT", "/admin/lessons/nope", adm, **body).status_code, 404)

    def test_existing_lesson_is_editable(self):
        adm = self.admin()
        L = self.api("GET", "/admin/lessons/" + LID, adm).get_json()["lesson"]
        self.assertEqual(L["author"], "Bahodir")
        self.assertIn("ok", L["blocks"][0]["why"])
        L["title"] = "Переименована"
        r = self.api("PUT", "/admin/lessons/" + LID, adm, **L)
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(content.BY_ID[LID]["title"], "Переименована")
        self.assertEqual(content.BY_ID[LID]["author"], "Bahodir")
        self.assertEqual(len(content.BY_ID[LID]["blocks"]), len(L["blocks"]))

    def test_all_seeded_lessons_pass_validation(self):
        adm = self.admin()
        for src in list(content.LESSONS):
            L = self.api("GET", "/admin/lessons/" + src["id"], adm).get_json()["lesson"]
            r = self.api("PUT", "/admin/lessons/" + src["id"], adm, **L)
            self.assertEqual(r.status_code, 200, (src["id"], r.get_json()))

    def test_delete_lesson(self):
        adm = self.admin()
        pid = self.api("POST", "/admin/packs", adm, title="П", items=[]).get_json()["id"]
        lid = self.api("POST", "/admin/lessons", adm, pack=pid, **lesson_body()).get_json()["lesson"]["id"]
        r = self.api("DELETE", "/admin/lessons/" + lid, adm)
        self.assertEqual(r.status_code, 409)
        self.assertIn("П", r.get_json()["error"])
        a = self.api("POST", "/admin/assign", adm, title="Зад", lessons=[lid], minutes=10, max_score=10)
        self.assertEqual(a.status_code, 201)
        self.api("PUT", "/admin/packs/" + pid, adm, title="П", items=[])
        r = self.api("DELETE", "/admin/lessons/" + lid, adm)
        self.assertEqual(r.status_code, 409)
        self.assertIn("Зад", r.get_json()["error"])
        aid = self.api("GET", "/admin/assign", adm).get_json()["items"][0]["id"]
        self.api("DELETE", "/admin/assign/" + aid, adm)
        self.assertEqual(self.api("DELETE", "/admin/lessons/" + lid, adm).status_code, 200)
        self.assertNotIn(lid, content.BY_ID)
        self.assertEqual(self.api("DELETE", "/admin/lessons/" + lid, adm).status_code, 404)

    def test_pack_edit_order_and_delete(self):
        adm = self.admin()
        before = [p["id"] for p in content.PACKS]
        pid = self.api("POST", "/admin/packs", adm, title="Новый", items=[
            {"name": "", "lesson": LID},
            {"name": "Скоро", "category": "x", "lesson": None},
        ]).get_json()["id"]
        p = content.get_pack(pid)
        self.assertEqual([it["name"] for it in p["items"]], [content.BY_ID[LID]["title"], "Скоро"])
        self.assertIsNone(p["items"][1]["lesson"])
        bad = lambda items: self.api("PUT", "/admin/packs/" + pid, adm, title="Новый", items=items).status_code
        self.assertEqual(bad([{"name": "a", "lesson": LID}, {"name": "b", "lesson": LID}]), 400)
        self.assertEqual(bad([{"name": "a", "lesson": "nope"}]), 400)
        self.assertEqual(bad([{"name": "", "lesson": None}]), 400)
        self.assertEqual(self.api("PUT", "/admin/packs/" + pid, adm, title="", items=[]).status_code, 400)
        # порядок паков
        order = [pid] + before
        self.assertEqual(self.api("PUT", "/admin/pack-order", adm, ids=order).status_code, 200)
        self.assertEqual([x["id"] for x in content.PACKS], order)
        self.assertEqual(self.api("PUT", "/admin/pack-order", adm, ids=before).status_code, 400)
        # удаление: пак с алгоритмами нельзя, обычный можно, карточки остаются
        self.assertTrue(any(a["pack"] == "algo" for a in algos.ALGOS))
        self.assertEqual(self.api("DELETE", "/admin/packs/algo", adm).status_code, 409)
        self.assertEqual(self.api("DELETE", "/admin/packs/" + pid, adm).status_code, 200)
        self.assertIsNone(content.get_pack(pid))
        self.assertIn(LID, content.BY_ID)
        self.assertEqual(self.api("DELETE", "/admin/packs/" + pid, adm).status_code, 404)

    def test_admin_content_listing(self):
        adm = self.admin()
        r = self.api("GET", "/admin/content", adm).get_json()
        self.assertEqual([p["id"] for p in r["packs"]], [p["id"] for p in content.PACKS])
        self.assertEqual(len(r["lessons"]), len(content.LESSONS))
        first = next(x for x in r["lessons"] if x["id"] == LID)
        self.assertTrue(first["packs"] and first["author"] == "Bahodir")

    def test_migration_adds_author_and_drops_desk(self):
        with self.app.app_context():
            con = db.get_db()
            con.execute("ALTER TABLE lessons DROP COLUMN author")
            con.execute("ALTER TABLE packs DROP COLUMN author")
            con.execute("CREATE TABLE desk_tasks (id TEXT PRIMARY KEY)")
            con.commit()
            db._migrate(con)
            con.commit()
            self.assertEqual(con.execute("SELECT author FROM lessons LIMIT 1").fetchone()["author"], "Bahodir")
            self.assertEqual(con.execute("SELECT author FROM packs LIMIT 1").fetchone()["author"], "Bahodir")
            with self.assertRaises(Exception):
                con.execute("SELECT 1 FROM desk_tasks")

    def test_create_admin_command(self):
        runner = self.app.test_cli_runner()
        res = runner.invoke(args=["create-admin", "--username", "bahodir", "--password", "secret12"])
        self.assertEqual(res.exit_code, 0, res.output)
        r = self.api("POST", "/auth/login", username="bahodir", password="secret12")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["user"]["is_admin"])
        again = runner.invoke(args=["create-admin", "--username", "bahodir", "--password", "other-pass"])
        self.assertEqual(again.exit_code, 0)
        self.assertEqual(self.api("POST", "/auth/login", username="bahodir", password="secret12").status_code, 200)
        bad = runner.invoke(args=["create-admin", "--username", "x", "--password", "secret12"])
        self.assertNotEqual(bad.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
