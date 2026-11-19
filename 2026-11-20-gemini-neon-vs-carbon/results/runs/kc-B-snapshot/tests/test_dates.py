import unittest
from datetime import date

from ledger.dates import parse_kst


class ParseKstTest(unittest.TestCase):
    def test_late_utc_is_next_day_in_kst(self):
        self.assertEqual(parse_kst("2026-11-15T23:00:05Z"), date(2026, 11, 16))

    def test_explicit_offsets_convert_to_kst(self):
        self.assertEqual(parse_kst("2026-11-16T00:30:00+09:00"), date(2026, 11, 16))
        self.assertEqual(parse_kst("2026-11-15T18:00:00-05:00"), date(2026, 11, 16))
