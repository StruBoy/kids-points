from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from families.decorators import kid_required, parent_required
from store.models import StoreItem

from .models import PurchaseRequest, PurchaseStatus


@kid_required
@require_POST
def request_item(request, item_id):
    from points.services import available_balance_for

    item = get_object_or_404(StoreItem, pk=item_id, is_active=True)
    available = available_balance_for(request.user)
    if item.cost > available:
        messages.error(
            request,
            f"You don't have enough points for {item.name} "
            f"(need {item.cost}, have {available} after pending requests).",
        )
        return redirect("store:browse")
    if item.is_limited and not item.in_stock:
        messages.error(request, f"{item.name} is sold out.")
        return redirect("store:browse")

    PurchaseRequest.objects.create(
        kid=request.user,
        item=item,
        cost_at_request=item.cost,
    )
    messages.success(
        request,
        f"Requested {item.name}. Waiting for a parent to approve.",
    )
    return redirect("store:browse")


@parent_required
def queue(request):
    pending = PurchaseRequest.objects.filter(
        status=PurchaseStatus.PENDING
    ).select_related("kid", "item")
    approved = PurchaseRequest.objects.filter(
        status=PurchaseStatus.APPROVED
    ).select_related("kid", "item")
    return render(request, "purchases/queue.html", {
        "pending": pending,
        "approved": approved,
    })


@parent_required
@require_POST
def approve(request, pk):
    from points.services import balance_for

    with transaction.atomic():
        pr = get_object_or_404(
            PurchaseRequest.objects.select_for_update(), pk=pk
        )
        if pr.status != PurchaseStatus.PENDING:
            messages.error(request, "Request is no longer pending.")
            return redirect("purchases:queue")

        if balance_for(pr.kid) < pr.cost_at_request:
            messages.error(
                request,
                f"{pr.kid.name} doesn't have enough points anymore.",
            )
            return redirect("purchases:queue")

        if pr.item.is_limited:
            item = StoreItem.objects.select_for_update().get(pk=pr.item_id)
            if not item.in_stock:
                messages.error(request, f"{item.name} is out of stock.")
                return redirect("purchases:queue")
            item.stock_remaining -= 1
            item.save(update_fields=["stock_remaining"])

        pr.status = PurchaseStatus.APPROVED
        pr.decided_at = timezone.now()
        pr.decided_by = request.user
        pr.save(update_fields=["status", "decided_at", "decided_by"])

    messages.success(
        request, f"Approved {pr.item.name} for {pr.kid.name}."
    )
    return redirect("purchases:queue")


@parent_required
@require_POST
def deny(request, pk):
    pr = get_object_or_404(PurchaseRequest, pk=pk)
    if pr.status != PurchaseStatus.PENDING:
        messages.error(request, "Request is no longer pending.")
        return redirect("purchases:queue")
    pr.status = PurchaseStatus.DENIED
    pr.decided_at = timezone.now()
    pr.decided_by = request.user
    pr.save(update_fields=["status", "decided_at", "decided_by"])
    messages.success(request, f"Denied {pr.item.name} for {pr.kid.name}.")
    return redirect("purchases:queue")


@parent_required
@require_POST
def fulfill(request, pk):
    pr = get_object_or_404(PurchaseRequest, pk=pk)
    if pr.status != PurchaseStatus.APPROVED:
        messages.error(request, "Only approved requests can be fulfilled.")
        return redirect("purchases:queue")
    pr.status = PurchaseStatus.FULFILLED
    pr.save(update_fields=["status"])
    messages.success(request, f"Marked {pr.item.name} as fulfilled.")
    return redirect("purchases:queue")
