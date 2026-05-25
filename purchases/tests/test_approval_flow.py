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


class ApprovalAccessTests(TestCase):
    def test_kid_blocked_from_queue(self):
        self.client.force_login(make_kid())
        r = self.client.get(reverse("purchases:queue"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, "/")

    def test_kid_blocked_from_approve(self):
        mom = make_parent()
        alex = make_kid()
        award(alex, 100, mom)
        pr = request_item(alex, make_item(cost=5))
        self.client.force_login(alex)
        r = self.client.post(reverse("purchases:approve", args=[pr.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, "/")
        pr.refresh_from_db()
        self.assertEqual(pr.status, PurchaseStatus.PENDING)


class QueueViewTests(TestCase):
    def setUp(self):
        self.mom = make_parent()
        self.alex = make_kid()
        award(self.alex, 100, self.mom)
        self.client.force_login(self.mom)

    def test_buckets(self):
        item = make_item(cost=10)
        pending = request_item(self.alex, item)
        approved = request_item(self.alex, item)
        approved.status = PurchaseStatus.APPROVED
        approved.save()
        fulfilled = request_item(self.alex, item)
        fulfilled.status = PurchaseStatus.FULFILLED
        fulfilled.save()
        denied = request_item(self.alex, item)
        denied.status = PurchaseStatus.DENIED
        denied.save()

        r = self.client.get(reverse("purchases:queue"))
        # Pending: only `pending` shows under "Waiting for approval"
        # Approved: only `approved` shows under "Approved (deliver these)"
        # Fulfilled and denied don't show in either bucket.
        self.assertContains(r, "Waiting for approval")
        self.assertContains(r, "Approved (deliver these)")
        # All four are for the same item name, so look at form actions instead.
        body = r.content.decode()
        self.assertIn(f"/purchases/{pending.pk}/approve/", body)
        self.assertNotIn(f"/purchases/{approved.pk}/approve/", body)
        self.assertIn(f"/purchases/{approved.pk}/fulfill/", body)
        self.assertNotIn(f"/purchases/{fulfilled.pk}/", body)
        self.assertNotIn(f"/purchases/{denied.pk}/", body)


class ApproveTests(TestCase):
    def setUp(self):
        self.mom = make_parent()
        self.alex = make_kid()
        self.client.force_login(self.mom)

    def test_approve_sets_metadata_and_deducts_balance(self):
        award(self.alex, 50, self.mom)
        item = make_item(cost=10)
        pr = request_item(self.alex, item)
        r = self.client.post(reverse("purchases:approve", args=[pr.pk]))
        self.assertRedirects(r, reverse("purchases:queue"))
        pr.refresh_from_db()
        self.assertEqual(pr.status, PurchaseStatus.APPROVED)
        self.assertEqual(pr.decided_by, self.mom)
        self.assertIsNotNone(pr.decided_at)
        self.assertEqual(balance_for(self.alex), 40)

    def test_approve_decrements_limited_stock(self):
        award(self.alex, 50, self.mom)
        item = make_item(cost=10, type=ItemType.LIMITED, stock=2)
        pr = request_item(self.alex, item)
        self.client.post(reverse("purchases:approve", args=[pr.pk]))
        item.refresh_from_db()
        self.assertEqual(item.stock_remaining, 1)

    def test_approve_rejected_when_balance_insufficient(self):
        """Two pending requests for 30 each, kid has 50.
        First approval succeeds (balance 20). Second must be rejected."""
        award(self.alex, 50, self.mom)
        item = make_item(cost=30)
        first = request_item(self.alex, item)
        second = request_item(self.alex, item)

        self.client.post(reverse("purchases:approve", args=[first.pk]))
        r = self.client.post(
            reverse("purchases:approve", args=[second.pk]), follow=True
        )
        self.assertContains(r, "doesn&#x27;t have enough points")
        second.refresh_from_db()
        self.assertEqual(second.status, PurchaseStatus.PENDING)
        self.assertEqual(balance_for(self.alex), 20)  # only first deducted

    def test_approve_rejected_when_stock_zero(self):
        award(self.alex, 50, self.mom)
        item = make_item(cost=5, type=ItemType.LIMITED, stock=1)
        a = request_item(self.alex, item)
        b = request_item(self.alex, item)
        self.client.post(reverse("purchases:approve", args=[a.pk]))
        r = self.client.post(
            reverse("purchases:approve", args=[b.pk]), follow=True
        )
        self.assertContains(r, "is out of stock")
        b.refresh_from_db()
        self.assertEqual(b.status, PurchaseStatus.PENDING)
        item.refresh_from_db()
        self.assertEqual(item.stock_remaining, 0)

    def test_cannot_re_approve(self):
        award(self.alex, 50, self.mom)
        item = make_item(cost=5)
        pr = request_item(self.alex, item)
        self.client.post(reverse("purchases:approve", args=[pr.pk]))
        r = self.client.post(
            reverse("purchases:approve", args=[pr.pk]), follow=True
        )
        self.assertContains(r, "no longer pending")
        # Balance only deducted once.
        self.assertEqual(balance_for(self.alex), 45)


class DenyTests(TestCase):
    def setUp(self):
        self.mom = make_parent()
        self.alex = make_kid()
        self.client.force_login(self.mom)

    def test_deny_sets_metadata_no_balance_change(self):
        award(self.alex, 50, self.mom)
        item = make_item(cost=10)
        pr = request_item(self.alex, item)
        self.client.post(reverse("purchases:deny", args=[pr.pk]))
        pr.refresh_from_db()
        self.assertEqual(pr.status, PurchaseStatus.DENIED)
        self.assertEqual(pr.decided_by, self.mom)
        self.assertEqual(balance_for(self.alex), 50)

    def test_denied_request_does_not_consume_stock(self):
        award(self.alex, 50, self.mom)
        item = make_item(cost=5, type=ItemType.LIMITED, stock=2)
        pr = request_item(self.alex, item)
        self.client.post(reverse("purchases:deny", args=[pr.pk]))
        item.refresh_from_db()
        self.assertEqual(item.stock_remaining, 2)

    def test_cannot_deny_already_approved(self):
        award(self.alex, 50, self.mom)
        pr = request_item(self.alex, make_item(cost=5))
        self.client.post(reverse("purchases:approve", args=[pr.pk]))
        r = self.client.post(
            reverse("purchases:deny", args=[pr.pk]), follow=True
        )
        self.assertContains(r, "no longer pending")
        pr.refresh_from_db()
        self.assertEqual(pr.status, PurchaseStatus.APPROVED)


class FulfillTests(TestCase):
    def setUp(self):
        self.mom = make_parent()
        self.alex = make_kid()
        self.client.force_login(self.mom)

    def test_fulfill_from_approved(self):
        award(self.alex, 50, self.mom)
        pr = request_item(self.alex, make_item(cost=5))
        self.client.post(reverse("purchases:approve", args=[pr.pk]))
        r = self.client.post(reverse("purchases:fulfill", args=[pr.pk]))
        self.assertRedirects(r, reverse("purchases:queue"))
        pr.refresh_from_db()
        self.assertEqual(pr.status, PurchaseStatus.FULFILLED)

    def test_cannot_fulfill_pending(self):
        award(self.alex, 50, self.mom)
        pr = request_item(self.alex, make_item(cost=5))
        r = self.client.post(
            reverse("purchases:fulfill", args=[pr.pk]), follow=True
        )
        self.assertContains(r, "Only approved requests")
        pr.refresh_from_db()
        self.assertEqual(pr.status, PurchaseStatus.PENDING)

    def test_cannot_fulfill_denied(self):
        award(self.alex, 50, self.mom)
        pr = request_item(self.alex, make_item(cost=5))
        self.client.post(reverse("purchases:deny", args=[pr.pk]))
        r = self.client.post(
            reverse("purchases:fulfill", args=[pr.pk]), follow=True
        )
        self.assertContains(r, "Only approved requests")
        pr.refresh_from_db()
        self.assertEqual(pr.status, PurchaseStatus.DENIED)

    def test_double_fulfill_is_a_no_op(self):
        award(self.alex, 50, self.mom)
        pr = request_item(self.alex, make_item(cost=5))
        self.client.post(reverse("purchases:approve", args=[pr.pk]))
        self.client.post(reverse("purchases:fulfill", args=[pr.pk]))
        r = self.client.post(
            reverse("purchases:fulfill", args=[pr.pk]), follow=True
        )
        self.assertContains(r, "Only approved requests")
