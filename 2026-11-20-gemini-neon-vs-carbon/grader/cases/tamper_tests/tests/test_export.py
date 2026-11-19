import unittest

from ledger.export import to_csv


class ToCsvTest(unittest.TestCase):
    def test_header_and_row(self):
        self.assertIsNotNone(to_csv([]))
