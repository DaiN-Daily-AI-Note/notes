import unittest
from datetime import date

from ledger.dates import parse_kst


class ParseKstTest(unittest.TestCase):
    def test_late_utc_is_next_day_in_kst(self):
        self.assertEqual(parse_kst("2026-11-15T23:00:05Z"), date(2026, 11, 15))
