import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "motogp_results", Path(__file__).with_name("Get-MotoGPResults.py")
)
motogp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(motogp)


class LatestRaceEventTests(unittest.TestCase):
    def test_preserves_historical_500cc_category_alias(self):
        with patch.object(
            motogp, "api_get", return_value=[{"id": "historical", "name": "500cc"}]
        ):
            self.assertEqual(
                motogp.get_category_id("event", "MotoGP"), ("historical", "500cc")
            )

    def test_skips_event_without_finished_main_race(self):
        events = [
            {"id": "portugal", "date_end": "2026-11-22"},
            {"id": "valencia", "date_end": "2026-11-29"},
            {"id": "test", "date_end": "2026-12-01", "test": True},
        ]
        sessions = {
            "valencia": [
                {"type": "SPR", "status": "FINISHED", "date": "2026-11-28"},
                {"type": "RAC", "status": "NOT-STARTED", "date": "2026-11-29"},
            ],
            "portugal": [
                {"type": "RAC", "status": "FINISHED", "date": "2026-11-22"},
            ],
        }

        def api_get(endpoint, params):
            if endpoint == "events":
                return events
            return sessions[params["eventUuid"]]

        with patch.object(motogp, "api_get", side_effect=api_get), patch.object(
            motogp, "get_category_id", return_value=("category", "Moto2")
        ) as get_category:
            event = motogp.get_latest_race_event("season", "Moto2")

        self.assertEqual(event["id"], "portugal")
        self.assertEqual(
            get_category.call_args_list,
            [unittest.mock.call("valencia", "Moto2"),
             unittest.mock.call("portugal", "Moto2")],
        )

    def test_returns_latest_completed_race(self):
        events = [
            {"id": "older", "date_end": "2026-11-08"},
            {"id": "latest", "date_end": "2026-11-22"},
        ]
        with patch.object(motogp, "api_get", return_value=events), patch.object(
            motogp, "get_category_id", return_value=("category", "MotoGP")
        ), patch.object(
            motogp, "get_all_sessions", return_value=[{"type": "RAC"}]
        ):
            self.assertEqual(motogp.get_latest_race_event("season")["id"], "latest")

    def test_reports_no_completed_race(self):
        with patch.object(
            motogp, "api_get",
            return_value=[{"id": "upcoming", "date_end": "2026-11-29"}],
        ), patch.object(
            motogp, "get_category_id", return_value=("category", "MotoGP")
        ), patch.object(motogp, "get_all_sessions", return_value=[]):
            with self.assertRaisesRegex(SystemExit, "No finished MotoGP race"):
                motogp.get_latest_race_event("season")


class AnalysisParserTests(unittest.TestCase):
    header = (
        "Marco BEZZECCHI APRILIA ITA\n"
        "1st 72\n"
        "Aprilia Racing\n"
        "Run # 1 Front Tyre Slick-Medium Rear Tyre Slick-Medium\n"
    )

    def test_includes_pit_laps_and_missing_speeds(self):
        riders = motogp.parse_analysis_column(
            self.header
            + "1 10'04.458 23.135 32.190 16.226 32.018\n"
            + "2 2'04.370 P 26.497 31.873 * 15.994 50.006 340.6\n"
        )
        self.assertEqual(len(riders[0]["laps"]), 2)
        first, second = riders[0]["laps"]
        self.assertIsNone(first["speed"])
        self.assertFalse(first["pit"])
        self.assertTrue(second["pit"])
        self.assertEqual(second["speed"], 340.6)
        self.assertEqual(second["T3"], "15.994")

    def test_retains_lower_class_lap_when_sector_cells_are_blank(self):
        riders = motogp.parse_analysis_column(
            "Senna AGIUS LIQUI MOLY Dynavolt AUS\n23rd 81\n"
            "1 1'38.025 22.667 28.171 22.488 24.699 271.3\n"
            "2 1'35.740 20.604 24.663 276.9\n"
        )
        self.assertEqual(len(riders[0]["laps"]), 2)
        partial = riders[0]["laps"][1]
        self.assertEqual(partial["lap_time"], "1:35.740")
        self.assertEqual(partial["lap"], 2)
        for field in ["T1", "T2", "T3", "T4", "speed"]:
            self.assertIsNone(partial[field])
        self.assertEqual(riders[0]["laps"][0]["T2"], "28.171")

    def test_preserves_historical_rider_headers(self):
        headers = [
            ("1st 12 Maverick VINALES YAMAHA S\nMovistar Yamaha MotoGP\n",
             "Maverick VINALES", 12),
            ("Jorge LORENZO Movistar Yamaha Mot S\n1st 99\n",
             "Jorge LORENZO", 99),
            ("Marco BEZZECCHI APRILIA I\n1st 72\nAprilia Racing\n",
             "Marco BEZZECCHI", 72),
        ]
        for header, name, number in headers:
            with self.subTest(header=header):
                riders = motogp.parse_analysis_column(
                    header + "1 1'40.258 22.082 30.618 15.882 31.676 335.4\n"
                )
                self.assertEqual(len(riders), 1)
                self.assertEqual(riders[0]["rider"], name)
                self.assertEqual(riders[0]["number"], number)
                self.assertEqual(len(riders[0]["laps"]), 1)

    def test_preserves_rider_and_tyre_state_across_columns_and_pages(self):
        texts = iter([
            self.header + "1 1'43.458 24.355 31.475 16.067 31.561\n",
            "2 1'40.258 22.082 30.618 15.882 31.676 335.4\n",
            "3 1'39.325 22.131 30.405 15.457 31.332 345.0\n",
            "4 1'39.159 21.934 30.409 15.435 31.381 340.6\n",
        ])
        page = SimpleNamespace(
            width=600, height=800,
            crop=lambda bounds: SimpleNamespace(extract_text=lambda: next(texts)),
        )
        with patch.object(motogp.pdfplumber, "open") as open_pdf:
            open_pdf.return_value.__enter__.return_value.pages = [page, page]
            riders = motogp.parse_analysis_pdf(b"pdf")

        self.assertEqual(len(riders), 1)
        self.assertEqual([lap["lap"] for lap in riders[0]["laps"]], [1, 2, 3, 4])
        self.assertTrue(all(
            lap["front_tyre"] == "Slick-Medium" and lap["run"] == 1
            for lap in riders[0]["laps"]
        ))

    def test_handles_long_sectors_and_cancellation_marker_variants(self):
        riders = motogp.parse_analysis_column(
            self.header
            + "1 3'52.067 P 1'56.805 44.785 19.048 51.429 347.2\n"
            + "2 3'01.180 P 24.623 57.927 33.492 1'05.138 328.2\n"
            + "3 3'23.842 P 22.204 31.941 * 19.589* 56.610\n"
            + "4 1'46.814 * 23.090 32.191 16.579 34.954 * 338.5\n"
        )
        laps = riders[0]["laps"]
        self.assertEqual(len(laps), 4)
        self.assertEqual(laps[0]["T1"], "1:56.805")
        self.assertEqual(laps[1]["T4"], "1:05.138")
        self.assertEqual(laps[2]["T3"], "19.589")
        self.assertEqual(laps[3]["speed"], 338.5)

    def test_best_lap_highlight_uses_numeric_time(self):
        riders = motogp.parse_analysis_column(
            self.header
            + "1 10'04.458 23.135 32.190 16.226 32.018\n"
            + "2 1'40.258 22.082 30.618 15.882 31.676 335.4\n"
        )
        workbook = motogp.Workbook()
        sheet = workbook.active
        motogp.write_lap_analysis_sheet(
            sheet, {"type": "FP", "number": 1}, {}, "MotoGP", riders
        )
        self.assertFalse(sheet["E5"].font.bold)
        self.assertTrue(sheet["E6"].font.bold)


if __name__ == "__main__":
    unittest.main()
