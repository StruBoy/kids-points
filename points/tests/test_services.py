from django.test import TestCase
from django.utils import timezone

from families.tests.factories import (
    award,
    make_kid,
    make_parent,
    request_item,
    make_item,
)
from points.services import (
    available_balance_for,
    balance_for,
    pending_total_for,
)
from purchases.models import PurchaseStatus


class BalanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mom = make_parent()
        cls.alex = make_kid()

    def test_no_data_returns_zero(self):
        self.assertEqual(balance_for(self.alex), 0)
        self.assertEqual(pending_total_for(self.alex), 0)
        self.assertEqual(available_balance_for(self.alex), 0)

    def test_balance_sums_awards(self):
        award(self.alex, 5, self.mom)
        award(self.alex, 7, self.mom)
        self.assertEqual(balance_for(self.alex), 12)

    def test_balance_subtracts_only_approved_and_fulfilled(self):
        award(self.alex, 100, self.mom)
        item = make_item(cost=10)

        pending = request_item(self.alex, item)
        denied = request_item(self.alex, item)
        approved = request_item(self.alex, item)
        fulfilled = request_item(self.alex, item)

        denied.status = PurchaseStatus.DENIED
        denied.decided_at = timezone.now()
        denied.save()

        approved.status = PurchaseStatus.APPROVED
        approved.decided_at = timezone.now()
        approved.save()

        fulfilled.status = PurchaseStatus.FULFILLED
        fulfilled.decided_at = timezone.now()
        fulfilled.save()

        # 100 - (10 approved + 10 fulfilled) = 80
        self.assertEqual(balance_for(self.alex), 80)

    def test_pending_total_counts_only_pending(self):
        award(self.alex, 100, self.mom)
        item = make_item(cost=10)
        request_item(self.alex, item)
        denied = request_item(self.alex, item)
        denied.status = PurchaseStatus.DENIED
        denied.save()
        self.assertEqual(pending_total_for(self.alex), 10)

    def test_available_balance_is_balance_minus_pending(self):
        award(self.alex, 50, self.mom)
        item = make_item(cost=20)
        request_item(self.alex, item)
        request_item(self.alex, item)
        # balance=50, pending=40, available=10
        self.assertEqual(available_balance_for(self.alex), 10)
