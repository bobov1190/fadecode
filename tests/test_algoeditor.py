import unittest

from fadecode import algos, content

from tests import test_editor as _te
from tests.test_app import AppCase

STARTER = "class Solution:\n    def twice(self, x: int) -> int:\n        pass"
REF = "class Solution:\n    def twice(self, x: int) -> int:\n        return 2 * x"
TESTS = "def gen(r):\n    return (r.randint(0, 9),)\n\ndef brute(x):\n    return x + x\n\ncheck(S, \"twice\", gen, brute)"


def problem(**kw):
    p = {"title": "Удвоить", "level": "easy", "fn": "twice", "statement": "Верни x * 2.", "examples": ["x = 2 → 4"],
         "hints": ["Умножь."], "starter": STARTER, "reference": REF, "insight": "Просто.", "pre": "", "tests": TESTS}
    p.update(kw)
    return p


class AlgoEditorTests(AppCase):
    api, signup, admin = _te.EditorTests.api, _te.EditorTests.signup, _te.EditorTests.admin

    def body(self, **kw):
        d = {"title": "Мой алгоритм", "tag": "тест", "desc": "Описание", "template": content.LESSONS[0]["id"],
             "variations": [], "pack": content.PACKS[0]["id"], "problems": [problem()]}
        d.update(kw)
        return d

    def test_only_admin(self):
        tok, _ = self.signup()
        self.assertEqual(self.api("GET", "/admin/algos", tok).status_code, 403)
        self.assertEqual(self.api("POST", "/admin/algos", tok, **self.body()).status_code, 403)

    def test_create_update_delete(self):
        tok = self.admin()
        r = self.api("POST", "/admin/algos", tok, **self.body(problems=[problem(), problem(title="Второй")]))
        self.assertEqual(r.status_code, 201, r.get_json())
        A = r.get_json()["algo"]
        self.assertEqual(len(A["problems"]), 2)
        self.assertIn(A["id"], algos.BY_ID)
        self.assertIn(A["problems"][0]["id"], algos.PROBLEMS)
        # правка: первая остаётся (тот же id), вторая убрана, третья новая
        keep = A["problems"][0]
        body = self.body(title="Новое имя", problems=[dict(keep, statement="Новое условие"), problem(title="Третий")])
        u = self.api("PUT", "/admin/algos/" + A["id"], tok, **body)
        self.assertEqual(u.status_code, 200, u.get_json())
        B = u.get_json()["algo"]
        self.assertEqual(B["title"], "Новое имя")
        self.assertEqual(B["problems"][0]["id"], keep["id"])
        self.assertEqual(B["problems"][0]["statement"], "Новое условие")
        self.assertNotIn(A["problems"][1]["id"], algos.PROBLEMS)
        self.assertEqual(self.api("DELETE", "/admin/algos/" + A["id"], tok).status_code, 200)
        self.assertNotIn(A["id"], algos.BY_ID)
        self.assertEqual(self.api("GET", "/admin/algos/" + A["id"], tok).status_code, 404)

    def test_validation(self):
        tok = self.admin()
        bad = [
            self.body(template="nope"),
            self.body(pack="nope"),
            self.body(title=""),
            self.body(problems=[problem(level="insane")]),
            self.body(problems=[problem(fn="bad name")]),
            self.body(problems=[problem(reference="class Solution:\n    def other(self):\n        pass")]),
            self.body(problems=[problem(starter="class Solution(:\n    pass")]),
            self.body(problems=[problem(tests="check(")]),
            self.body(problems=[problem(tests="")]),
        ]
        for b in bad:
            self.assertEqual(self.api("POST", "/admin/algos", tok, **b).status_code, 400, b["problems"])

    def test_all_existing_algos_survive_a_roundtrip(self):
        tok = self.admin()
        for A in list(algos.ALGOS):
            full = self.api("GET", "/admin/algos/" + A["id"], tok).get_json()["algo"]
            r = self.api("PUT", "/admin/algos/" + A["id"], tok, **full)
            self.assertEqual(r.status_code, 200, (A["id"], r.get_json()))
            self.assertEqual(r.get_json()["algo"]["problems"], full["problems"])


if __name__ == "__main__":
    unittest.main()
