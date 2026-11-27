import copy
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from rider_media import ROOT, read_portrait


MARC = "f55b433d-38b8-4d1d-bb3a-a709c82a0260"


class RiderMediaTests(unittest.TestCase):
    def test_only_approved_same_season_same_class_face_is_selected(self):
        portrait = read_portrait(MARC, 2026, ["MotoGP"])
        self.assertEqual(portrait["rights"]["creator"], "Denkmit")
        for rider, year, categories in [
            (MARC, None, ["MotoGP"]), (MARC, 2025, ["MotoGP"]),
            (MARC, 2026, ["Moto2"]), ("unpictured", 2026, ["MotoGP"]),
            ("e7e4c72e-952e-4f64-8e8a-a47ff590fade", 2025, ["MotoGP"]),
        ]:
            with self.subTest(rider=rider, year=year, categories=categories):
                self.assertIsNone(read_portrait(rider, year, categories))
        for variant in portrait["display_derivatives"]:
            with Image.open(ROOT / variant["path"]) as image:
                self.assertEqual(image.size, (variant["width_px"], variant["height_px"]))
                self.assertEqual(image.format, "WEBP")
                self.assertEqual(image.getexif().get(315), "Denkmit")
                self.assertIn("CC BY-SA 4.0", image.getexif().get(33432))
            self.assertLess(variant["bytes"], 60000)

    def test_unapproved_or_mislicensed_derivatives_cannot_be_displayed(self):
        original = read_portrait(MARC, 2026, ["MotoGP"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            asset = copy.deepcopy(original)
            asset["rights"]["approval"] = "unapproved"
            (root / "media_catalog.json").write_text(json.dumps({"format_version": 1, "assets": [asset]}))
            self.assertIsNone(read_portrait(MARC, 2026, ["MotoGP"], root))
            asset["rights"]["approval"] = "approved_editorial"
            asset["display_derivatives"][0]["license"] = "NOASSERTION"
            (root / "media_catalog.json").write_text(json.dumps({"format_version": 1, "assets": [asset]}))
            with self.assertRaisesRegex(ValueError, "rights/source"):
                read_portrait(MARC, 2026, ["MotoGP"], root)


if __name__ == "__main__":
    unittest.main()
