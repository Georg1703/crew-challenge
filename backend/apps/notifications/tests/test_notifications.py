"""News for a member, from reactions and comments on any registered target, and how it is read,
pushed and pruned. Members stand in for the targets, as in the comments tests."""

import pytest
import time_machine

from apps.comments import services as comments
from apps.core import clock
from apps.crews import targets
from apps.crews.models import Member
from apps.notifications import selectors, services
from apps.notifications.models import Notification, PushSubscription
from apps.reactions import services as reactions
from tests.factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db

Kind = Notification.Kind
FIRE = "\U0001f525"
CLAP = "\U0001f44f"
A, T = chr(0x103), chr(0x21B)  # Romanian a-breve and t-comma: sources stay ASCII


def _crewmates(member):
    return Member.objects.filter(crew=member.crew)


@pytest.fixture
def people():
    """Ana, Bogdan and Cristina in one crew; members stand in for a target that takes comments
    ("person", owned by the member it is)."""
    targets.register(
        targets.Target(key="person", model=Member, visible=_crewmates, comments=True, owner="pk")
    )
    ana = AdminFactory.create(display_name="Ana")
    bogdan = MemberFactory.create(crew=ana.crew, display_name="Bogdan")
    cristina = MemberFactory.create(crew=ana.crew, display_name="Cristina")
    yield ana, bogdan, cristina
    targets.unregister("person")


def at(moment: str):
    return time_machine.travel(moment, tick=False)


def react(who, on, emoji=FIRE):
    reactions.react(member=who, target="person", target_id=on.pk, emoji=emoji)


def say(who, on, text="Bravo!", parent=None):
    return comments.add(
        member=who,
        target="person",
        target_id=on.pk,
        text=text,
        parent_id=parent.pk if parent is not None else None,
    )


def news(member):
    return [(n.kind, n.actor.display_name, n.facts) for n in selectors.page(member=member)]


def test_a_reaction_is_news_to_the_owner_never_to_the_actor(people):
    ana, bogdan, _ = people
    react(bogdan, ana)
    react(ana, ana)  # on her own page: nothing
    assert news(ana) == [(Kind.REACTION, "Bogdan", {"emoji": FIRE, "on": "person"})]
    assert news(bogdan) == []
    row = Notification.objects.get()
    assert (row.target, row.crew_id, row.read_at) == (ana, ana.crew_id, None)


def test_a_reaction_changed_is_fresh_news_and_one_taken_back_is_gone(people):
    ana, bogdan, _ = people
    with at("2026-11-09 08:00Z"):
        react(bogdan, ana)
        react(bogdan, ana)  # the same again: nothing new
    first = Notification.objects.get()
    with at("2026-11-09 08:05Z"):
        react(bogdan, ana, CLAP)
    changed = Notification.objects.get()
    assert (changed.facts["emoji"], changed.created_at > first.created_at) == (CLAP, True)
    reactions.unreact(member=bogdan, target="person", target_id=ana.pk)
    assert not Notification.objects.exists()


def test_a_reaction_on_a_comment_is_news_to_its_writer_on_the_comments_page(people):
    ana, bogdan, cristina = people
    comment = say(bogdan, ana)
    reactions.react(member=cristina, target="comment", target_id=comment.pk, emoji=FIRE)
    reactions.react(member=bogdan, target="comment", target_id=comment.pk, emoji=FIRE)  # his own
    row = Notification.objects.get(kind=Kind.REACTION)
    assert (row.recipient, row.actor, row.target) == (bogdan, cristina, ana)
    assert row.facts == {"emoji": FIRE, "on": "comment"}


def test_a_comment_is_news_to_the_owner_and_to_everyone_who_commented(people):
    ana, bogdan, cristina = people
    say(bogdan, ana, "x" * 100)
    say(cristina, ana, "Si eu!")
    say(ana, ana, "Multumesc")  # her own: news to the others, not to her
    assert news(ana) == [
        (Kind.COMMENT, "Cristina", {"text": "Si eu!", "on": "person"}),
        (Kind.COMMENT, "Bogdan", {"text": "x" * 80, "on": "person"}),
    ]
    assert news(bogdan) == [
        (Kind.COMMENT, "Ana", {"text": "Multumesc", "on": "person"}),
        (Kind.COMMENT, "Cristina", {"text": "Si eu!", "on": "person"}),
    ]
    assert news(cristina) == [(Kind.COMMENT, "Ana", {"text": "Multumesc", "on": "person"})]


def test_a_reply_is_one_line_to_the_writer_answered_and_a_comment_to_the_rest(people):
    ana, bogdan, cristina = people
    on_ana = say(bogdan, ana)
    say(cristina, ana, "Raspund", parent=on_ana)
    assert news(bogdan) == [(Kind.REPLY, "Cristina", {"text": "Raspund", "on": "person"})]
    assert news(ana) == [
        (Kind.COMMENT, "Cristina", {"text": "Raspund", "on": "person"}),
        (Kind.COMMENT, "Bogdan", {"text": "Bravo!", "on": "person"}),
    ]
    mine = say(ana, ana)
    say(bogdan, ana, "Pentru tine", parent=mine)  # a reply to her on her own page: one line
    assert news(ana)[0] == (Kind.REPLY, "Bogdan", {"text": "Pentru tine", "on": "person"})
    assert Notification.objects.filter(recipient=ana).count() == 3
    assert news(cristina)[0] == (Kind.COMMENT, "Bogdan", {"text": "Pentru tine", "on": "person"})


def test_a_deleted_comment_takes_its_news_with_it(people):
    ana, bogdan, _ = people
    with at("2026-11-09 08:00Z"):
        comment = say(bogdan, ana)
        comments.delete(member=bogdan, comment_id=comment.pk)
    assert not Notification.objects.exists()


def test_news_is_read_all_at_once_or_card_by_card(people):
    ana, bogdan, cristina = people
    with at("2026-11-09 08:00Z"):
        react(bogdan, ana)
        say(cristina, ana)
        react(ana, bogdan)
        say(ana, bogdan)
    assert selectors.unread_count(member=ana) == 2
    with at("2026-11-09 08:10Z"):
        comments.mark_read(member=bogdan, target="person", target_id=bogdan.pk)  # opened his card
    assert selectors.unread_count(member=bogdan) == 0
    assert selectors.unread_count(member=ana) == 2  # hers untouched
    with at("2026-11-09 08:20Z"):
        services.mark_read(member=ana)  # opened the list
        assert selectors.unread_count(member=ana) == 0
        assert {n.read_at for n in selectors.page(member=ana)} == {clock.now()}


def test_the_list_pages_latest_first(people):
    ana, bogdan, _ = people
    for minute in range(3):
        with at(f"2026-11-09 08:0{minute}Z"):
            say(bogdan, ana, f"n{minute}")
    first = selectors.page(member=ana, limit=2)
    assert [n.facts["text"] for n in first] == ["n2", "n1"]
    rest = selectors.page(member=ana, before=first[-1].created_at, limit=2)
    assert [n.facts["text"] for n in rest] == ["n0"]


def test_old_news_is_pruned(people):
    ana, bogdan, _ = people
    with at("2026-08-01 08:00Z"):
        say(bogdan, ana, "old")
    with at("2026-11-09 08:00Z"):
        say(bogdan, ana, "new")
        assert services.prune() == 1
        assert services.prune() == 0
    assert [n.facts["text"] for n in selectors.page(member=ana)] == ["new"]


def test_a_push_reaches_every_device_in_the_recipients_language(people, push_sender):
    ana, bogdan, _ = people
    ana.user.preferred_language = "en"
    ana.user.save()
    for name in ("phone", "laptop"):
        services.subscribe(user=ana.user, endpoint=f"https://push/{name}", p256dh="p", auth="a")
    services.subscribe(user=bogdan.user, endpoint="https://push/his", p256dh="p", auth="a")
    react(bogdan, ana)
    row = Notification.objects.get()
    assert services.send_push(notification_id=row.pk) == 2
    endpoints = sorted(endpoint for endpoint, _ in push_sender.sent)
    assert endpoints == ["https://push/laptop", "https://push/phone"]
    assert push_sender.sent[0][1] == {
        "title": ana.crew.name,
        "body": f"Bogdan reacted with {FIRE} to your post",
        "url": f"/person/{ana.pk}?crew={ana.crew_id}",
        "tag": f"person:{ana.pk}",
    }


def test_push_lines_say_what_happened(people, push_sender):
    ana, bogdan, cristina = people
    services.subscribe(user=ana.user, endpoint="https://push/ana", p256dh="p", auth="a")
    services.subscribe(user=bogdan.user, endpoint="https://push/bogdan", p256dh="p", auth="a")
    comment = say(bogdan, ana, "Bravo!")
    reactions.react(member=ana, target="comment", target_id=comment.pk, emoji=FIRE)
    say(ana, ana, "Mersi", parent=comment)
    for row in Notification.objects.order_by("created_at"):
        services.send_push(notification_id=row.pk)
    assert [payload["body"] for _, payload in push_sender.sent] == [
        "Bogdan a comentat: Bravo!",
        f"Ana a reac{T}ionat cu {FIRE} la comentariul t{A}u",
        f"Ana {T}i-a r{A}spuns: Mersi",
    ]


def test_a_device_the_push_service_lost_is_dropped(people, push_sender):
    ana, bogdan, _ = people
    services.subscribe(user=ana.user, endpoint="https://push/gone", p256dh="p", auth="a")
    push_sender.gone.add("https://push/gone")
    react(bogdan, ana)
    assert services.send_push(notification_id=Notification.objects.get().pk) == 0
    assert not PushSubscription.objects.exists()
    assert services.send_push(notification_id=ana.pk) == 0  # no such notification: nothing


def test_push_goes_out_when_the_post_commits(
    people, push_sender, django_capture_on_commit_callbacks
):
    ana, bogdan, _ = people
    services.subscribe(user=ana.user, endpoint="https://push/ana", p256dh="p", auth="a")
    with django_capture_on_commit_callbacks(execute=True):
        react(bogdan, ana)
    assert [endpoint for endpoint, _ in push_sender.sent] == ["https://push/ana"]


def test_push_off_sends_nothing(people, settings):
    from integrations.push import get_push_sender

    ana, bogdan, _ = people
    settings.PUSH_BACKEND = "off"
    get_push_sender.cache_clear()
    services.subscribe(user=ana.user, endpoint="https://push/ana", p256dh="p", auth="a")
    react(bogdan, ana)
    assert services.send_push(notification_id=Notification.objects.get().pk) == 0


def test_a_browser_subscribes_once_and_follows_its_user(people):
    ana, bogdan, _ = people
    services.subscribe(user=ana.user, endpoint="https://push/x", p256dh="p1", auth="a1")
    services.subscribe(
        user=bogdan.user, endpoint="https://push/x", p256dh="p2", auth="a2", user_agent="x" * 300
    )
    row = PushSubscription.objects.get()
    assert (row.user, row.p256dh, len(row.user_agent)) == (bogdan.user, "p2", 200)
    services.unsubscribe(user=ana.user, endpoint="https://push/x")  # not hers any more
    assert PushSubscription.objects.exists()
    services.unsubscribe(user=bogdan.user, endpoint="https://push/x")
    assert not PushSubscription.objects.exists()


def test_the_registry_knows_owners_and_pages(people):
    ana, bogdan, _ = people
    comment = say(bogdan, ana)
    assert targets.owner_id_of(ana) == ana.pk
    assert targets.owner_id_of(comment) == bogdan.pk
    assert targets.page_of(comment) == ("person", ana.pk)
    assert targets.page_of(ana) == ("person", ana.pk)
    assert targets.key_for(comment.target_type) == "person"
    with pytest.raises(targets.ImproperlyConfigured):
        targets.of(ana.user)
    with pytest.raises(targets.ImproperlyConfigured):
        targets.key_for(comments.ContentType.objects.get_for_model(ana.user))


def test_a_target_without_an_owner_makes_no_news(people):
    ana, bogdan, _ = people
    targets.register(targets.Target(key="quiet", model=Member, visible=_crewmates))
    try:
        targets.unregister("person")
        reactions.react(member=bogdan, target="quiet", target_id=ana.pk, emoji=FIRE)
        assert not Notification.objects.exists()
    finally:
        targets.unregister("quiet")
