from django.test import TestCase
from django.urls import reverse

from .factories import make_kid, make_parent


class LoginPickerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alex = make_kid(name="Alex", pin="1234")
        cls.sam = make_kid(name="Sam", pin="5678")
        cls.archived = make_kid(name="Old", pin="0000")
        cls.archived.is_active = False
        cls.archived.save()
        cls.mom = make_parent(name="Mom")

    def test_lists_active_kids_only(self):
        r = self.client.get(reverse("families:login_picker"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Alex")
        self.assertContains(r, "Sam")
        self.assertNotContains(r, "Old")

    def test_authenticated_user_redirects_home(self):
        self.client.force_login(self.mom)
        r = self.client.get(reverse("families:login_picker"))
        self.assertRedirects(r, "/", target_status_code=302)


class ParentLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mom = make_parent(name="Mom", username="mom", password="pw")
        cls.alex = make_kid(name="Alex", pin="1234")

    def test_valid_credentials_log_in(self):
        r = self.client.post(reverse("families:parent_login"), {
            "username": "mom", "password": "pw",
        })
        self.assertRedirects(r, "/", target_status_code=302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.mom.pk)

    def test_wrong_password_rerenders_with_error(self):
        r = self.client.post(reverse("families:parent_login"), {
            "username": "mom", "password": "nope",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Incorrect username or password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_kid_cannot_use_parent_login(self):
        # Kid has no usable username, and authenticate() requires one
        # for ModelBackend. Even if it succeeded, the view rejects non-parents.
        r = self.client.post(reverse("families:parent_login"), {
            "username": "alex", "password": "1234",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Incorrect username or password.")


class KidLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alex = make_kid(name="Alex", pin="1234")

    def test_valid_pin_logs_in(self):
        url = reverse("families:kid_login", args=[self.alex.pk])
        r = self.client.post(url, {"pin": "1234"})
        self.assertRedirects(r, "/", target_status_code=302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.alex.pk)

    def test_wrong_pin_rerenders_with_error(self):
        url = reverse("families:kid_login", args=[self.alex.pk])
        r = self.client.post(url, {"pin": "9999"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "PIN didn")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_archived_kid_404(self):
        self.alex.is_active = False
        self.alex.save()
        url = reverse("families:kid_login", args=[self.alex.pk])
        self.assertEqual(self.client.get(url).status_code, 404)


class LogoutTests(TestCase):
    def test_logout_clears_session_and_redirects_to_picker(self):
        mom = make_parent()
        self.client.force_login(mom)
        r = self.client.get(reverse("families:logout"))
        self.assertRedirects(r, reverse("families:login_picker"))
        self.assertNotIn("_auth_user_id", self.client.session)
