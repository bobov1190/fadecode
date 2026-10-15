"""Режим «всё в одном сервисе»: Flask отдаёт собранный Vue и JSON API (SERVE_SPA)."""
import os
import tempfile
import unittest

from fadecode import create_app, db


class SpaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        dist = os.path.join(self.tmp.name, "dist")
        os.makedirs(os.path.join(dist, "assets"))
        for name, text in {"index.html": "<!doctype html>SPA-INDEX", "landing.html": "LANDING",
                           "favicon.svg": "<svg/>", "assets/app-abc.js": "console.log(1)"}.items():
            with open(os.path.join(dist, name), "w", encoding="utf-8") as f:
                f.write(text)
        self.app = create_app({
            "TESTING": True, "SERVE_SPA": True, "SPA_DIR": dist,
            "DATABASE": os.path.join(self.tmp.name, "t.db"), "DATABASE_URL": "", "DATABASE_SCHEMA": "",
            "OPENROUTER_API_KEY": "",
        })
        self.c = self.app.test_client()

    def tearDown(self):
        db.shutdown(self.app, drop_schema=True)
        self.tmp.cleanup()

    def test_index_and_client_routes(self):
        for path in ("/", "/login", "/lessons/linreg/recall", "/stats"):
            r = self.c.get(path)
            self.assertEqual(r.status_code, 200, path)
            self.assertIn(b"SPA-INDEX", r.data, path)
            self.assertIn("no-cache", r.headers["Cache-Control"])

    def test_about_is_landing(self):
        r = self.c.get("/about")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"LANDING", r.data)

    def test_static_files(self):
        self.assertIn(b"console.log", self.c.get("/assets/app-abc.js").data)
        self.assertIn(b"<svg", self.c.get("/favicon.svg").data)
        self.assertEqual(self.c.get("/assets/missing.js").status_code, 404)

    def test_api_not_swallowed(self):
        r = self.c.get("/api/v1/packs")
        self.assertEqual(r.status_code, 401)  # JSON API, а не index.html
        self.assertEqual(self.c.get("/api/nope").status_code, 404)

    def test_healthz_still_works(self):
        r = self.c.get("/healthz")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["status"], "ok")

    def test_register_and_use_api_through_spa_mode(self):
        r = self.c.post("/api/v1/auth/register", json={"username": "neo", "password": "secret1"})
        self.assertEqual(r.status_code, 201, r.data)
        tok = r.get_json()["token"]
        r = self.c.get("/api/v1/packs", headers={"Authorization": "Bearer " + tok})
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
