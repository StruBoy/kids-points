from django.urls import path

from . import views

app_name = "purchases"

urlpatterns = [
    path("request/<int:item_id>/", views.request_item, name="request_item"),
    path("queue/", views.queue, name="queue"),
    path("<int:pk>/approve/", views.approve, name="approve"),
    path("<int:pk>/deny/", views.deny, name="deny"),
    path("<int:pk>/fulfill/", views.fulfill, name="fulfill"),
]
