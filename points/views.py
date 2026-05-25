from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from families.decorators import kid_required, parent_required
from families.models import Role, User
from purchases.models import PurchaseRequest, PurchaseStatus

from .forms import AwardForm
from .models import PointAward
from .services import balance_for, history_for


@parent_required
def parent_home(request):
    kids = User.objects.filter(role=Role.KID, is_active=True)
    rows = [
        {"kid": k, "balance": balance_for(k)} for k in kids
    ]
    pending_count = PurchaseRequest.objects.filter(
        status=PurchaseStatus.PENDING
    ).count()
    return render(request, "points/parent_home.html", {
        "rows": rows,
        "pending_count": pending_count,
    })


@kid_required
def kid_home(request):
    return render(request, "points/kid_home.html", {
        "balance": balance_for(request.user),
        "history": history_for(request.user),
    })


@parent_required
@require_http_methods(["GET", "POST"])
def award(request):
    initial = {}
    if request.GET.get("kid"):
        initial["kid"] = request.GET.get("kid")
    if request.method == "POST":
        form = AwardForm(request.POST)
        if form.is_valid():
            PointAward.objects.create(
                kid=form.cleaned_data["kid"],
                awarded_by=request.user,
                amount=form.cleaned_data["amount"],
                reason=form.cleaned_data["reason"],
            )
            messages.success(
                request,
                f"Gave {form.cleaned_data['amount']} points to "
                f"{form.cleaned_data['kid'].name}.",
            )
            return redirect("points:parent_home")
    else:
        form = AwardForm(initial=initial)
    return render(request, "points/award.html", {"form": form})
