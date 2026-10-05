from django.urls import path

from . import views

urlpatterns = [
    path("proposals", views.PoolView.as_view(), name="proposals"),
    path("challenges", views.ChallengesView.as_view(), name="challenges"),
    path("challenges/<uuid:challenge_id>", views.ChallengeView.as_view(), name="challenge"),
    path("challenges/<uuid:challenge_id>/vote", views.VoteView.as_view(), name="challenge-vote"),
    path(
        "challenges/<uuid:challenge_id>/schedule",
        views.ScheduleView.as_view(),
        name="challenge-schedule",
    ),
    path(
        "challenges/<uuid:challenge_id>/participation",
        views.ParticipationView.as_view(),
        name="challenge-participation",
    ),
]
