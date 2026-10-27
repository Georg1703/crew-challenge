from django.urls import path

from . import views

urlpatterns = [
    path("comments/<str:target>/<uuid:target_id>", views.ThreadView.as_view(), name="thread"),
    path("comments/<str:target>/<uuid:target_id>/read", views.ReadView.as_view(), name="read"),
    path(
        "comments/<str:target>/<uuid:target_id>/images", views.ImagesView.as_view(), name="images"
    ),
    path("comments/<uuid:comment_id>", views.CommentView.as_view(), name="comment"),
]
