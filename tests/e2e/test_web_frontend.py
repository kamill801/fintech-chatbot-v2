from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ledger.factory import create_app
from tests.helpers import FERNET_KEY, USER_REF_SECRET


class WebFrontendE2ETests(unittest.TestCase):
    def app_config(self, frontend_dist: str) -> dict[str, str]:
        return {
            "TESTING": "1",
            "APP_ENV": "test",
            "LEDGER_STORE": "memory",
            "ALLOW_DEV_AUTH": "1",
            "LEDGER_ENCRYPTION_KEY": FERNET_KEY.decode("ascii"),
            "LEDGER_USER_REF_SECRET": USER_REF_SECRET.decode("ascii"),
            "FRONTEND_DIST": frontend_dist,
        }

    def test_serves_frontend_assets_and_spa_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            build_dir = Path(temporary_directory)
            (build_dir / "index.html").write_text("<main>내 장부</main>", encoding="utf-8")
            (build_dir / "asset.txt").write_text("asset", encoding="utf-8")
            client = create_app(self.app_config(temporary_directory)).test_client()

            root = client.get("/")
            ledger = client.get("/ledger")
            asset = client.get("/asset.txt")
            try:
                self.assertIn("내 장부", root.get_data(as_text=True))
                self.assertIn("내 장부", ledger.get_data(as_text=True))
                self.assertEqual(asset.get_data(as_text=True), "asset")
            finally:
                root.close()
                ledger.close()
                asset.close()
            self.assertEqual(client.get("/api/unknown").status_code, 404)

    def test_reports_missing_frontend_build_without_hiding_api(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            client = create_app(self.app_config(temporary_directory)).test_client()
            self.assertEqual(client.get("/").status_code, 404)
            self.assertEqual(client.get("/health").status_code, 200)


if __name__ == "__main__":
    unittest.main()
