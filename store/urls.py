from django.urls import path

from . import views

app_name = "store"

urlpatterns = [
    path("", views.browse, name="browse"),
    path("admin/", views.admin_list, name="admin_list"),
    path("admin/new/", views.admin_create, name="admin_create"),
    path("admin/<int:pk>/edit/", views.admin_edit, name="admin_edit"),
    path("admin/<int:pk>/archive/", views.admin_archive, name="admin_archive"),
]
