import unittest
from unittest.mock import patch
from pathlib import Path
import io
import tarfile
import tempfile

from build_champion_biographies import build_catalog, factual_summary, select_champions
from rider_profiles import read_enrichment
from test_rider_profiles import LINK, PROFILE, RIDER, response


def winner(year, category, rider="rider", final="1", position="1"):
    return {
        "season_year": str(year), "category": category, "rider_id": rider,
        "is_final": final, "position": position, "source_url": "https://source.example/standings",
    }


class ChampionBiographyTests(unittest.TestCase):
    def test_exact_premier_threshold_unifies_500cc_and_motogp(self):
        selected = select_champions([
            winner(2001, "500cc"), winner(2002, "MotoGP\u2122"),
            winner(2003, "MotoGP", "single"),
        ])
        self.assertEqual(set(selected), {"rider"})
        self.assertEqual(selected["rider"]["premier_final_records"], 2)

    def test_lower_threshold_combines_distinct_classes_and_simultaneous_titles(self):
        rows = [winner(1980, "250cc"), winner(1981, "250cc"), winner(1981, "350cc"),
                winner(1982, "350cc"), winner(1987, "250cc")]
        self.assertEqual(select_champions(rows)["rider"]["lower_class_final_records"], 5)
        self.assertEqual(select_champions(rows[:-1]), {})

    def test_one_premier_plus_four_lower_does_not_pass_either_threshold(self):
        rows = [winner(2000, "500cc")] + [winner(year, "125cc") for year in range(1990, 1994)]
        self.assertEqual(select_champions(rows), {})

    def test_provisional_titles_runners_up_and_duplicate_rows_do_not_inflate_counts(self):
        first = winner(2025, "MotoGP")
        rows = [first, first, winner(2026, "MotoGP", final="0"), winner(2024, "MotoGP", position="2")]
        self.assertEqual(select_champions(rows), {})

    def test_conflicting_winners_fail_instead_of_silently_selecting_both(self):
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            select_champions([winner(2000, "500cc", "one"), winner(2000, "500cc", "two")])

    def test_small_displacement_titles_count_and_summary_does_not_claim_career_totals(self):
        rows = [winner(year, "50cc") for year in range(1970, 1973)] + [
            winner(1984, "80cc"), winner(1985, "80cc")]
        evidence = select_champions(rows)["rider"]
        summary = factual_summary(evidence)
        self.assertIn("50cc: 1970, 1971, 1972", summary)
        self.assertIn("not a complete career-title total", summary)

    def test_generated_catalog_keeps_explicit_identity_and_facts_but_strips_all_artwork(self):
        csv_bytes = (
            "season_year,category,rider_id,is_final,position,source_url\n"
            f"2013,MotoGP,{RIDER},1,1,https://source.example/2013\n"
            f"2014,MotoGP,{RIDER},1,1,https://source.example/2014\n"
        ).encode()
        with tempfile.TemporaryDirectory() as temporary, \
                patch("build_champion_biographies.verify_export",
                      return_value={"snapshot_database_time_utc": "2026-11-27T20:00:00"}), \
                patch("build_champion_biographies.identity_links", return_value={PROFILE: LINK}), \
                patch("builtins.print"):
            path = Path(temporary) / "snapshot.tar.xz"
            with tarfile.open(path, "w:xz") as archive:
                member = tarfile.TarInfo("tables/dbo.championship_standings.csv")
                member.size = len(csv_bytes)
                archive.addfile(member, io.BytesIO(csv_bytes))
            catalog = build_catalog(path, Path("cache"), lambda endpoint: response())
            profile = catalog["profiles"][0]
            self.assertEqual(profile["rider_id"], RIDER)
            self.assertEqual(profile["profile_id"], PROFILE)
            self.assertEqual(profile["biography"]["birth_date"], "1993-02-17")
            self.assertEqual(profile["careers"], [])
            self.assertEqual(profile["source"], {
                key: response()[key] for key in ("source_url", "retrieved_at", "source_sha256")
            })
            self.assertNotIn("pictures", str(profile))
            self.assertEqual(catalog["coverage"]["profiles"], 1)

    def test_reviewed_catalog_exposes_both_premier_and_lower_class_champions_without_media(self):
        rossi = read_enrichment("640859bc-3f12-44fe-949a-4eab1f48f02a")["profile"]
        mang = read_enrichment("8da50702-f7da-4b03-8cc7-a671ae928cc9")["profile"]
        for profile in (rossi, mang):
            self.assertIsNotNone(profile)
            self.assertEqual(profile["careers"], [])
            self.assertIsNotNone(profile["biography"]["birth_date"])
        self.assertEqual(mang["selection_evidence"]["lower_class_final_records"], 5)
        self.assertEqual(read_enrichment("e7e4c72e-952e-4f64-8e8a-a47ff590fade")["status"], "not_collected")


if __name__ == "__main__":
    unittest.main()
