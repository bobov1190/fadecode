import json
import os
import unittest
from unittest import mock

from fadecode import aimakerp, algoeditor, algos, content

from tests import test_editor as _te
from tests.test_app import AppCase

PRELUDE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "src", "lib", "prelude.py")
FORM = {"idea": "Лучшее время для покупки акций", "topic": "Скользящее окно", "level": "easy", "fn": "maxProfit"}
EX = aimakerp.EXAMPLE


def run_prelude(code, pre, tests, cls="Solution"):
    """То же, что делает браузер: fc_run из frontend/src/lib/prelude.py."""
    ns = {"__name__": "prelude"}
    with open(PRELUDE, encoding="utf-8") as f:
        exec(compile(f.read(), PRELUDE, "exec"), ns)
    return json.loads(ns["fc_run"](code, pre, tests, cls))


class AiMakerProblemTests(AppCase):
    api, signup, admin = _te.EditorTests.api, _te.EditorTests.signup, _te.EditorTests.admin

    def fake(self, payload):
        return mock.patch.object(aimakerp, "_generate", return_value=(payload, "test/model:free"))

    def post(self, tok, **kw):
        return self.api("POST", "/admin/aimaker/problem", tok, **dict(FORM, **kw))

    def test_example_in_prompt_really_works(self):
        ok = run_prelude(EX["reference"], EX["pre"], EX["tests"])
        self.assertEqual(ok["status"], "ok", ok)
        self.assertEqual(ok["count"], 150)
        empty = run_prelude(EX["starter"], EX["pre"], EX["tests"])
        self.assertNotEqual(empty["status"], "ok")

    def test_only_admin(self):
        tok, _ = self.signup()
        self.assertEqual(self.post(tok).status_code, 403)

    def test_good_draft_is_clean_and_not_saved(self):
        tok = self.admin()
        before = len(algos.PROBLEMS)
        with self.fake(json.dumps(dict(EX, level="hard"))):
            r = self.post(tok)
        self.assertEqual(r.status_code, 200, r.get_json())
        j = r.get_json()
        self.assertEqual(j["problems"], [])
        self.assertEqual(j["draft"]["fn"], "maxProfit")
        self.assertEqual(j["draft"]["level"], "easy")  # уровень задаёт форма, а не модель
        self.assertEqual(j["left"], self.app.config["AIMAKER_PROBLEMS_DAILY"] - 1)
        self.assertEqual(len(algos.PROBLEMS), before)
        algoeditor.problem_data(dict(j["draft"]), 1)  # редактор примет такой черновик при сохранении

    def test_fenced_json_and_string_lists(self):
        tok = self.admin()
        raw = dict(EX, examples="a  →  1\nb  →  2", hints="раз\nдва")
        with self.fake("```json\n" + json.dumps(raw) + "\n```"):
            j = self.post(tok).get_json()
        self.assertEqual(j["problems"], [])
        self.assertEqual(len(j["draft"]["examples"]), 2)

    def test_missing_method_is_reported(self):
        tok = self.admin()
        bad = dict(EX, reference=EX["reference"].replace("maxProfit", "other"))
        with self.fake(json.dumps(bad)):
            j = self.post(tok).get_json()
        self.assertTrue(any("class Solution" in p for p in j["problems"]), j["problems"])

    def test_tests_without_check_are_reported(self):
        tok = self.admin()
        with self.fake(json.dumps(dict(EX, tests="def gen(r):\n    return ()"))):
            j = self.post(tok).get_json()
        self.assertTrue(any("check" in p for p in j["problems"]), j["problems"])

    def test_not_json_is_502(self):
        tok = self.admin()
        with self.fake("не получилось"):
            self.assertEqual(self.post(tok).status_code, 502)

    def test_fix_mode_sends_draft_and_error(self):
        tok = self.admin()
        with self.fake(json.dumps(EX)) as g:
            r = self.post(tok, fix={"draft": EX, "error": "Вход: [1]\nОжидалось: 0\nПолучено: 5"})
        self.assertEqual(r.status_code, 200, r.get_json())
        user = g.call_args[0][0][1]["content"]
        self.assertIn("Получено: 5", user)
        self.assertIn("maxProfit", user)

    def test_fix_without_error_is_400(self):
        tok = self.admin()
        self.assertEqual(self.post(tok, fix={"draft": EX, "error": ""}).status_code, 400)

    def test_template_and_titles_go_into_prompt(self):
        tok = self.admin()
        L = content.LESSONS[0]
        with self.fake(json.dumps(EX)) as g:
            self.post(tok, template=L["id"], titles=["Уже есть такая"])
        user = g.call_args[0][0][1]["content"]
        self.assertIn(L["cls"], user)
        self.assertIn("Уже есть такая", user)

    def test_daily_limit(self):
        tok = self.admin()
        self.app.config["AIMAKER_PROBLEMS_DAILY"] = 1
        with self.fake(json.dumps(EX)):
            self.assertEqual(self.post(tok).status_code, 200)
            self.assertEqual(self.post(tok).status_code, 429)

    def test_form_validation(self):
        tok = self.admin()
        self.assertEqual(self.post(tok, idea="").status_code, 400)
        self.assertEqual(self.post(tok, level="insane").status_code, 400)
        self.assertEqual(self.post(tok, fn="bad name").status_code, 400)


if __name__ == "__main__":
    unittest.main()
