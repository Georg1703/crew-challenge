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
        "challenges/<uuid:challenge_id>/days/<str:day>",
        views.DaySheetView.as_view(),
        name="challenge-day-sheet",
    ),
    path("feed", views.FeedView.as_view(), name="feed"),
    path(
        "challenges/<uuid:challenge_id>/check-ins/<str:day>/proofs",
        views.ProofsView.as_view(),
        name="check-in-proofs",
    ),
    path("proofs/resume", views.ResumeProofView.as_view(), name="proof-resume"),
    path("proofs/<uuid:proof_id>", views.ProofView.as_view(), name="proof"),
    path("proofs/<uuid:proof_id>/parts", views.PartsView.as_view(), name="proof-parts"),
    path("proofs/<uuid:proof_id>/parts/<int:number>", views.PartView.as_view(), name="proof-part"),
    path(
        "proofs/<uuid:proof_id>/complete", views.CompleteProofView.as_view(), name="proof-complete"
    ),
]
