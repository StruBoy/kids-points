from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def home(request):
    if request.user.is_parent:
        return redirect("points:parent_home")
    return redirect("points:kid_home")
