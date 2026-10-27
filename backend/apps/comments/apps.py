from django.apps import AppConfig


class CommentsConfig(AppConfig):
    name = "apps.comments"
    label = "comments"
    verbose_name = "Comments"

    def ready(self) -> None:
        from apps.crews import targets

        from . import selectors
        from .models import Comment

        # Members react to comments; they answer one with a reply, not a comment on it. A
        # comment is shown on its target's page.
        targets.register(
            targets.Target(
                key="comment",
                model=Comment,
                visible=selectors.visible,
                owner="member",
                page=lambda comment: targets.page_of(comment.target),
            )
        )
