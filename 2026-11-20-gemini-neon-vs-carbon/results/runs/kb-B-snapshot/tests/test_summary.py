import unittest

from ledger.summary import monthly


class MonthlySummaryTest(unittest.TestCase):
    def test_empty_entries_returns_empty_dict(self):
        self.assertEqual(monthly([]), {})

    def test_groups_by_kst_month_boundary(self):
        entries = [
            {"at": "2026-10-31T14:59:59Z", "item": "점심", "amount": 10000},
            {"at": "2026-10-31T15:00:00Z", "item": "야식", "amount": 20000},
        ]
        self.assertEqual(
            monthly(entries),
            {
                "2026-10": {"count": 1, "amount": 10000, "vat": 1000},
                "2026-11": {"count": 1, "amount": 20000, "vat": 2000},
            },
        )

    def test_months_sorted_ascending(self):
        entries = [
            {"at": "2026-12-01T00:00:00+09:00", "item": "연말", "amount": 3000},
            {"at": "2025-12-31T00:00:00+09:00", "item": "작년", "amount": 1000},
            {"at": "2026-10-05T00:00:00+09:00", "item": "시월", "amount": 4000},
            {"at": "2026-09-15T00:00:00+09:00", "item": "구월", "amount": 2000},
        ]
        result = monthly(entries)
        self.assertEqual(list(result.keys()), ["2025-12", "2026-09", "2026-10", "2026-12"])

    def test_sums_per_entry_vat_instead_of_monthly_total_vat(self):
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
            {"at": "2026-11-10T01:00:00Z", "item": "결제", "amount": 10000},
            {"at": "2026-11-11T01:00:00Z", "item": "부분환불", "amount": -25},
        ]
        self.assertEqual(
            monthly(entries),
            {"2026-11": {"count": 2, "amount": 9975, "vat": 997}},
        )
