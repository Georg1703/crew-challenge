from django.urls import path

from . import views

urlpatterns = [
    path("spins", views.OwedView.as_view(), name="spins"),
    path("spins/<uuid:spin_id>/draw", views.DrawView.as_view(), name="spin-draw"),
    path("spins/<uuid:spin_id>/done", views.DoneView.as_view(), name="spin-done"),
    path("spins/<uuid:spin_id>/proofs", views.SpinProofsView.as_view(), name="spin-proofs"),
    path(
        "spins/<uuid:spin_id>/proofs/resume",
        views.SpinProofResumeView.as_view(),
        name="spin-proofs-resume",
    ),
]
