import unittest

from ledger.summary import monthly


class MonthlySummaryTest(unittest.TestCase):
    def test_empty_entries_returns_empty_dict(self):
        self.assertEqual(monthly([]), {})

    def test_groups_by_kst_month_and_sorts_ascending(self):
        entries = [
            {"at": "2026-12-05T02:00:00Z", "item": "책", "amount": 20000},
            {"at": "2026-10-31T15:00:00Z", "item": "야식", "amount": 10000},  # KST 2026-11-01
            {"at": "2026-10-15T01:00:00Z", "item": "커피", "amount": 4500},
            {"at": "2026-11-10T10:00:00+09:00", "item": "점심", "amount": 12000},
        ]
        result = monthly(entries)
        self.assertEqual(list(result.keys()), ["2026-10", "2026-11", "2026-12"])
        self.assertEqual(
            result,
            {
                "2026-10": {"count": 1, "amount": 4500, "vat": 450},
                "2026-11": {"count": 2, "amount": 22000, "vat": 2200},
                "2026-12": {"count": 1, "amount": 20000, "vat": 2000},
            },
        )

    def test_vat_is_summed_per_transaction(self):
        entries = [
            {"at": "2026-11-01T00:00:00Z", "item": "a", "amount": 15},
            {"at": "2026-11-02T00:00:00Z", "item": "b", "amount": 15},
        ]
        # vat(15) + vat(15) == 2 + 2 == 4 (not vat(30) == 3)
        self.assertEqual(
            monthly(entries),
            {"2026-11": {"count": 2, "amount": 30, "vat": 4}},
        )

    def test_negative_refund_included_in_totals(self):
        entries = [
            {"at": "2026-11-05T01:00:00Z", "item": "구매", "amount": 4500},
            {"at": "2026-11-06T01:00:00Z", "item": "부분환불", "amount": -1500},
            {"at": "2026-11-07T01:00:00Z", "item": "소액구매", "amount": 25},
            {"at": "2026-11-08T01:00:00Z", "item": "소액환불", "amount": -25},
        ]
        self.assertEqual(
            monthly(entries),
            {"2026-11": {"count": 4, "amount": 3000, "vat": 300}},
        )
