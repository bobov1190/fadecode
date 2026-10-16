import json
import unittest
from unittest import mock

from fadecode import aimaker

from tests.test_app import AppCase
from tests import test_editor as _te

lesson_body = _te.lesson_body

FORM = {"topic": "Стек", "goal": "Следующий больший элемент", "stack": "Python", "level": "medium", "n_methods": 2}


class AiMakerTests(AppCase):
    api, signup, admin = _te.EditorTests.api, _te.EditorTests.signup, _te.EditorTests.admin
    def fake(self, payload):
        return mock.patch.object(aimaker, "_generate", return_value=(payload, "test/model:free"))

    def test_parse_handles_fences_and_noise(self):
        obj = {"a": 1}
        self.assertEqual(aimaker._parse("```json\n" + json.dumps(obj) + "\n```"), obj)
        self.assertEqual(aimaker._parse("Вот результат: " + json.dumps(obj) + " готово"), obj)
        with self.assertRaises(ValueError):
            aimaker._parse("совсем не json")

    def test_only_admin(self):
        tok, _ = self.signup()
        self.assertEqual(self.api("POST", "/admin/aimaker/lesson", tok, **FORM).status_code, 403)

    def test_good_draft_has_no_problems_and_is_not_saved(self):
        tok = self.admin()
        before = len(self.api("GET", "/admin/content", tok).get_json()["lessons"])
        with self.fake(json.dumps(lesson_body())):
            r = self.api("POST", "/admin/aimaker/lesson", tok, **FORM)
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertEqual(j["problems"], [])
        self.assertEqual(len(j["draft"]["blocks"]), 2)
        self.assertEqual(j["left"], self.app.config["AIMAKER_DAILY"] - 1)
        self.assertEqual(len(self.api("GET", "/admin/content", tok).get_json()["lessons"]), before)

    def test_bad_code_comes_back_as_problem(self):
        tok = self.admin()
        body = lesson_body()
        body["blocks"][0]["code"] = "def broken(:\n    pass"
        with self.fake(json.dumps(body)):
            j = self.api("POST", "/admin/aimaker/lesson", tok, **FORM).get_json()
        self.assertTrue(any("синтаксис" in p for p in j["problems"]))

    def test_wrong_method_count_is_reported(self):
        tok = self.admin()
        with self.fake(json.dumps(lesson_body())):
            j = self.api("POST", "/admin/aimaker/lesson", tok, **dict(FORM, n_methods=4)).get_json()
        self.assertTrue(any("методов" in p for p in j["problems"]))

    def test_not_json_is_502(self):
        tok = self.admin()
        with self.fake("извини, не могу"):
            r = self.api("POST", "/admin/aimaker/lesson", tok, **FORM)
        self.assertEqual(r.status_code, 502)

    def test_daily_limit(self):
        tok = self.admin()
        self.app.config["AIMAKER_DAILY"] = 1
        with self.fake(json.dumps(lesson_body())):
            self.assertEqual(self.api("POST", "/admin/aimaker/lesson", tok, **dict(FORM, n_methods=2)).status_code, 200)
            self.assertEqual(self.api("POST", "/admin/aimaker/lesson", tok, **FORM).status_code, 429)

    def test_validation_of_form(self):
        tok = self.admin()
        self.assertEqual(self.api("POST", "/admin/aimaker/lesson", tok, **dict(FORM, topic="")).status_code, 400)
        self.assertEqual(self.api("POST", "/admin/aimaker/lesson", tok, **dict(FORM, level="insane")).status_code, 400)
        self.assertEqual(self.api("POST", "/admin/aimaker/lesson", tok, **dict(FORM, n_methods=99)).status_code, 400)


if __name__ == "__main__":
    unittest.main()
