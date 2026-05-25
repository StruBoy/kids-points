from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from families.decorators import kid_required, parent_required

from .forms import StoreItemForm
from .models import StoreItem


@kid_required
def browse(request):
    from points.services import available_balance_for, balance_for
    from purchases.models import PurchaseRequest, PurchaseStatus

    items = StoreItem.objects.filter(is_active=True)
    pending = PurchaseRequest.objects.filter(
        kid=request.user, status=PurchaseStatus.PENDING
    ).select_related("item")
    return render(request, "store/browse.html", {
        "items": items,
        "pending": pending,
        "balance": balance_for(request.user),
        "available": available_balance_for(request.user),
    })


@parent_required
def admin_list(request):
    items = StoreItem.objects.all()
    return render(request, "store/admin_list.html", {"items": items})


@parent_required
@require_http_methods(["GET", "POST"])
def admin_create(request):
    if request.method == "POST":
        form = StoreItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Item added.")
            return redirect("store:admin_list")
    else:
        form = StoreItemForm()
    return render(request, "store/admin_form.html", {"form": form, "item": None})


@parent_required
@require_http_methods(["GET", "POST"])
def admin_edit(request, pk):
    item = get_object_or_404(StoreItem, pk=pk)
    if request.method == "POST":
        form = StoreItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Item saved.")
            return redirect("store:admin_list")
    else:
        form = StoreItemForm(instance=item)
    return render(request, "store/admin_form.html", {"form": form, "item": item})


@parent_required
@require_POST
def admin_archive(request, pk):
    item = get_object_or_404(StoreItem, pk=pk)
    item.is_active = not item.is_active
    item.save(update_fields=["is_active"])
    messages.success(
        request,
        f"{item.name} {'restored' if item.is_active else 'archived'}.",
    )
    return redirect("store:admin_list")
