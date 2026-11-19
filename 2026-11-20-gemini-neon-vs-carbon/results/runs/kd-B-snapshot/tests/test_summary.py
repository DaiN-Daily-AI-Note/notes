import unittest

from ledger.summary import monthly


class MonthlySummaryTest(unittest.TestCase):
    def test_empty_entries_returns_empty_dict(self):
        self.assertEqual(monthly([]), {})

    def test_groups_by_kst_month_and_sorts_ascending(self):
        entries = [
            {"at": "2026-11-19T01:00:00Z", "item": "커피", "amount": 4500},
            {"at": "2026-10-31T14:59:59Z", "item": "점심", "amount": 10000},
            {"at": "2026-10-31T15:00:00Z", "item": "야식", "amount": 8000},
            {"at": "2025-12-31T16:00:00Z", "item": "새해커피", "amount": 5000},
        ]
        result = monthly(entries)
        self.assertEqual(list(result.keys()), ["2026-01", "2026-10", "2026-11"])
        self.assertEqual(
            result,
            {
                "2026-01": {"count": 1, "amount": 5000, "vat": 500},
                "2026-10": {"count": 1, "amount": 10000, "vat": 1000},
                "2026-11": {"count": 2, "amount": 12500, "vat": 1250},
            },
        )

    def test_vat_is_summed_per_entry_not_on_monthly_total(self):
        entries = [
            {"at": "2026-11-01T00:00:00Z", "item": "과자1", "amount": 25},
            {"at": "2026-11-02T00:00:00Z", "item": "과자2", "amount": 25},
        ]
        result = monthly(entries)
        # vat(25) + vat(25) = 3 + 3 = 6 (월 합계 50에 매기면 5)
        self.assertEqual(
            result,
            {"2026-11": {"count": 2, "amount": 50, "vat": 6}},
        )

    def test_negative_refund_entries_are_included_in_totals(self):
        entries = [
            {"at": "2026-11-10T03:00:00Z", "item": "셔츠", "amount": 4500},
            {"at": "2026-11-11T03:00:00Z", "item": "부분환불", "amount": -1500},
            {"at": "2026-12-01T00:00:00+09:00", "item": "사탕", "amount": 25},
            {"at": "2026-12-02T00:00:00+09:00", "item": "사탕환불", "amount": -25},
        ]
        result = monthly(entries)
        self.assertEqual(
            result,
            {
                "2026-11": {"count": 2, "amount": 3000, "vat": 300},
                "2026-12": {"count": 2, "amount": 0, "vat": 0},
            },
        )
