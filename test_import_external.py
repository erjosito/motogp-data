import unittest
from import_external import assess, expected_points, name_key


class ExternalImportTests(unittest.TestCase):
    def setUp(self):
        self.row = {"year": "1966", "category": "500cc", "shortname": "TT",
                    "rider_name": "Agostini, Giacomo", "position": "2", "points": "6",
                    "bike_name": "MV Agusta"}
        self.identities = {(1966, "500cc", "giacomoagostini"): {"ago"}}
        self.sessions = {(1966, "500cc", "TT"): {"race"}}

    def test_independent_missing_race_pilot_and_official_point_enrichment(self):
        for official in [{}, {("race", "ago"): (2, None)}]:
            result = assess(self.row, self.identities, self.sessions, official)
            self.assertEqual(result["decision"], "accepted")
            self.assertEqual(result["points"], 6)
            self.assertNotIn("time", result)

    def test_unknown_status_points_and_conflicts_are_held(self):
        for changes, official in [
            ({"position": "-1"}, {}),
            ({"points": "NaN"}, {}),
            ({"points": "5"}, {}),
            ({}, {("race", "ago"): (1, None)}),
            ({}, {("race", "ago"): (2, 5)}),
        ]:
            with self.subTest(changes=changes, official=official):
                result = assess({**self.row, **changes}, self.identities, self.sessions, official)
                self.assertEqual(result["decision"], "held")
                self.assertIsNone(result["points"])

    def test_ambiguous_identity_or_multiple_races_cannot_cross_link(self):
        for ids, races in [({"ago", "another"}, {"race"}), ({"ago"}, {"race", "restart"})]:
            result = assess(self.row, {(1966, "500cc", "giacomoagostini"): ids},
                            {(1966, "500cc", "TT"): races}, {})
            self.assertEqual(result["decision"], "held")
            self.assertIsNone(result["rider_id"])

    def test_unreviewed_missing_result_stays_held_and_1949_bonus_is_not_guessed(self):
        row = {**self.row, "shortname": "NED"}
        result = assess(row, self.identities, {(1966, "500cc", "NED"): {"ned"}}, {})
        self.assertEqual(result["decision"], "held")
        self.assertIsNone(expected_points(1949, 1))
        self.assertEqual(expected_points(1969, 1), 15)
        self.assertEqual(name_key("M\u00e1rquez, Marc"), name_key("Marc Marquez"))


if __name__ == "__main__":
    unittest.main()
