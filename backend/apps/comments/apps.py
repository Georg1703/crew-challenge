from django.apps import AppConfig


class CommentsConfig(AppConfig):
    name = "apps.comments"
    label = "comments"
    verbose_name = "Comments"

    def ready(self) -> None:
        from apps.crews.targets import Target, register

        from . import selectors
        from .models import Comment

        # Members react to comments; they answer one with a reply, not a comment on it.
        register(Target(key="comment", model=Comment, visible=selectors.visible))
