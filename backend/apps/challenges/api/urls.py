from django.urls import path

from . import views

urlpatterns = [
    path("rounds/current", views.CurrentRoundView.as_view(), name="round-current"),
    path("rounds/<uuid:round_id>", views.RoundView.as_view(), name="round"),
    path("rounds/<uuid:round_id>/vote", views.RoundVoteView.as_view(), name="round-vote"),
    path("rounds/<uuid:round_id>/choice", views.RoundChoiceView.as_view(), name="round-choice"),
    path("challenges", views.ChallengesView.as_view(), name="challenges"),
    path("challenges/<uuid:challenge_id>", views.ChallengeView.as_view(), name="challenge"),
    path(
        "challenges/<uuid:challenge_id>/repropose",
        views.ReproposeView.as_view(),
        name="challenge-repropose",
    ),
    path(
        "challenges/<uuid:challenge_id>/participation",
        views.ParticipationView.as_view(),
        name="challenge-participation",
    ),
]
