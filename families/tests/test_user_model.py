from django.test import TestCase

from families.models import Role, User


class UserModelTests(TestCase):
    def test_create_parent_sets_fields_and_hashes_password(self):
        u = User.objects.create_parent(name="Mom", username="mom", password="secret")
        self.assertEqual(u.role, Role.PARENT)
        self.assertEqual(u.username, "mom")
        self.assertTrue(u.is_parent)
        self.assertFalse(u.is_kid)
        self.assertNotEqual(u.password, "secret")
        self.assertTrue(u.check_password("secret"))

    def test_create_kid_sets_fields_and_hashes_pin(self):
        u = User.objects.create_kid(name="Alex", pin="1234")
        self.assertEqual(u.role, Role.KID)
        self.assertIsNone(u.username)
        self.assertTrue(u.is_kid)
        self.assertFalse(u.is_parent)
        self.assertTrue(u.check_password("1234"))
        self.assertFalse(u.check_password("9999"))
