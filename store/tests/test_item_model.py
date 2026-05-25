from django.test import TestCase

from store.models import ItemType, StoreItem


class StoreItemTests(TestCase):
    def test_repeatable_is_always_in_stock(self):
        i = StoreItem.objects.create(name="x", cost=1, type=ItemType.REPEATABLE)
        self.assertFalse(i.is_limited)
        self.assertTrue(i.in_stock)

    def test_limited_in_stock_when_positive(self):
        i = StoreItem.objects.create(
            name="x", cost=1, type=ItemType.LIMITED, stock_remaining=3,
        )
        self.assertTrue(i.is_limited)
        self.assertTrue(i.in_stock)

    def test_limited_out_of_stock_at_zero(self):
        i = StoreItem.objects.create(
            name="x", cost=1, type=ItemType.LIMITED, stock_remaining=0,
        )
        self.assertFalse(i.in_stock)

    def test_limited_with_null_stock_treated_as_zero(self):
        i = StoreItem.objects.create(
            name="x", cost=1, type=ItemType.LIMITED, stock_remaining=None,
        )
        self.assertFalse(i.in_stock)
