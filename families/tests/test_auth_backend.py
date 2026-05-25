from django.contrib.auth import authenticate
from django.test import TestCase

from families.auth import KidPinBackend

from .factories import make_kid, make_parent


class KidPinBackendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alex = make_kid(name="Alex", pin="1234")
        cls.mom = make_parent(name="Mom")

    def test_correct_pin_authenticates(self):
        u = authenticate(None, user_id=self.alex.pk, pin="1234")
        self.assertEqual(u, self.alex)

    def test_wrong_pin_rejected(self):
        self.assertIsNone(authenticate(None, user_id=self.alex.pk, pin="9999"))

    def test_archived_kid_rejected(self):
        self.alex.is_active = False
        self.alex.save()
        self.assertIsNone(authenticate(None, user_id=self.alex.pk, pin="1234"))

    def test_parent_user_id_rejected(self):
        # Even if you somehow pass the parent's pk + their password, the
        # backend only matches kids.
        self.assertIsNone(authenticate(None, user_id=self.mom.pk, pin="pw"))

    def test_missing_args_returns_none(self):
        backend = KidPinBackend()
        self.assertIsNone(backend.authenticate(None))
        self.assertIsNone(backend.authenticate(None, user_id=self.alex.pk))
        self.assertIsNone(backend.authenticate(None, pin="1234"))
