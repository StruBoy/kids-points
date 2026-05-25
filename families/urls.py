from django.urls import path

from . import views

app_name = "families"

urlpatterns = [
    path("login/", views.login_picker, name="login_picker"),
    path("login/parent/", views.parent_login, name="parent_login"),
    path("login/kid/<int:user_id>/", views.kid_login, name="kid_login"),
    path("logout/", views.logout_view, name="logout"),
    path("users/", views.user_list, name="user_list"),
    path("users/new/", views.user_create, name="user_create"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/archive/", views.user_archive, name="user_archive"),
]
