import unittest

from ledger.summary import monthly


class MonthlySummaryTest(unittest.TestCase):
    def test_empty_entries_returns_empty_dict(self):
        self.assertEqual(monthly([]), {})

    def test_groups_by_kst_month_and_sorts_months_ascending(self):
        entries = [
            {"at": "2026-11-15T02:00:00Z", "item": "점심", "amount": 10000},
            {"at": "2026-09-10T05:00:00Z", "item": "책", "amount": 20000},
            {"at": "2026-10-31T23:30:00Z", "item": "야식", "amount": 5000},
        ]
        result = monthly(entries)

        self.assertEqual(list(result.keys()), ["2026-09", "2026-11"])
        self.assertEqual(
            result,
            {
                "2026-09": {"count": 1, "amount": 20000, "vat": 2000},
                "2026-11": {"count": 2, "amount": 15000, "vat": 1500},
            },
        )

    def test_sums_vat_per_entry_instead_of_monthly_total(self):
        entries = [
            {"at": "2026-11-01T01:00:00Z", "item": "껌A", "amount": 25},
            {"at": "2026-11-02T01:00:00Z", "item": "껌B", "amount": 25},
        ]
        self.assertEqual(
            monthly(entries),
            {"2026-11": {"count": 2, "amount": 50, "vat": 6}},
        )

    def test_includes_negative_refund_entries(self):
        entries = [
            {"at": "2026-11-05T01:00:00Z", "item": "키보드", "amount": 10000},
            {"at": "2026-11-06T01:00:00Z", "item": "환불", "amount": -25},
        ]
        self.assertEqual(
            monthly(entries),
            {"2026-11": {"count": 2, "amount": 9975, "vat": 997}},
        )
