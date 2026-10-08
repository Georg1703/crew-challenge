from django.urls import path

from . import views

urlpatterns = [path("journal", views.JournalView.as_view(), name="journal")]
