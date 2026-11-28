import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from fastapi.testclient import TestClient

import preview_api
from rider_numbers import list_numbers, read_identity_number, read_number
from stage_rider_numbers import stage


PROFILE = "23e50438-a657-4fb0-a190-3262b5472f29"
RIDER = "f55b433d-38b8-4d1d-bb3a-a709c82a0260"


class NumberArtworkTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.image = self.source / "number.png"
        Image.new("RGBA", (3, 3), "red").save(self.image)
        self.row = {
            "rider_id": PROFILE, "legacy_id": 1, "season": 2021, "category": "MotoGP",
            "number": 93, "source_url": "https://photos.motogp.com/number.png",
            "file": str(self.image), "bytes": self.image.stat().st_size,
        }
        self.bundle = self.root / "bundle"

    def make_bundle(self, rows=None):
        (self.source / "manifest.json").write_text(json.dumps({"files": rows or [self.row]}), encoding="utf-8")
        with patch("stage_rider_numbers.identity_links", return_value={PROFILE: {"rider_id": RIDER, "legacy_id": 1}}):
            return stage(self.source, self.bundle, self.root / "cache")

    def test_exact_identity_scope_and_http_delivery(self):
        self.assertEqual(self.make_bundle(), (1, 1))
        asset, data = read_number(RIDER, 2021, "MotoGP", 93, self.bundle)
        self.assertEqual(hashlib.sha256(data).hexdigest(), asset["sha256"])
        for rider, year, category, number in [
            ("other", 2021, "MotoGP", 93), (RIDER, 2022, "MotoGP", 93),
            (RIDER, 2021, "Moto2", 93), (RIDER, 2021, "MotoGP", 1),
        ]:
            self.assertIsNone(read_number(rider, year, category, number, self.bundle))
        with patch.dict("os.environ", {"MOTOGP_RIDER_NUMBERS": str(self.bundle)}):
            client = TestClient(preview_api.app)
            for prefix in ("", "/paddock"):
                listing = client.get(f"{prefix}/api/riders/{RIDER}/number-art").json()["artwork"]
                self.assertEqual(len(listing), 1)
                response = client.get(prefix + listing[0]["url"])
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, data)
                self.assertEqual(response.headers["content-type"], "image/png")
                self.assertEqual(client.get(f"{prefix}/api/riders/{RIDER}/number-art/2022/MotoGP/93").status_code, 404)
                identity = client.get(f"{prefix}/api/riders/{RIDER}/number-identity?season=1970&category=350cc&number=1").json()["artwork"][0]
                self.assertEqual((identity["season"], identity["category"], identity["number"]), (2021, "MotoGP", 93))
                self.assertEqual(client.get(prefix + identity["url"]).content, data)

    def test_conflicting_designs_are_not_selected(self):
        other = self.source / "other.png"
        Image.new("RGBA", (3, 3), "blue").save(other)
        second = {**self.row, "file": str(other), "bytes": other.stat().st_size}
        self.make_bundle([self.row, second])
        self.assertIsNone(read_number(RIDER, 2021, "MotoGP", 93, self.bundle))
        self.assertEqual(list_numbers(RIDER, bundle=self.bundle), [])
        with patch.dict("os.environ", {"MOTOGP_RIDER_NUMBERS": str(self.bundle)}):
            client = TestClient(preview_api.app)
            for prefix in ("", "/paddock"):
                identity = client.get(f"{prefix}/api/riders/{RIDER}/number-identity").json()["artwork"][0]
                response = client.get(prefix + identity["url"])
                self.assertEqual(response.status_code, 200)
                self.assertIn(response.content, [self.image.read_bytes(), other.read_bytes()])

    def test_identity_uses_latest_design_with_stable_tie_break_and_verified_bytes(self):
        other = self.source / "other.png"
        Image.new("RGBA", (3, 3), "blue").save(other)
        newer = {**self.row, "season": 2024}
        alternative = {**newer, "file": str(other), "bytes": other.stat().st_size}
        self.make_bundle([self.row, newer, alternative])
        selected, data = read_identity_number(RIDER, self.bundle)
        self.assertEqual(selected["season"], 2024)
        self.assertEqual(hashlib.sha256(data).hexdigest(), selected["sha256"])
        self.assertIsNone(read_identity_number("another-rider", self.bundle))
        catalog_path = self.bundle / "catalog.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog["assets"].reverse()
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
        self.assertEqual(read_identity_number(RIDER, self.bundle), (selected, data))
        (self.bundle / selected["file"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            read_identity_number(RIDER, self.bundle)

    def test_identity_uses_latest_design_with_stable_tie_break_and_verified_bytes(self):
        other = self.source / "other.png"
        Image.new("RGBA", (3, 3), "blue").save(other)
        newer = {**self.row, "season": 2024}
        alternative = {**newer, "file": str(other), "bytes": other.stat().st_size}
        self.make_bundle([self.row, newer, alternative])
        selected, data = read_identity_number(RIDER, self.bundle)
        self.assertEqual(selected["season"], 2024)
        self.assertEqual(hashlib.sha256(data).hexdigest(), selected["sha256"])
        self.assertIsNone(read_identity_number("another-rider", self.bundle))
        catalog_path = self.bundle / "catalog.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog["assets"].reverse()
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
        self.assertEqual(read_identity_number(RIDER, self.bundle), (selected, data))
        (self.bundle / selected["file"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            read_identity_number(RIDER, self.bundle)

    def test_integrity_and_path_tampering_are_errors(self):
        self.make_bundle()
        catalog_path = self.bundle / "catalog.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        asset = catalog["assets"][0]
        (self.bundle / asset["file"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            list_numbers(RIDER, bundle=self.bundle)
        asset["file"] = "../outside.png"
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inside"):
            list_numbers(RIDER, bundle=self.bundle)

    def test_unmatched_profile_and_outside_source_are_rejected(self):
        (self.source / "manifest.json").write_text(json.dumps({"files": [self.row]}), encoding="utf-8")
        with patch("stage_rider_numbers.identity_links", return_value={}):
            with self.assertRaisesRegex(ValueError, "unambiguous"):
                stage(self.source, self.bundle, self.root)
        outside = self.root / "outside.png"
        outside.write_bytes(self.image.read_bytes())
        self.row["file"] = str(outside)
        with self.assertRaisesRegex(ValueError, "outside source"):
            self.make_bundle()
        self.assertFalse(self.bundle.exists())

    def test_explicit_missing_bundle_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            list_numbers(RIDER, bundle=self.root / "missing")

    def test_explicit_hold_keeps_unmatched_and_unknown_scope_out_of_display(self):
        unknown = {**self.row, "category": "dorsales-legacy-3", "number": None}
        unmatched = {**self.row, "rider_id": "00000000-0000-0000-0000-000000000001"}
        (self.source / "manifest.json").write_text(
            json.dumps({"files": [self.row, unknown, unmatched]}), encoding="utf-8"
        )
        with patch("stage_rider_numbers.identity_links", return_value={PROFILE: {"rider_id": RIDER, "legacy_id": 1}}):
            self.assertEqual(stage(self.source, self.bundle, self.root / "cache", hold_unmatched=True), (1, 1))
        catalog = json.loads((self.bundle / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual([item["reason"] for item in catalog["held"]],
                         ["unknown_class_and_number", "no_unambiguous_results_id"])
        self.assertEqual(len(list_numbers(RIDER, bundle=self.bundle)), 1)


if __name__ == "__main__":
    unittest.main()
