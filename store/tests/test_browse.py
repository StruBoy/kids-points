from django.test import TestCase
from django.urls import reverse

from families.tests.factories import (
    award,
    make_item,
    make_kid,
    make_parent,
    request_item,
)
from store.models import ItemType


class StoreBrowseAccessTests(TestCase):
    def test_parent_blocked(self):
        self.client.force_login(make_parent())
        r = self.client.get(reverse("store:browse"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, "/")


class StoreBrowseContentTests(TestCase):
    def setUp(self):
        self.mom = make_parent()
        self.alex = make_kid()
        self.client.force_login(self.alex)

    def test_archived_items_hidden(self):
        live = make_item(name="Live")
        hidden = make_item(name="Hidden")
        hidden.is_active = False
        hidden.save()
        r = self.client.get(reverse("store:browse"))
        self.assertContains(r, "Live")
        self.assertNotContains(r, "Hidden")

    def test_pending_requests_pinned_at_top(self):
        award(self.alex, 100, self.mom)
        item = make_item(name="Screen time", cost=10)
        request_item(self.alex, item)
        r = self.client.get(reverse("store:browse"))
        self.assertContains(r, "Waiting for a parent")
        self.assertContains(r, "Screen time")

    def test_disabled_button_when_too_expensive(self):
        award(self.alex, 5, self.mom)
        make_item(name="Pricey", cost=999)
        r = self.client.get(reverse("store:browse"))
        self.assertContains(r, "Not enough points")

    def test_disabled_button_when_sold_out(self):
        award(self.alex, 1000, self.mom)
        make_item(name="Gone", cost=1, type=ItemType.LIMITED, stock=0)
        r = self.client.get(reverse("store:browse"))
        self.assertContains(r, "Sold out")
