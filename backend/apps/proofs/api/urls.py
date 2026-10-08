from django.urls import path

from . import views

urlpatterns = [
    path("proofs/<uuid:proof_id>", views.ProofView.as_view(), name="proof"),
    path("proofs/<uuid:proof_id>/parts", views.PartsView.as_view(), name="proof-parts"),
    path("proofs/<uuid:proof_id>/parts/<int:number>", views.PartView.as_view(), name="proof-part"),
    path(
        "proofs/<uuid:proof_id>/complete", views.CompleteProofView.as_view(), name="proof-complete"
    ),
]
