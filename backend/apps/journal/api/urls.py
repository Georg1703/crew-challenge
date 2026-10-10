from django.urls import path

from . import views

urlpatterns = [
    path("journal", views.JournalView.as_view(), name="journal"),
    path("journal/<uuid:entry_id>", views.CardView.as_view(), name="card"),
]
