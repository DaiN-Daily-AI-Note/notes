import unittest

from ledger.money import vat


class VatTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(vat(10000), 1000)

    def test_half_rounds_up(self):
        self.assertEqual(vat(25), 3)  # 2.5 -> 3
        self.assertEqual(vat(15), 2)  # 1.5 -> 2
        self.assertEqual(vat(24), 2)  # 2.4 -> 2
        self.assertEqual(vat(-25), -3)  # 환불(-2.5 -> -3)
        self.assertEqual(vat(0), 0)
