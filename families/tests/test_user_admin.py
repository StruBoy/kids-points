from django.test import TestCase
from django.urls import reverse

from families.models import Role, User

from .factories import make_kid, make_parent


class UserAdminAccessTests(TestCase):
    def test_kid_blocked_from_user_admin(self):
        alex = make_kid()
        self.client.force_login(alex)
        r = self.client.get(reverse("families:user_list"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, "/")

    def test_anonymous_redirected_to_login(self):
        r = self.client.get(reverse("families:user_list"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)


class UserAdminCreateTests(TestCase):
    def setUp(self):
        self.mom = make_parent(name="Mom", username="mom")
        self.client.force_login(self.mom)

    def test_create_kid_with_pin(self):
        r = self.client.post(reverse("families:user_create"), {
            "name": "Riley", "role": Role.KID, "pin": "4321",
            "username": "", "password": "",
        })
        self.assertRedirects(r, reverse("families:user_list"))
        riley = User.objects.get(name="Riley")
        self.assertEqual(riley.role, Role.KID)
        self.assertIsNone(riley.username)
        self.assertTrue(riley.check_password("4321"))

    def test_create_parent_with_password(self):
        r = self.client.post(reverse("families:user_create"), {
            "name": "Dad", "role": Role.PARENT,
            "username": "dad", "password": "secret",
            "pin": "",
        })
        self.assertRedirects(r, reverse("families:user_list"))
        dad = User.objects.get(name="Dad")
        self.assertEqual(dad.role, Role.PARENT)
        self.assertEqual(dad.username, "dad")
        self.assertTrue(dad.check_password("secret"))

    def test_kid_without_pin_rejected(self):
        r = self.client.post(reverse("families:user_create"), {
            "name": "X", "role": Role.KID, "pin": "",
            "username": "", "password": "",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Set a 4-digit PIN")
        self.assertFalse(User.objects.filter(name="X").exists())

    def test_parent_without_username_rejected(self):
        r = self.client.post(reverse("families:user_create"), {
            "name": "X", "role": Role.PARENT,
            "username": "", "password": "pw", "pin": "",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Parents need a username")
        self.assertFalse(User.objects.filter(name="X").exists())

    def test_parent_without_password_rejected_on_create(self):
        r = self.client.post(reverse("families:user_create"), {
            "name": "X", "role": Role.PARENT,
            "username": "x", "password": "", "pin": "",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Set a password")
        self.assertFalse(User.objects.filter(name="X").exists())


class UserAdminEditTests(TestCase):
    def setUp(self):
        self.mom = make_parent(name="Mom", username="mom", password="oldpw")
        self.alex = make_kid(name="Alex", pin="1234")
        self.client.force_login(self.mom)

    def test_edit_leaves_credential_unchanged_when_blank(self):
        r = self.client.post(reverse("families:user_edit", args=[self.alex.pk]), {
            "name": "Alex", "role": Role.KID, "pin": "",
            "username": "", "password": "",
        })
        self.assertRedirects(r, reverse("families:user_list"))
        self.alex.refresh_from_db()
        self.assertTrue(self.alex.check_password("1234"))

    def test_edit_resets_pin_when_provided(self):
        self.client.post(reverse("families:user_edit", args=[self.alex.pk]), {
            "name": "Alex", "role": Role.KID, "pin": "0000",
            "username": "", "password": "",
        })
        self.alex.refresh_from_db()
        self.assertTrue(self.alex.check_password("0000"))


class UserAdminArchiveTests(TestCase):
    def setUp(self):
        self.mom = make_parent(name="Mom", username="mom")
        self.dad = make_parent(name="Dad", username="dad")
        self.alex = make_kid(name="Alex", pin="1234")
        self.client.force_login(self.mom)

    def test_archive_kid_toggles_is_active(self):
        r = self.client.post(reverse("families:user_archive", args=[self.alex.pk]))
        self.assertRedirects(r, reverse("families:user_list"))
        self.alex.refresh_from_db()
        self.assertFalse(self.alex.is_active)

        # Toggling again restores.
        self.client.post(reverse("families:user_archive", args=[self.alex.pk]))
        self.alex.refresh_from_db()
        self.assertTrue(self.alex.is_active)

    def test_can_archive_one_parent_when_another_exists(self):
        r = self.client.post(reverse("families:user_archive", args=[self.dad.pk]))
        self.assertRedirects(r, reverse("families:user_list"))
        self.dad.refresh_from_db()
        self.assertFalse(self.dad.is_active)

    def test_cannot_archive_last_active_parent(self):
        # Archive Dad first so Mom is the only active parent.
        self.dad.is_active = False
        self.dad.save()
        r = self.client.post(reverse("families:user_archive", args=[self.mom.pk]), follow=True)
        self.mom.refresh_from_db()
        self.assertTrue(self.mom.is_active)
        self.assertContains(r, "Can&#x27;t archive the last active parent")

    def test_archive_requires_post(self):
        r = self.client.get(reverse("families:user_archive", args=[self.alex.pk]))
        self.assertEqual(r.status_code, 405)
