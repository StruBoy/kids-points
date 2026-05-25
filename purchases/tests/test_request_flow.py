from django.test import TestCase
from django.urls import reverse

from families.tests.factories import (
    award,
    make_item,
    make_kid,
    make_parent,
    request_item,
)
from points.services import balance_for
from purchases.models import PurchaseRequest, PurchaseStatus
from store.models import ItemType


class RequestAccessTests(TestCase):
    def test_parent_blocked(self):
        item = make_item()
        self.client.force_login(make_parent())
        r = self.client.post(reverse("purchases:request_item", args=[item.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, "/")


class RequestFlowTests(TestCase):
    def setUp(self):
        self.mom = make_parent()
        self.alex = make_kid()
        self.client.force_login(self.alex)

    def test_successful_request_creates_pending_without_changing_balance(self):
        award(self.alex, 100, self.mom)
        item = make_item(name="Screen", cost=10)
        before = balance_for(self.alex)
        r = self.client.post(reverse("purchases:request_item", args=[item.pk]))
        self.assertRedirects(r, reverse("store:browse"))
        pr = PurchaseRequest.objects.get()
        self.assertEqual(pr.status, PurchaseStatus.PENDING)
        self.assertEqual(pr.cost_at_request, 10)
        self.assertEqual(pr.kid, self.alex)
        self.assertEqual(balance_for(self.alex), before)  # no deduction yet

    def test_price_locked_at_request_time(self):
        award(self.alex, 100, self.mom)
        item = make_item(cost=10)
        self.client.post(reverse("purchases:request_item", args=[item.pk]))
        pr = PurchaseRequest.objects.get()
        item.cost = 50
        item.save()
        pr.refresh_from_db()
        self.assertEqual(pr.cost_at_request, 10)

    def test_overdraft_blocked_accounting_for_pending(self):
        award(self.alex, 30, self.mom)
        item = make_item(cost=20)
        request_item(self.alex, item)  # existing pending: 20
        # available = 30 - 20 = 10. Item costs 20 → reject.
        r = self.client.post(
            reverse("purchases:request_item", args=[item.pk]), follow=True
        )
        self.assertContains(r, "don&#x27;t have enough points")
        # Only the pre-existing pending request remains.
        self.assertEqual(PurchaseRequest.objects.count(), 1)

    def test_sold_out_limited_item_rejected_at_request(self):
        award(self.alex, 100, self.mom)
        item = make_item(name="Gone", cost=1, type=ItemType.LIMITED, stock=0)
        r = self.client.post(
            reverse("purchases:request_item", args=[item.pk]), follow=True
        )
        self.assertContains(r, "is sold out")
        self.assertFalse(PurchaseRequest.objects.exists())

    def test_archived_item_404(self):
        award(self.alex, 100, self.mom)
        item = make_item(cost=1)
        item.is_active = False
        item.save()
        r = self.client.post(reverse("purchases:request_item", args=[item.pk]))
        self.assertEqual(r.status_code, 404)

    def test_get_not_allowed(self):
        item = make_item()
        r = self.client.get(reverse("purchases:request_item", args=[item.pk]))
        self.assertEqual(r.status_code, 405)
