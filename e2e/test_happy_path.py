"""End-to-end happy path: a parent awards points, a kid spends them.

Walks the full flow across two roles and screenshots every meaningful surface.
Output lives in screenshots/HappyPathTests/test_full_purchase_cycle/.
"""

from families.tests.factories import make_item, make_kid, make_parent
from store.models import ItemType

from .base import PlaywrightTestCase


class HappyPathTests(PlaywrightTestCase):
    def setUp(self):
        super().setUp()
        self.mom = make_parent(name="Mom", username="mom", password="pw")
        make_parent(name="Dad", username="dad", password="pw")
        self.alex = make_kid(name="Alex", pin="1234")
        make_kid(name="Sam", pin="5678")
        self.screen_time = make_item(name="30 min screen time", cost=10)
        self.lego = make_item(
            name="Lego set", cost=50, type=ItemType.LIMITED, stock=2,
        )
        make_item(name="Pick the dinner menu", cost=20)

    def test_full_purchase_cycle(self):
        # 1. Login picker (anon)
        self.page.goto(self.url("/login/"))
        self.shot("login_picker")

        # 2. Parent login form
        self.page.click('a:has-text("I\'m a parent")')
        self.page.wait_for_url("**/login/parent/")
        self.shot("parent_login_form")

        # 3. Parent home after login (kids listed with balances)
        self.login_parent("mom", "pw")
        self.page.goto(self.url("/points/parent/"))
        self.shot("parent_home_initial")
        self.assertEqual(
            self.page.locator(
                'div:has-text("Alex") + .text-sm, '
                'div.text-sm:near(:text("Alex"))'
            ).first.text_content().strip(),
            "0 points",
        )

        # 4. Give points form
        self.page.click('a:has-text("Give points")')
        self.page.wait_for_url("**/points/award/")
        self.shot("give_points_form_empty")

        self.page.select_option('select[name="kid"]', label="Alex")
        self.page.fill('input[name="amount"]', "60")
        self.page.fill('input[name="reason"]', "Great week of chores")
        self.shot("give_points_form_filled")
        self.page.click('button:has-text("Give points")')

        # 5. Parent home reflects the new balance
        self.page.wait_for_url("**/points/parent/")
        self.shot("parent_home_after_award")
        # Alex should now have 60 points
        self.assertTrue(
            self.page.get_by_text("60 points").first.is_visible()
        )

        # 6. Switch to kid Alex
        self.switch_user()
        self.page.click('a:has-text("Alex")')
        self.page.wait_for_url(f"**/login/kid/{self.alex.pk}/")
        self.shot("kid_pin_entry")
        self.page.fill('input[name="pin"]', "1234")
        self.page.click('button:has-text("Go")')
        self.page.wait_for_url("**/points/kid/")
        self.shot("kid_home_with_balance")
        self.assertTrue(self.page.get_by_text("Great week of chores").is_visible())

        # 7. Kid visits store
        self.page.click('a:has-text("Visit the store")')
        self.page.wait_for_url("**/store/")
        self.shot("kid_store_browse")
        lego_card = self.page.locator("div.bg-white").filter(has_text="Lego set")
        self.assertTrue(
            lego_card.locator('button:has-text("Request")').is_visible()
        )

        # 8. Request the Lego set
        lego_card.locator('button:has-text("Request")').click()
        self.page.wait_for_url("**/store/")
        self.shot("kid_store_after_request")
        self.assertTrue(
            self.page.get_by_role("heading", name="Waiting for a parent").is_visible()
        )

        # 9. Switch back to parent
        self.switch_user()
        self.page.click('a:has-text("I\'m a parent")')
        self.login_parent("mom", "pw")
        self.page.goto(self.url("/points/parent/"))
        self.shot("parent_home_with_pending_badge")
        self.assertTrue(self.page.get_by_text("1 waiting for approval").is_visible())

        # 10. Parent purchase queue
        self.page.click('a:has-text("1 waiting for approval")')
        self.page.wait_for_url("**/purchases/queue/")
        self.shot("purchase_queue_with_pending")

        # 11. Approve the request
        self.page.click('button:has-text("Approve")')
        self.page.wait_for_url("**/purchases/queue/")
        self.shot("purchase_queue_after_approve")
        self.assertTrue(
            self.page.get_by_text("Approved Lego set for Alex").is_visible()
        )

        # 12. Fulfill (mark delivered)
        self.page.click('button:has-text("Mark fulfilled")')
        self.page.wait_for_url("**/purchases/queue/")
        self.shot("purchase_queue_after_fulfill")
        self.assertTrue(self.page.get_by_text("Nothing to deliver").is_visible())

        # 13. Verify Alex's history shows the spend
        self.switch_user()
        self.login_kid(self.alex.pk, "1234")
        self.page.goto(self.url("/points/kid/"))
        self.shot("kid_home_after_purchase")
        # Balance should be 60 - 50 = 10
        self.assertTrue(self.page.locator("text=10").first.is_visible())
        self.assertTrue(self.page.get_by_text("−50").is_visible())
        self.assertTrue(self.page.get_by_text("Lego set").is_visible())
