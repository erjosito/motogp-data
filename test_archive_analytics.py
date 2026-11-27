import unittest

import numpy as np
import pandas as pd

from archive_analytics import complete_points, nominal_maximum, points_efficiency, qualifying_proxy


class ArchiveAnalyticsTests(unittest.TestCase):
    def test_efficiency_requires_supported_rules_and_complete_scores(self):
        self.assertTrue(np.isnan(complete_points(pd.Series([None, 3.0]))))
        maximum = nominal_maximum([1972, 1993, 2026, 2026, 2022], [2, 2, 1, 1, 1],
                                  [0, 0, 1, 0, 1], [0, 0, 0, 1, 0])
        np.testing.assert_allclose(maximum, [np.nan, 50, 37, np.nan, np.nan], equal_nan=True)
        np.testing.assert_allclose(points_efficiency([3, 32.5, 37, 25, 30], maximum),
                                   [np.nan, 65, 100, np.nan, np.nan], equal_nan=True)
        self.assertTrue(np.isnan(points_efficiency(26, 25)))

    def qualifying_data(self):
        qualifying = pd.DataFrame([
            dict(event_id="event", category="MotoGP", season_year=2026,
                 session_number=stage, rider_id=rider, position=position)
            for stage, riders in [(1, ["a", "b", "q1-only", "dns"]), (2, ["a", "b", *map(str, range(10))])]
            for position, rider in enumerate(riders, 1)
        ])
        races = pd.DataFrame([
            dict(event_id="event", category="MotoGP", season_year=2026, session_id=session,
                 rider_id=rider, finish_pos=position, status=status)
            for session in ["race", "sprint"]
            for rider, position, status in [
                ("a", 1, "INSTND"), ("b", None, "OUTSTND"),
                ("q1-only", 3, "INSTND"), ("dns", None, "NOTSTARTED"),
            ]
        ])
        return qualifying, races

    def test_proxy_keeps_q1_riders_dnf_and_distinct_races_without_duplicate_promotions(self):
        qualifying, races = self.qualifying_data()
        result = qualifying_proxy(qualifying, races)
        self.assertEqual(len(result), 6)
        self.assertEqual(result.groupby("session_id")["rider_id"].count().tolist(), [3, 3])
        self.assertEqual(result.loc[result["rider_id"].eq("q1-only"), "grid_pos"].tolist(), [13, 13])
        self.assertEqual(result["finish_pos"].isna().sum(), 2)

    def test_proxy_rejects_missing_starters_q1_q2_and_historical_formats(self):
        qualifying, races = self.qualifying_data()
        for removed in ["q1-only", "a", "0"]:
            with self.subTest(removed=removed):
                self.assertTrue(qualifying_proxy(
                    qualifying[~qualifying["rider_id"].eq(removed)], races
                ).empty)
        historical = qualifying.assign(category="500cc", season_year=1984)
        self.assertTrue(qualifying_proxy(historical, races.assign(category="500cc")).empty)
        unknown = races.copy()
        unknown.loc[unknown["rider_id"].eq("b"), "status"] = None
        self.assertTrue(qualifying_proxy(qualifying, unknown).empty)


if __name__ == "__main__":
    unittest.main()
