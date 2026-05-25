from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def parent_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_parent:
            return redirect("/")
        return view(request, *args, **kwargs)
    return wrapper


def kid_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_kid:
            return redirect("/")
        return view(request, *args, **kwargs)
    return wrapper
