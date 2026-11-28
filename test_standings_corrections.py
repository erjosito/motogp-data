import unittest

from standings_corrections import corrected_standings


class StandingsCorrectionsTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"rider_id": "ea0101ee-6b38-4d39-a466-fa83d2e1b36f", "position": 1,
             "points": 9, "is_final": True},
            {"rider_id": "b3668951-07a4-43f1-962a-8c4fde9dfe7a", "position": 2,
             "points": 28, "is_final": True},
            {"rider_id": "other", "position": 3, "points": 46, "is_final": True},
        ]

    def test_exact_snapshot_gets_independent_totals_and_keeps_raw_values(self):
        output, evidence = corrected_standings(self.rows, 1970, "350cc")
        self.assertEqual([x["points"] for x in output], [90, 58, 46])
        self.assertEqual([x.get("source_points") for x in output], [9, 28, None])
        self.assertEqual(self.rows[0]["points"], 9)
        self.assertIn("best six", evidence["note"])

    def test_changed_or_partial_snapshot_is_not_patched(self):
        for rows, year, family in [
            (self.rows[:1], 1970, "350cc"),
            ([{**self.rows[0], "points": 90}, *self.rows[1:]], 1970, "350cc"),
            ([self.rows[0], {**self.rows[1], "position": 3}], 1970, "350cc"),
            ([{**self.rows[0], "is_final": False}, *self.rows[1:]], 1970, "350cc"),
            (self.rows, 1970, "premier"),
        ]:
            with self.subTest(rows=rows, year=year, family=family):
                result, evidence = corrected_standings(rows, year, family)
                self.assertIs(result, rows)
                self.assertIsNone(evidence)


if __name__ == "__main__":
    unittest.main()
