from django.test import TestCase
from django.urls import reverse

from families.tests.factories import make_kid, make_parent
from points.models import PointAward
from points.services import balance_for


class AwardViewAccessTests(TestCase):
    def test_kid_blocked(self):
        alex = make_kid()
        self.client.force_login(alex)
        r = self.client.get(reverse("points:award"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, "/")

    def test_anonymous_redirects_to_login(self):
        r = self.client.get(reverse("points:award"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)


class AwardViewPostTests(TestCase):
    def setUp(self):
        self.mom = make_parent()
        self.alex = make_kid(name="Alex", pin="1234")
        self.client.force_login(self.mom)

    def test_valid_post_creates_award_and_updates_balance(self):
        r = self.client.post(reverse("points:award"), {
            "kid": self.alex.pk,
            "amount": 5,
            "reason": "Made bed",
        })
        self.assertRedirects(r, reverse("points:parent_home"))
        a = PointAward.objects.get()
        self.assertEqual(a.kid, self.alex)
        self.assertEqual(a.awarded_by, self.mom)
        self.assertEqual(a.amount, 5)
        self.assertEqual(a.reason, "Made bed")
        self.assertEqual(balance_for(self.alex), 5)

    def test_amount_zero_rejected(self):
        r = self.client.post(reverse("points:award"), {
            "kid": self.alex.pk, "amount": 0, "reason": "x",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(PointAward.objects.exists())

    def test_missing_reason_rejected(self):
        r = self.client.post(reverse("points:award"), {
            "kid": self.alex.pk, "amount": 5, "reason": "",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(PointAward.objects.exists())

    def test_non_kid_target_rejected(self):
        other_parent = make_parent(name="Dad", username="dad")
        r = self.client.post(reverse("points:award"), {
            "kid": other_parent.pk, "amount": 5, "reason": "x",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(PointAward.objects.exists())
