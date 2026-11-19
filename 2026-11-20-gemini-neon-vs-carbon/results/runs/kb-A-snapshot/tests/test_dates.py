import unittest
from datetime import date

from ledger.dates import parse_kst


class ParseKstTest(unittest.TestCase):
    def test_late_utc_is_next_day_in_kst(self):
        self.assertEqual(parse_kst("2026-11-15T23:00:05Z"), date(2026, 11, 16))
        self.assertEqual(parse_kst("2026-11-19T15:00:00Z"), date(2026, 11, 20))
        self.assertEqual(parse_kst("2026-11-19T14:59:59Z"), date(2026, 11, 19))

    def test_explicit_offset_to_kst(self):
        self.assertEqual(parse_kst("2026-11-19T00:30:00+09:00"), date(2026, 11, 19))
        self.assertEqual(parse_kst("2026-11-19T12:00:00-05:00"), date(2026, 11, 20))
