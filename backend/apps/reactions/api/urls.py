from django.urls import path

from . import views

urlpatterns = [
    path(
        "reactions/<str:target>/<uuid:target_id>",
        views.ReactionView.as_view(),
        name="reaction",
    ),
]
