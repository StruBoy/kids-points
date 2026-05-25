"""Plain-function factories for tests. No factory_boy needed at this scale."""

from families.models import User
from points.models import PointAward
from purchases.models import PurchaseRequest, PurchaseStatus
from store.models import ItemType, StoreItem


def make_parent(name="Mom", username=None, password="pw"):
    return User.objects.create_parent(
        name=name,
        username=username or name.lower(),
        password=password,
    )


def make_kid(name="Alex", pin="1234"):
    return User.objects.create_kid(name=name, pin=pin)


def make_item(name="Item", cost=10, type=ItemType.REPEATABLE, stock=None):
    return StoreItem.objects.create(
        name=name,
        cost=cost,
        type=type,
        stock_remaining=stock,
    )


def award(kid, amount, by, reason="ok"):
    return PointAward.objects.create(
        kid=kid, awarded_by=by, amount=amount, reason=reason
    )


def request_item(kid, item):
    return PurchaseRequest.objects.create(
        kid=kid, item=item, cost_at_request=item.cost
    )


def login_as(client, user):
    """Skip the password/PIN dance for non-auth tests."""
    client.force_login(user)
