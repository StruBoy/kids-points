from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from families.tests.factories import (
    award,
    make_kid,
    make_item,
    make_parent,
    request_item,
)
from purchases.models import PurchaseStatus


class ParentHomeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mom = make_parent()
        cls.alex = make_kid(name="Alex", pin="1234")
        cls.sam = make_kid(name="Sam", pin="5678")

    def setUp(self):
        self.client.force_login(self.mom)

    def test_lists_active_kids_with_balances(self):
        award(self.alex, 7, self.mom)
        r = self.client.get(reverse("points:parent_home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Alex")
        self.assertContains(r, "7 points")
        self.assertContains(r, "Sam")
        self.assertContains(r, "0 points")

    def test_pending_count_reflects_reality(self):
        item = make_item(cost=10)
        award(self.alex, 100, self.mom)
        request_item(self.alex, item)
        request_item(self.alex, item)
        r = self.client.get(reverse("points:parent_home"))
        self.assertContains(r, "2 waiting for approval")


class KidHomeTests(TestCase):
    def setUp(self):
        self.mom = make_parent()
        self.alex = make_kid(name="Alex", pin="1234")
        self.sam = make_kid(name="Sam", pin="5678")

    def test_kid_sees_own_balance_and_history(self):
        award(self.alex, 5, self.mom, reason="Made bed")
        award(self.alex, 3, self.mom, reason="Helped clean")
        self.client.force_login(self.alex)
        r = self.client.get(reverse("points:kid_home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, ">8<")  # balance number
        self.assertContains(r, "Made bed")
        self.assertContains(r, "Helped clean")

    def test_history_includes_approved_purchases_as_negative(self):
        award(self.alex, 50, self.mom)
        item = make_item(name="Screen time", cost=10)
        pr = request_item(self.alex, item)
        pr.status = PurchaseStatus.APPROVED
        pr.decided_at = timezone.now()
        pr.decided_by = self.mom
        pr.save()
        self.client.force_login(self.alex)
        r = self.client.get(reverse("points:kid_home"))
        self.assertContains(r, "Screen time")
        self.assertContains(r, "−10")

    def test_kid_does_not_see_other_kid_history(self):
        award(self.sam, 99, self.mom, reason="Sam reward")
        award(self.alex, 5, self.mom, reason="Alex reward")
        self.client.force_login(self.alex)
        r = self.client.get(reverse("points:kid_home"))
        self.assertContains(r, "Alex reward")
        self.assertNotContains(r, "Sam reward")
        self.assertNotContains(r, ">99<")

    def test_parent_redirected_away_from_kid_home(self):
        self.client.force_login(self.mom)
        r = self.client.get(reverse("points:kid_home"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, "/")
