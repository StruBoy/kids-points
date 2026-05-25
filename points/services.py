from django.db.models import Sum

from purchases.models import PurchaseRequest, PurchaseStatus, SPENT_STATUSES

from .models import PointAward


def balance_for(kid) -> int:
    earned = PointAward.objects.filter(kid=kid).aggregate(
        s=Sum("amount")
    )["s"] or 0
    spent = PurchaseRequest.objects.filter(
        kid=kid, status__in=SPENT_STATUSES
    ).aggregate(s=Sum("cost_at_request"))["s"] or 0
    return int(earned) - int(spent)


def pending_total_for(kid) -> int:
    return int(PurchaseRequest.objects.filter(
        kid=kid, status=PurchaseStatus.PENDING
    ).aggregate(s=Sum("cost_at_request"))["s"] or 0)


def available_balance_for(kid) -> int:
    """Balance minus the cost of all pending requests."""
    return balance_for(kid) - pending_total_for(kid)


def history_for(kid):
    """Return list of (timestamp, kind, amount, label) newest first.

    kind is 'award' or 'spend'.
    """
    items = []
    for a in PointAward.objects.filter(kid=kid).select_related("awarded_by"):
        items.append({
            "ts": a.created_at,
            "kind": "award",
            "amount": a.amount,
            "label": a.reason,
            "actor": a.awarded_by.name,
        })
    spent_qs = PurchaseRequest.objects.filter(
        kid=kid, status__in=SPENT_STATUSES
    ).select_related("item")
    for p in spent_qs:
        items.append({
            "ts": p.decided_at or p.requested_at,
            "kind": "spend",
            "amount": p.cost_at_request,
            "label": p.item.name,
            "actor": None,
        })
    items.sort(key=lambda x: x["ts"], reverse=True)
    return items
