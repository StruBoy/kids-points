"""Render coverage + screenshots for admin surfaces and error states
that aren't part of the main happy path."""

from families.tests.factories import award, make_item, make_kid, make_parent
from store.models import ItemType

from .base import PlaywrightTestCase


class StoreAdminTests(PlaywrightTestCase):
    def setUp(self):
        super().setUp()
        self.mom = make_parent(name="Mom", username="mom", password="pw")
        make_item(name="30 min screen time", cost=10)
        make_item(
            name="Lego set", cost=50, type=ItemType.LIMITED, stock=2,
        )
        archived = make_item(name="Old item", cost=5)
        archived.is_active = False
        archived.save()
        self.login_parent("mom", "pw")

    def test_store_admin_list_and_forms(self):
        self.page.goto(self.url("/store/admin/"))
        self.shot("admin_list")
        self.assertTrue(self.page.get_by_text("30 min screen time").is_visible())
        self.assertTrue(self.page.get_by_text("Lego set").is_visible())
        # Archived still shown in admin list (with line-through styling)
        self.assertTrue(self.page.get_by_text("Old item").is_visible())

        self.page.click('a:has-text("Add item")')
        self.page.wait_for_url("**/store/admin/new/")
        self.shot("admin_form_empty")

        # Trigger the limited-stock validation error.
        self.page.fill('input[name="name"]', "Broken")
        self.page.fill('input[name="cost"]', "5")
        self.page.select_option('select[name="type"]', value="limited")
        self.page.click('button:has-text("Save")')
        self.shot("admin_form_limited_missing_stock")
        self.assertTrue(
            self.page.get_by_text("Limited-stock items need a stock count").is_visible()
        )

        # Fix it and save.
        self.page.fill('input[name="stock_remaining"]', "3")
        self.page.click('button:has-text("Save")')
        self.page.wait_for_url("**/store/admin/")
        self.shot("admin_list_after_create")
        self.assertTrue(self.page.get_by_text("Broken").is_visible())


class UserAdminTests(PlaywrightTestCase):
    def setUp(self):
        super().setUp()
        self.mom = make_parent(name="Mom", username="mom", password="pw")
        make_parent(name="Dad", username="dad", password="pw")
        make_kid(name="Alex", pin="1234")
        self.login_parent("mom", "pw")

    def test_user_admin_list_and_add_forms(self):
        self.page.goto(self.url("/users/"))
        self.shot("user_list")
        self.assertTrue(self.page.get_by_text("Alex", exact=True).is_visible())
        self.assertTrue(self.page.get_by_text("Dad", exact=True).is_visible())

        self.page.click('a:has-text("Add user")')
        self.page.wait_for_url("**/users/new/")
        self.shot("user_form_default_kid")
        # The role-aware JS should hide the password + username fields when
        # the kid role is selected (default).
        self.assertFalse(
            self.page.locator('input[name="password"]').is_visible()
        )
        self.assertTrue(
            self.page.locator('input[name="pin"]').is_visible()
        )

        # Switch to parent — username + password show, PIN hides.
        self.page.select_option('select[name="role"]', value="parent")
        self.shot("user_form_parent_selected")
        self.assertTrue(
            self.page.locator('input[name="username"]').is_visible()
        )
        self.assertTrue(
            self.page.locator('input[name="password"]').is_visible()
        )
        self.assertFalse(self.page.locator('input[name="pin"]').is_visible())

    def test_last_parent_archive_guard(self):
        # Archive Dad so Mom is the only active parent.
        self.page.goto(self.url("/users/"))
        # Find Dad's archive button.
        dad_row = self.page.locator("div.bg-white").filter(has_text="Dad")
        dad_row.locator('button:has-text("Archive")').click()
        self.page.wait_for_url("**/users/")
        self.shot("after_archiving_dad")

        # Try to archive Mom — should be blocked.
        mom_row = self.page.locator("div.bg-white").filter(has_text="Mom")
        mom_row.locator('button:has-text("Archive")').click()
        self.page.wait_for_url("**/users/")
        self.shot("last_parent_guard_blocks")
        self.assertTrue(
            self.page.get_by_text("Can't archive the last active parent").is_visible()
        )


class ErrorStateTests(PlaywrightTestCase):
    def setUp(self):
        super().setUp()
        self.mom = make_parent(name="Mom", username="mom", password="pw")
        self.alex = make_kid(name="Alex", pin="1234")
        # 60 points: enough to "buy" Lego (50) if it had stock, but not
        # enough for Expensive (100). Lets us cover both disabled-button
        # states in one screenshot.
        award(self.alex, 60, self.mom)
        self.lego = make_item(
            name="Lego set", cost=50, type=ItemType.LIMITED, stock=0,
        )
        self.expensive = make_item(name="Expensive thing", cost=100)

    def test_wrong_pin_shows_error(self):
        self.page.goto(self.url(f"/login/kid/{self.alex.pk}/"))
        self.page.fill('input[name="pin"]', "9999")
        self.page.click('button:has-text("Go")')
        self.shot("wrong_pin")
        self.assertTrue(
            self.page.get_by_text("That PIN didn't match").is_visible()
        )

    def test_wrong_parent_login_shows_error(self):
        self.page.goto(self.url("/login/parent/"))
        self.page.fill('input[name="username"]', "mom")
        self.page.fill('input[name="password"]', "wrong")
        self.page.click('button:has-text("Sign in")')
        self.shot("wrong_parent_password")
        self.assertTrue(
            self.page.get_by_text("Incorrect username or password").is_visible()
        )

    def test_kid_store_disabled_buttons(self):
        # Kid has 5 points, Expensive is 100 → "Not enough points".
        # Lego is sold out → "Sold out".
        self.login_kid(self.alex.pk, "1234")
        self.page.goto(self.url("/store/"))
        self.shot("kid_store_disabled_buttons")
        self.assertTrue(
            self.page.get_by_text("Not enough points").first.is_visible()
        )
        self.assertTrue(self.page.get_by_text("Sold out").is_visible())
