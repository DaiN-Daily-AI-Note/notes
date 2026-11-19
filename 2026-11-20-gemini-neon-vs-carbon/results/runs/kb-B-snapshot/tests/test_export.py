import unittest

from ledger.export import to_csv


class ToCsvTest(unittest.TestCase):
    def test_header_and_row(self):
        out = to_csv([{"at": "2026-11-19T01:00:00Z", "item": "커피", "amount": 4500}])
        self.assertEqual(out.splitlines()[0], "date,item,amount,vat")
        self.assertEqual(out.splitlines()[1], "2026-11-19,커피,4500,450")

    def test_empty_entries_has_header(self):
        self.assertEqual(to_csv([]), "date,item,amount,vat\n")
