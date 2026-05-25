from django.test import TestCase
from django.urls import reverse

from families.tests.factories import make_kid, make_parent
from store.models import ItemType, StoreItem


class StoreAdminAccessTests(TestCase):
    def test_kid_blocked(self):
        alex = make_kid()
        self.client.force_login(alex)
        r = self.client.get(reverse("store:admin_list"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, "/")


class StoreAdminCreateTests(TestCase):
    def setUp(self):
        self.client.force_login(make_parent())

    def test_create_repeatable_item(self):
        r = self.client.post(reverse("store:admin_create"), {
            "name": "Screen time", "description": "30 min", "cost": 10,
            "type": ItemType.REPEATABLE, "stock_remaining": "",
        })
        self.assertRedirects(r, reverse("store:admin_list"))
        item = StoreItem.objects.get()
        self.assertEqual(item.name, "Screen time")
        self.assertEqual(item.type, ItemType.REPEATABLE)
        self.assertIsNone(item.stock_remaining)

    def test_create_limited_item_requires_stock(self):
        r = self.client.post(reverse("store:admin_create"), {
            "name": "Lego", "description": "", "cost": 100,
            "type": ItemType.LIMITED, "stock_remaining": "",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Limited-stock items need a stock count")
        self.assertFalse(StoreItem.objects.exists())

    def test_create_limited_item_with_stock(self):
        r = self.client.post(reverse("store:admin_create"), {
            "name": "Lego", "description": "", "cost": 100,
            "type": ItemType.LIMITED, "stock_remaining": 2,
        })
        self.assertRedirects(r, reverse("store:admin_list"))
        item = StoreItem.objects.get()
        self.assertEqual(item.stock_remaining, 2)


class StoreAdminArchiveTests(TestCase):
    def setUp(self):
        self.client.force_login(make_parent())
        self.item = StoreItem.objects.create(
            name="x", cost=5, type=ItemType.REPEATABLE,
        )

    def test_archive_toggles_is_active(self):
        self.client.post(reverse("store:admin_archive", args=[self.item.pk]))
        self.item.refresh_from_db()
        self.assertFalse(self.item.is_active)
        self.client.post(reverse("store:admin_archive", args=[self.item.pk]))
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_active)

    def test_archive_requires_post(self):
        r = self.client.get(reverse("store:admin_archive", args=[self.item.pk]))
        self.assertEqual(r.status_code, 405)
