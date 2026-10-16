"""Тесты заданий с таймером и автоматическим баллом."""
import json
import unittest

from fadecode import content, db
from tests.test_app import AppCase

LID = "linreg"


class AssignTests(AppCase):
    def api(self, method, path, token=None, **body):
        headers = {"Authorization": "Bearer " + token} if token else {}
        return self.c.open("/api/v1" + path, method=method, json=body or None, headers=headers)

    def signup(self, login, pw="secret1", **extra):
        r = self.api("POST", "/auth/register", username=login, password=pw, **extra)
        self.assertEqual(r.status_code, 201)
        return r.get_json()["token"]

    def make_admin(self, name):
        with self.app.app_context():
            db.make_admin(db.get_user_by_name(name)["id"])

    def setup_task(self, lessons=(LID,), minutes=30, mx=100):
        self.signup("teacher")
        self.make_admin("teacher")
        tok = self.api("POST", "/auth/login", username="teacher", password="secret1").get_json()["token"]
        r = self.api("POST", "/admin/assign", tok, title="Тест", lessons=list(lessons), minutes=minutes, max_score=mx)
        self.assertEqual(r.status_code, 201)
        return tok, r.get_json()["id"]

    def solve(self, tok, lid, bid, wrong=0, hints=0):
        target = content.slot_target(content.BY_ID[lid], bid)
        base = {"lesson": lid, "block": bid}
        for _ in range(wrong):
            self.api("POST", "/check", tok, value="x = 1", **base)
        for n in range(1, hints + 1):
            self.api("POST", "/hint", tok, n=n, **base)
        r = self.api("POST", "/check", tok, value=target, **base)
        self.assertTrue(r.get_json()["resolved"])

    def solve_all(self, tok, lid, **kw):
        L = content.BY_ID[lid]
        self.api("POST", "/copy_done", tok, lesson=lid, errors=kw.pop("copy_errors", 0))
        for b in L["blocks"]:
            self.solve(tok, lid, b["id"])
        self.solve(tok, lid, "whole", **kw)

    def test_admin_only(self):
        self.signup("stud")
        tok = self.api("POST", "/auth/login", username="stud", password="secret1").get_json()["token"]
        self.assertEqual(self.api("GET", "/admin/assign", tok).status_code, 403)
        self.assertEqual(self.api("POST", "/admin/assign", tok, title="x", lessons=[LID], minutes=5).status_code, 403)

    def test_validation(self):
        adm, _ = self.setup_task()
        bad = lambda **kw: self.api("POST", "/admin/assign", adm, **dict(dict(title="t", lessons=[LID], minutes=10), **kw))
        self.assertEqual(bad(title=" ").status_code, 400)
        self.assertEqual(bad(lessons=["nope"]).status_code, 400)
        self.assertEqual(bad(minutes=0).status_code, 400)
        self.assertEqual(bad(minutes=9999).status_code, 400)
        self.assertEqual(bad(max_score=0).status_code, 400)

    def test_start_needs_name_and_perfect_score(self):
        adm, aid = self.setup_task(mx=100)
        tok = self.signup("stud")
        self.assertEqual(self.api("POST", "/assign/%s/start" % aid, tok).status_code, 400)
        r = self.api("POST", "/assign/%s/start" % aid, tok, name="Иван Петров")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["attempt"]["status"], "running")
        self.assertNotIn("score", r.get_json()["attempt"])  # пока идёт, балл не показываем
        self.assertEqual(self.api("GET", "/assign/active", tok).get_json()["active"]["id"], aid)
        self.solve_all(tok, LID)
        fin = self.api("POST", "/assign/%s/finish" % aid, tok).get_json()["attempt"]
        self.assertEqual(fin["status"], "finished")
        self.assertEqual(fin["score"], 100.0)
        self.assertIsNone(self.api("GET", "/assign/active", tok).get_json()["active"])

    def test_mistakes_lower_score(self):
        adm, aid = self.setup_task(mx=100)
        tok = self.signup("stud")
        self.api("POST", "/assign/%s/start" % aid, tok, name="Иван")
        self.solve_all(tok, LID, wrong=3, hints=2, copy_errors=10)
        fin = self.api("POST", "/assign/%s/finish" % aid, tok).get_json()["attempt"]
        self.assertLess(fin["score"], 100)
        self.assertGreater(fin["score"], 50)
        slot = [s for s in fin["breakdown"][0]["slots"] if s["id"] == "whole"][0]
        self.assertEqual((slot["wrong"], slot["hints"]), (3, 2))
        self.assertEqual(fin["breakdown"][0]["copy_errors"], 10)

    def test_reveal_and_skipped_give_zero(self):
        adm, aid = self.setup_task()
        tok = self.signup("stud")
        self.api("POST", "/assign/%s/start" % aid, tok, name="Иван")
        bid = content.BY_ID[LID]["blocks"][0]["id"]
        self.api("POST", "/reveal", tok, lesson=LID, block=bid, value="")
        fin = self.api("POST", "/assign/%s/finish" % aid, tok).get_json()["attempt"]
        self.assertEqual(fin["score"], 0.0)
        s = [x for x in fin["breakdown"][0]["slots"] if x["id"] == bid][0]
        self.assertTrue(s["revealed"])

    def test_timer_expires_and_blocks_scoring(self):
        adm, aid = self.setup_task(minutes=10)
        tok = self.signup("stud")
        self.api("POST", "/assign/%s/start" % aid, tok, name="Иван")
        bid = content.BY_ID[LID]["blocks"][0]["id"]
        self.solve(tok, LID, bid)  # засчитается
        with self.app.app_context():  # «прошло 11 минут», выход из страницы таймер не останавливал
            con = db.get_db()
            con.execute("UPDATE assign_attempts SET started=started-?", (11 * 60000,))
            con.execute("UPDATE assign_log SET t=t-?", (11 * 60000,))
            con.commit()
        self.assertIsNone(self.api("GET", "/assign/active", tok).get_json()["active"])
        other = content.BY_ID[LID]["blocks"][1]["id"]
        self.solve(tok, LID, other)  # после дедлайна не засчитывается
        st = self.api("GET", "/assign/%s" % aid, tok).get_json()["attempt"]
        self.assertEqual(st["status"], "finished")
        self.assertEqual(st["spent_sec"], 600)
        slots = {s["id"]: s for s in st["breakdown"][0]["slots"]}
        self.assertTrue(slots[bid]["solved"])
        self.assertFalse(slots[other]["solved"])

    def test_other_lessons_do_not_count(self):
        adm, aid = self.setup_task(lessons=("logreg",))
        tok = self.signup("stud")
        self.api("POST", "/assign/%s/start" % aid, tok, name="Иван")
        self.solve(tok, LID, content.BY_ID[LID]["blocks"][0]["id"])
        with self.app.app_context():
            n = db.get_db().execute("SELECT COUNT(*) AS n FROM assign_log").fetchone()["n"]
        self.assertEqual(n, 0)

    def test_admin_results_and_reset(self):
        adm, aid = self.setup_task()
        tok = self.signup("stud", name="Анна Иванова")
        self.api("POST", "/assign/%s/start" % aid, tok)
        self.api("POST", "/assign/%s/finish" % aid, tok)
        r = self.api("GET", "/admin/assign/" + aid, adm).get_json()
        self.assertEqual(len(r["results"]), 1)
        self.assertEqual(r["results"][0]["name"], "Анна Иванова")
        self.assertEqual(r["results"][0]["username"], "stud")
        lst = self.api("GET", "/admin/assign", adm).get_json()
        self.assertEqual((lst["items"][0]["started"], lst["items"][0]["finished"]), (1, 1))
        self.assertTrue(lst["catalog"])
        uid = r["results"][0]["user_id"]
        self.assertEqual(self.api("DELETE", "/admin/assign/%s/attempt/%d" % (aid, uid), adm).status_code, 200)
        self.assertEqual(self.api("GET", "/admin/assign/" + aid, adm).get_json()["results"], [])
        self.assertEqual(self.api("DELETE", "/admin/assign/" + aid, adm).status_code, 200)
        self.assertEqual(self.api("GET", "/assign/" + aid, tok).status_code, 404)

    def test_one_running_at_a_time(self):
        adm, aid = self.setup_task()
        r = self.api("POST", "/admin/assign", adm, title="Второе", lessons=["logreg"], minutes=20)
        aid2 = r.get_json()["id"]
        tok = self.signup("stud")
        self.api("POST", "/assign/%s/start" % aid, tok, name="Иван")
        self.assertEqual(self.api("POST", "/assign/%s/start" % aid2, tok).status_code, 409)


if __name__ == "__main__":
    unittest.main()
