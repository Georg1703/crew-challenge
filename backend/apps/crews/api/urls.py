from django.urls import path

from . import views

urlpatterns = [
    path("me", views.MeView.as_view(), name="me"),
    path("crew", views.CrewView.as_view(), name="crew"),
    path("crew/rotation", views.RotationView.as_view(), name="crew-rotation"),
    path("crew/invites", views.InviteCreateView.as_view(), name="crew-invites"),
    path("invites/<str:code>", views.InvitePreviewView.as_view(), name="invite"),
    path("invites/<str:code>/accept", views.AcceptInviteView.as_view(), name="invite-accept"),
]
