from django.urls import path

from . import views

urlpatterns = [
    path("notifications", views.NewsView.as_view(), name="notifications"),
    path("notifications/read", views.ReadView.as_view(), name="notifications-read"),
    path("push/key", views.PushKeyView.as_view(), name="push-key"),
    path("push/subscriptions", views.PushSubscriptionView.as_view(), name="push-subscriptions"),
]
