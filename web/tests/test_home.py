from django.test import TestCase
from django.urls import reverse

from families.tests.factories import make_kid, make_parent


class HomeRedirectTests(TestCase):
    def test_parent_redirected_to_parent_home(self):
        self.client.force_login(make_parent())
        r = self.client.get(reverse("web:home"))
        self.assertRedirects(r, reverse("points:parent_home"))

    def test_kid_redirected_to_kid_home(self):
        self.client.force_login(make_kid())
        r = self.client.get(reverse("web:home"))
        self.assertRedirects(r, reverse("points:kid_home"))

    def test_anonymous_redirected_to_login(self):
        r = self.client.get(reverse("web:home"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)
