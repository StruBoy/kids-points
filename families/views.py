from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from .decorators import parent_required
from .forms import UserAdminForm
from .models import Role, User


def login_picker(request):
    if request.user.is_authenticated:
        return redirect("/")
    kids = User.objects.filter(role=Role.KID, is_active=True)
    return render(request, "families/login_picker.html", {"kids": kids})


@require_http_methods(["GET", "POST"])
def parent_login(request):
    if request.user.is_authenticated:
        return redirect("/")
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user and user.is_active and user.is_parent:
            login(request, user)
            return redirect("/")
        error = "Incorrect username or password."
    return render(request, "families/parent_login.html", {"error": error})


@require_http_methods(["GET", "POST"])
def kid_login(request, user_id):
    if request.user.is_authenticated:
        return redirect("/")
    kid = get_object_or_404(
        User, pk=user_id, role=Role.KID, is_active=True
    )
    error = None
    if request.method == "POST":
        pin = request.POST.get("pin", "")
        user = authenticate(request, user_id=kid.pk, pin=pin)
        if user:
            login(request, user)
            return redirect("/")
        error = "That PIN didn't match. Try again."
    return render(request, "families/kid_login.html", {"kid": kid, "error": error})


def logout_view(request):
    logout(request)
    return redirect("families:login_picker")


@parent_required
def user_list(request):
    users = User.objects.all().order_by("-is_active", "role", "name")
    return render(request, "families/user_list.html", {"users": users})


@parent_required
@require_http_methods(["GET", "POST"])
def user_create(request):
    if request.method == "POST":
        form = UserAdminForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Added {user.name}.")
            return redirect("families:user_list")
    else:
        form = UserAdminForm(initial={"role": Role.KID})
    return render(request, "families/user_form.html", {"form": form, "target": None})


@parent_required
@require_http_methods(["GET", "POST"])
def user_edit(request, pk):
    target = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = UserAdminForm(request.POST, request.FILES, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, f"Saved {target.name}.")
            return redirect("families:user_list")
    else:
        form = UserAdminForm(instance=target)
    return render(request, "families/user_form.html", {"form": form, "target": target})


@parent_required
@require_POST
def user_archive(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target.role == Role.PARENT and target.is_active:
        active_parents = User.objects.filter(
            role=Role.PARENT, is_active=True
        ).count()
        if active_parents <= 1:
            messages.error(
                request,
                "Can't archive the last active parent.",
            )
            return redirect("families:user_list")
    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    messages.success(
        request,
        f"{target.name} {'restored' if target.is_active else 'archived'}.",
    )
    return redirect("families:user_list")
