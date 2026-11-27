import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rider_profiles import (
    BASE_URL, ProfileSource, coverage, digest, identity_links, main, normalize_profile,
    read_enrichment, write_json,
)


PROFILE = "23e50438-a657-4fb0-a190-3262b5472f29"
RIDER = "f55b433d-38b8-4d1d-bb3a-a709c82a0260"
STEP = "ca3a0001-e5d8-4bd2-bb25-bc478fcf6bfd"
LINK = {"rider_id": RIDER, "legacy_id": 7444, "method": "official_results_explicit_profile_uuid"}


def response():
    return {
        "source_url": f"{BASE_URL}/riders/{PROFILE}", "retrieved_at": "2026-11-27T12:00:00+00:00",
        "source_sha256": "a" * 64,
        "payload": {
            "id": PROFILE, "legacy_id": 7444, "name": "Marc", "surname": "Marquez",
            "birth_date": "1993-02-17", "birth_city": "Cervera", "birth_country": "Spain",
            "physical_attributes": {"height": 169},
            "career": [{
                "id": STEP, "season": 2024, "number": 93, "sponsored_team": "Gresini Racing",
                "team": {"id": "team", "name": "Renamed team TODAY", "constructor": {"name": "Ducati"}},
                "category": {"id": "class", "name": "MotoGP"},
                "pictures": {"profile": {"main": "https://photos.motogp.com/2024/profile.png"},
                             "bike": {"main": "https://photos.motogp.com/2024/bike.png"},
                             "portrait": "https://photos.motogp.com/2024/face.jpg",
                             "number": "https://photos.motogp.com/2024/93.png"},
            }, {
                "id": "e8742a71-7a54-4a52-9d87-a63103eb8647", "season": 2026,
                "sponsored_team": "Ducati Lenovo Team", "pictures": {},
            }],
        },
    }


class RiderProfileTests(unittest.TestCase):
    def test_explicit_identity_link_and_historical_kit_are_preserved(self):
        profile = normalize_profile(response(), LINK)
        self.assertEqual(profile["rider_id"], RIDER)
        self.assertEqual(profile["profile_id"], PROFILE)
        self.assertEqual(profile["biography"]["height_cm"], 169)
        old, current = profile["careers"]
        self.assertEqual(old["team_name"], "Gresini Racing")
        self.assertIsNotNone(old["media"]["bike"])
        self.assertIsNone(current["media"]["bike"])
        self.assertIsNone(old["media"]["rider_with_bike"])
        self.assertEqual(old["media"]["number"]["rights"]["approval"], "unapproved")
        self.assertIsNone(old["media"]["rider_cutout"]["technical"]["has_transparency"])
        self.assertEqual(coverage([profile], 2026)["requested_season_media"]["bike"], 0)

    def test_missing_biography_and_zero_height_are_unknown_not_estimated(self):
        source = response()
        source["payload"].update(birth_date=None, birth_city=None, physical_attributes={"height": 0})
        profile = normalize_profile(source, None)
        self.assertIsNone(profile["rider_id"])
        self.assertIsNone(profile["biography"]["height_cm"])
        self.assertIsNone(profile["biography"]["birth_date"])
        self.assertEqual(profile["identity"]["method"], "unmatched")

    def test_invalid_facts_identity_and_duplicate_steps_fail_explicitly(self):
        for field, value in [("birth_date", "2999-01-01"), ("physical_attributes", {"height": -1}),
                             ("physical_attributes", {"height": float("nan")})]:
            with self.subTest(field=field, value=value):
                source = response()
                source["payload"][field] = value
                with self.assertRaises(ValueError):
                    normalize_profile(source, None)
        with self.assertRaisesRegex(ValueError, "Legacy ID"):
            normalize_profile(response(), {"rider_id": RIDER, "legacy_id": 999})
        source = response()
        source["payload"]["career"].append(copy.deepcopy(source["payload"]["career"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate career"):
            normalize_profile(source, None)

    def test_nonofficial_or_nonhttps_media_is_rejected(self):
        for url in ["http://photos.motogp.com/test.png", "https://unrelated.example/test.png"]:
            source = response()
            source["payload"]["career"][0]["pictures"]["number"] = url
            with self.assertRaisesRegex(ValueError, "artwork URL"):
                normalize_profile(source, None)

    def test_only_explicit_result_ids_can_match_and_conflicts_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "2026.json"
            rider = {"id": RIDER, "riders_api_uuid": PROFILE, "legacy_id": 7444}
            snapshot = {"events": [], "standings": {"classification": [{"rider": rider}]}}
            write_json(path, snapshot)
            links = identity_links(temporary)
            self.assertEqual(links[PROFILE]["rider_id"], RIDER)
            self.assertEqual(links[PROFILE]["snapshot"], "2026.json")
            rider["riders_id"] = "5556da3f-aa2f-46cc-a6e8-48641f47d500"
            write_json(path, snapshot)
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                identity_links(temporary)
            rider.pop("riders_id")
            rider.pop("riders_api_uuid")
            rider["full_name"] = "Marc Marquez"
            write_json(path, snapshot)
            with self.assertRaisesRegex(ValueError, "no explicit"):
                identity_links(temporary)

    def test_enrichment_is_optional_but_explicit_bad_configuration_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "catalog.json"
            with patch("rider_profiles.DEFAULT_CATALOG", path):
                self.assertEqual(read_enrichment(RIDER)["status"], "not_collected")
            with self.assertRaisesRegex(ValueError, "missing"):
                read_enrichment(RIDER, path)
            profile = normalize_profile(response(), LINK)
            write_json(path, {"format_version": 1, "profiles": [profile]})
            self.assertEqual(read_enrichment(RIDER, path)["profile"]["profile_id"], PROFILE)
            self.assertEqual(read_enrichment("another-rider", path)["status"], "not_collected")
            write_json(path, {"format_version": 1, "profiles": [profile, profile]})
            with self.assertRaisesRegex(ValueError, "Duplicate rider"):
                read_enrichment(RIDER, path)

    def test_multiple_result_uuids_for_one_profile_are_held_not_merged(self):
        with tempfile.TemporaryDirectory() as temporary:
            write_json(Path(temporary) / "2026.json", {
                "events": [], "standings": {"classification": [
                    {"rider": {"id": RIDER, "riders_id": PROFILE, "legacy_id": 7444}},
                    {"rider": {"id": STEP, "riders_id": PROFILE, "legacy_id": 7444}},
                ]},
            })
            link = identity_links(temporary)[PROFILE]
            self.assertEqual(link["method"], "ambiguous_official_results_links")
            self.assertIsNone(normalize_profile(response(), link)["rider_id"])
            self.assertEqual(len(link["candidates"]), 2)

    def test_cached_source_keeps_retrieval_date_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as temporary, patch("rider_profiles.requests.get") as get:
            get.return_value.status_code = 200
            get.return_value.json.return_value = {"id": PROFILE}
            source = ProfileSource(temporary)
            first = source(f"riders/{PROFILE}")
            second = source(f"riders/{PROFILE}")
            self.assertEqual(first, second)
            get.assert_called_once()
            self.assertEqual(first["source_sha256"], digest(first["payload"]))
            path = next(Path(temporary).glob("*.json"))
            data = json.loads(path.read_text())
            data["payload"]["id"] = "tampered"
            write_json(path, data)
            with self.assertRaisesRegex(ValueError, "Invalid cached"):
                source(f"riders/{PROFILE}")

    def test_collection_rejects_wrong_endpoint_identity_and_wrong_season(self):
        with tempfile.TemporaryDirectory() as temporary, patch("rider_profiles.identity_links", return_value={}), \
                patch("rider_profiles.ProfileSource") as source:
            directory = {"payload": [{"id": PROFILE}]}
            wrong = response()
            wrong["payload"]["id"] = RIDER
            source.return_value.side_effect = [directory, wrong]
            with self.assertRaisesRegex(ValueError, "different rider"):
                main(["--output", str(Path(temporary) / "output.json")])
            wrong = response()
            wrong["payload"]["career"] = []
            source.return_value.side_effect = [directory, wrong]
            with self.assertRaisesRegex(ValueError, "requested-season"):
                main(["--season", "2026", "--output", str(Path(temporary) / "output.json")])

    def test_collection_writes_counts_manifest_separate_from_private_catalog(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch("rider_profiles.identity_links", return_value={PROFILE: LINK}), \
                patch("rider_profiles.ProfileSource") as source, patch("builtins.print"):
            directory = {**response(), "payload": [{"id": PROFILE}]}
            source.return_value.side_effect = [directory, response()]
            output, manifest = Path(temporary) / "catalog.json", Path(temporary) / "manifest.json"
            main(["--season", "2026", "--output", str(output), "--manifest", str(manifest)])
            report = json.loads(manifest.read_text())
            self.assertEqual(report["coverage"]["matched_results_riders"], 1)
            self.assertEqual(report["catalog"]["bytes"], output.stat().st_size)
            self.assertNotIn("profiles", report)
            self.assertEqual(json.loads(output.read_text())["profiles"][0]["rider_id"], RIDER)


if __name__ == "__main__":
    unittest.main()
