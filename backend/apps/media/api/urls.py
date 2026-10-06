from django.urls import path

from . import views

urlpatterns = [
    path("media/session", views.MediaSessionView.as_view(), name="media-session"),
]
