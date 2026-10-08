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
    path(
        "challenges/<uuid:challenge_id>/windows",
        views.WindowsView.as_view(),
        name="challenge-windows",
    ),
    path(
        "challenges/<uuid:challenge_id>/days/<str:day>",
        views.DaySheetView.as_view(),
        name="challenge-day-sheet",
    ),
    path("feed", views.FeedView.as_view(), name="feed"),
    path(
        "members/<uuid:member_id>/progress",
        views.MemberProgressView.as_view(),
        name="member-progress",
    ),
    path(
        "challenges/<uuid:challenge_id>/check-ins/<str:day>/proofs",
        views.ProofsView.as_view(),
        name="check-in-proofs",
    ),
    path(
        "challenges/<uuid:challenge_id>/check-ins/proofs/resume",
        views.ResumeProofView.as_view(),
        name="check-in-proofs-resume",
    ),
]
