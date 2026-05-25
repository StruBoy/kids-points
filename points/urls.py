from django.urls import path

from . import views

app_name = "points"

urlpatterns = [
    path("parent/", views.parent_home, name="parent_home"),
    path("kid/", views.kid_home, name="kid_home"),
    path("award/", views.award, name="award"),
]
