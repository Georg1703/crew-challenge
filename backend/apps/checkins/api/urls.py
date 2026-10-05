from django.urls import path

from . import views

urlpatterns = [
    path("today", views.TodayView.as_view(), name="today"),
    path(
        "challenges/<uuid:challenge_id>/check-ins",
        views.CheckInsView.as_view(),
        name="challenge-check-ins",
    ),
    path(
        "challenges/<uuid:challenge_id>/check-ins/<str:day>/last",
        views.UndoView.as_view(),
        name="challenge-check-in-undo",
    ),
    path("challenges/<uuid:challenge_id>/board", views.BoardView.as_view(), name="challenge-board"),
]
