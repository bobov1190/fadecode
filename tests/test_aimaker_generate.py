import http.client
import io
import json
import urllib.error
from unittest import mock

from fadecode import ai, aimaker, aimakerp

from tests import test_editor as _te
from tests.test_app import AppCase


class Resp:
    """Ответ urlopen для стриминга: контекстный менеджер и итерация по строкам."""

    def __init__(self, lines):
        self.lines = [(l + "\n").encode("utf-8") for l in lines]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        return iter(self.lines)


def sse(parts, finish="stop"):
    lines = [": OPENROUTER PROCESSING", ""]
    lines += ["data: " + json.dumps({"choices": [{"delta": {"reasoning": "думаю"}}]}), ""]
    for p in parts:
        lines += ["data: " + json.dumps({"choices": [{"delta": {"content": p}}]}), ""]
    lines += ["data: " + json.dumps({"choices": [{"delta": {}, "finish_reason": finish}]}), "", "data: [DONE]"]
    return Resp(lines)


def http_error(code, msg):
    body = io.BytesIO(json.dumps({"error": {"message": msg}}).encode("utf-8"))
    return urllib.error.HTTPError("u", code, "x", {}, body)


class GenerateTests(AppCase):
    api, signup, admin = _te.EditorTests.api, _te.EditorTests.signup, _te.EditorTests.admin

    def setUp(self):
        super().setUp()
        self.app.config.update(OPENROUTER_API_KEY="k", AIMAKER_MODELS=["a/one:free", "b/two:free"])

    def gen(self, *effects):
        with self.app.app_context(), mock.patch.object(aimaker.urllib.request, "urlopen", side_effect=list(effects)) as u:
            try:
                return aimaker._generate([{"role": "user", "content": "x"}]), u
            except ai.AIError as e:
                return e, u

    def test_stream_collects_content_and_ignores_reasoning(self):
        (text, model), u = self.gen(sse(['{"a":', ' 1}']))
        self.assertEqual((text, model), ('{"a": 1}', "a/one:free"))
        self.assertEqual(u.call_count, 1)

    def test_falls_back_to_next_model(self):
        (text, model), u = self.gen(http_error(429, "Rate limit exceeded"), sse(["ok"]))
        self.assertEqual((text, model), ("ok", "b/two:free"))

    def test_error_lists_reason_for_every_model(self):
        e, _ = self.gen(http_error(429, "Rate limit exceeded: free-models-per-day"), TimeoutError("t"))
        self.assertIsInstance(e, ai.AIError)
        self.assertEqual(e.status, 502)
        self.assertIn("one: 429 Rate limit exceeded", e.message)
        self.assertIn("two: таймаут", e.message)

    def test_truncated_answer_goes_to_next_model(self):
        (text, model), _ = self.gen(sse(['{"a":'], finish="length"), sse(["{}"]))
        self.assertEqual(model, "b/two:free")

    def test_empty_answer_is_reported(self):
        e, _ = self.gen(sse([]), sse([]))
        self.assertIn("пустой ответ", e.message)

    def test_dropped_connection_is_handled(self):
        e, _ = self.gen(http.client.IncompleteRead(b"x"), http.client.RemoteDisconnected("gone"))
        self.assertIsInstance(e, ai.AIError)
        self.assertIn("one:", e.message)

    def test_midstream_error_event(self):
        bad = Resp(["data: " + json.dumps({"error": {"message": "overloaded"}})])
        (text, model), _ = self.gen(bad, sse(["ok"]))
        self.assertEqual(model, "b/two:free")

    def test_bad_key_stops_at_once(self):
        e, u = self.gen(http_error(401, "no auth"), sse(["ok"]))
        self.assertIn("OPENROUTER_API_KEY", e.message)
        self.assertEqual(u.call_count, 1)

    def test_no_key_is_503(self):
        self.app.config["OPENROUTER_API_KEY"] = ""
        e, u = self.gen()
        self.assertEqual(e.status, 503)
        self.assertEqual(u.call_count, 0)

    def test_failed_generation_does_not_spend_daily_limit(self):
        tok = self.admin()
        with mock.patch.object(aimakerp, "_generate", side_effect=ai.AIError("нет", 502)):
            r = self.api("POST", "/admin/aimaker/problem", tok, idea="x", level="easy")
        self.assertEqual(r.status_code, 502)
        with self.app.app_context():
            from fadecode import db

            self.assertEqual(db.ai_counts("makerp:" + ai.today(), 1)[1], 0)  # сумма за день по всем
