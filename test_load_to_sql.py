import contextlib
import io
import unittest
from unittest.mock import Mock

import load_to_sql as loader


class LapRiderLookupTests(unittest.TestCase):
    def test_imports_pdf_laps_when_session_classification_is_empty(self):
        cursor = Mock()
        cursor.fetchall.side_effect = [[], [("bezzecchi-id", 72, "Marco BEZZECCHI")]]
        riders = [{
            "rider": "Marco BEZZECCHI", "number": 72,
            "laps": [{
                "lap": 1, "lap_time": "1:30.000", "T1": "20.000",
                "T2": "25.000", "T3": "20.000", "T4": "25.000", "speed": None,
            }],
        }]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            inserted = loader.insert_laps(cursor, "warmup-id", riders)
        self.assertEqual(inserted, 1)
        self.assertIn("empty session classification", output.getvalue())
        self.assertEqual(cursor.execute.call_args.args[1:4], ("warmup-id", "bezzecchi-id", 1))

    def test_session_classification_takes_priority_over_other_sessions(self):
        cursor = Mock()
        cursor.fetchall.side_effect = [
            [("current-rider", 72, "Current Rider")],
            [("other-rider", 72, "Other Rider")],
        ]
        by_number, by_surname = loader.build_rider_lookup(cursor, "session-id")
        self.assertEqual(loader.resolve_rider_id_fast(by_number, by_surname, "Current Rider", 72),
                         "current-rider")
        self.assertEqual(cursor.fetchall.call_count, 1)


if __name__ == "__main__":
    unittest.main()
