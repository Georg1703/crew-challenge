"""Comments on any target that takes them: the rules, the reads and the API. Members stand in for
the targets, so no domain app is needed (comments on journal cards: apps/journal/tests)."""

import pytest
import time_machine
from django.contrib.contenttypes.fields import GenericRelation

from apps.comments import selectors, services
from apps.comments.models import MAX_LENGTH, Comment
from apps.core.errors import ValidationFailed
from apps.crews import targets
from apps.crews.models import Member
from apps.crews.targets import TargetNotFound
from apps.proofs import services as proofs
from apps.proofs.models import Proof
from tests.factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db

FIRE = "\U0001f525"


def _crewmates(member):
    return Member.objects.filter(crew=member.crew)


@pytest.fixture
def people():
    """Ana and Bogdan in one crew. Members stand in for a target that takes comments ("person",
    made by the member it is) and for one that takes reactions only ("quiet")."""
    targets.register(
        targets.Target(key="person", model=Member, visible=_crewmates, comments=True, owner="pk")
    )
    targets.register(targets.Target(key="quiet", model=Member, visible=_crewmates))
    ana = AdminFactory.create(display_name="Ana")
    yield ana, MemberFactory.create(crew=ana.crew, display_name="Bogdan")
    targets.unregister("person")
    targets.unregister("quiet")


def at(moment: str):
    return time_machine.travel(moment, tick=False)


def say(member, on, text="Bravo!", parent=None):
    return services.add(
        member=member,
        target="person",
        target_id=on.pk,
        text=text,
        parent_id=parent.pk if parent is not None else None,
    )


def test_any_comment_can_be_answered_however_long_the_chain(people):
    ana, bogdan = people
    comment = say(ana, bogdan)
    for turn in range(8):
        reply = say(bogdan if turn % 2 else ana, bogdan, parent=comment)
        assert reply.parent_id == comment.pk
        comment = reply


def test_the_text_is_trimmed_and_kept_short(people):
    ana, bogdan = people
    assert say(ana, bogdan, text="  la multi ani \n").text == "la multi ani"
    assert len(say(ana, bogdan, text="x" * MAX_LENGTH).text) == MAX_LENGTH
    for text in (" \n ", "x" * (MAX_LENGTH + 1)):
        with pytest.raises(ValidationFailed):
            say(ana, bogdan, text=text)


def test_only_targets_i_see_that_take_comments(people):
    ana, bogdan = people
    stranger = AdminFactory.create()
    for key, target_id in (("person", stranger.pk), ("quiet", bogdan.pk), ("nothing", bogdan.pk)):
        with pytest.raises(TargetNotFound):
            services.add(member=ana, target=key, target_id=target_id, text="Bravo!")
    with pytest.raises(TargetNotFound):
        selectors.thread(member=stranger, target="person", target_id=bogdan.pk)


def test_a_reply_answers_a_comment_on_the_same_target(people):
    ana, bogdan = people
    on_bogdan = say(ana, bogdan)
    with pytest.raises(services.CommentNotFound):
        say(bogdan, ana, parent=on_bogdan)


def test_you_delete_your_own_comment_in_its_first_minute(people):
    ana, bogdan = people
    stranger = AdminFactory.create()
    with at("2026-11-09 08:00:00Z"):
        mine = say(ana, bogdan)
        theirs = say(bogdan, bogdan)
    with at("2026-11-09 08:00:59Z"):
        with pytest.raises(services.NotYourComment):
            services.delete(member=ana, comment_id=theirs.pk)
        with pytest.raises(services.CommentNotFound):
            services.delete(member=stranger, comment_id=mine.pk)
        services.delete(member=ana, comment_id=mine.pk)
    assert not Comment.objects.filter(pk=mine.pk).exists()
    assert Comment.all_objects.filter(pk=mine.pk).exists()  # soft: the admin can restore it
    with pytest.raises(services.CommentNotFound):
        services.delete(member=ana, comment_id=mine.pk)
    with at("2026-11-09 08:01:01Z"), pytest.raises(services.CommentTooOld):
        services.delete(member=bogdan, comment_id=theirs.pk)


def test_a_comment_with_replies_stays(people):
    ana, bogdan = people
    with at("2026-11-09 08:00Z"):
        first = say(ana, bogdan)
        reply = say(bogdan, bogdan, parent=first)
        with pytest.raises(services.CommentHasReplies):
            services.delete(member=ana, comment_id=first.pk)
        services.delete(member=bogdan, comment_id=reply.pk)  # a deleted reply does not count
        services.delete(member=ana, comment_id=first.pk)
        with pytest.raises(services.CommentNotFound):  # nothing left to answer
            say(bogdan, bogdan, parent=first)


def test_the_thread_and_the_summary_of_its_target(people):
    ana, bogdan = people
    cristina, dan = (MemberFactory.create(crew=ana.crew) for _ in range(2))
    said: list[Comment] = []
    for minute, who in enumerate((ana, bogdan, cristina, dan, bogdan)):
        with at(f"2026-11-09 08:0{minute}Z"):
            said.append(say(who, bogdan, parent=said[0] if who is bogdan else None))
    with at("2026-11-09 08:06Z"):
        gone = say(ana, bogdan)
        services.delete(member=ana, comment_id=gone.pk)  # in neither the thread nor the count

    assert selectors.thread(member=dan, target="person", target_id=bogdan.pk) == said
    assert selectors.summaries(member=ana, target="person", ids=[bogdan.pk, ana.pk]) == {
        bogdan.pk: selectors.Summary(
            count=5, member_ids=[bogdan.pk, dan.pk, cristina.pk], unread=4
        ),
        ana.pk: selectors.Summary(),
    }
    assert selectors.summaries(member=ana, target="nothing", ids=[ana.pk]) == {
        ana.pk: selectors.Summary()
    }
    assert selectors.summaries(member=ana, target="person", ids=[]) == {}


def test_unread_is_the_others_comments_since_i_last_looked(people):
    ana, bogdan = people
    unread = lambda who, on: selectors.summaries(  # noqa: E731
        member=who, target="person", ids=[on.pk]
    )[on.pk].unread
    with at("2026-11-09 08:00Z"):
        say(bogdan, ana)  # on Ana's own page: news to her
        say(ana, ana)  # her own words are never unread for her
    assert (unread(ana, ana), selectors.unread_count(member=ana)) == (1, 1)
    assert (unread(bogdan, ana), selectors.unread_count(member=bogdan)) == (1, 1)  # he wrote there

    with at("2026-11-09 08:05Z"):
        services.mark_read(member=ana, target="person", target_id=ana.pk)
    assert (unread(ana, ana), selectors.unread_count(member=ana)) == (0, 0)
    with at("2026-11-09 08:10Z"):
        later = say(bogdan, ana)
        services.mark_read(member=ana, target="person", target_id=ana.pk)  # again: one row
        services.delete(member=bogdan, comment_id=later.pk)
    assert selectors.unread_count(member=ana) == 0
    with at("2026-11-09 08:20Z"):
        say(bogdan, ana)
    assert (unread(ana, ana), selectors.unread_count(member=ana)) == (1, 1)

    with at("2026-11-09 09:00Z"):  # joins after all that: none of it is news to her
        cristina = MemberFactory.create(crew=ana.crew)
    assert unread(cristina, ana) == 0
    with pytest.raises(TargetNotFound):
        services.mark_read(member=AdminFactory.create(), target="person", target_id=ana.pk)


def test_whether_someone_else_commented(people):
    ana, bogdan = people
    on = Member.objects.filter(pk=bogdan.pk)
    say(bogdan, bogdan)
    assert not selectors.others_commented(member=bogdan, on=on)
    say(ana, bogdan)
    assert selectors.others_commented(member=bogdan, on=on)


def test_every_target_that_takes_comments_deletes_them():
    """A generic key has no FK: each such target model needs a GenericRelation to Comment."""
    for target in targets.all_targets():
        if target.comments:
            assert any(
                isinstance(f, GenericRelation) and f.related_model is Comment
                for f in target.model._meta.get_fields()
            ), f"{target.model.__name__} needs a GenericRelation to Comment"


def picked(member, on, storage, *, gif=True, finish=True):
    """A photo (a GIF by default) picked for my next comment on `on`, uploaded unless `finish`
    is false."""
    plan = services.start_image(
        member=member,
        target="person",
        target_id=on.pk,
        kind="photo",
        content_type="image/gif" if gif else "image/jpeg",
        size=4,
    )
    if finish:
        storage.put_object(key=plan.proof.original.key, data=b"gif8", content_type="")
        proofs.complete_proof(by=member, proof_id=plan.proof.pk)
    return plan.proof


def test_a_comment_carries_my_photos_and_gifs(people, object_storage):
    ana, bogdan = people
    gif = picked(ana, bogdan, object_storage)
    picked(bogdan, bogdan, object_storage)  # his own draft: not part of her comment
    late = picked(ana, bogdan, object_storage, gif=False, finish=False)
    with pytest.raises(proofs.UploadsRunning):
        say(ana, bogdan, text="")
    proofs.delete_proof(by=ana, proof_id=late.pk)

    comment = say(ana, bogdan, text="  ")  # a GIF alone is a whole comment
    assert comment.text == ""
    assert list(Proof.objects.filter(post_id=comment.pk)) == [gif]
    assert selectors.my_drafts(member=ana, target="person", target_id=bogdan.pk) == []
    assert len(selectors.my_drafts(member=bogdan, target="person", target_id=bogdan.pk)) == 1
    with pytest.raises(ValidationFailed):  # nothing to send
        say(ana, bogdan, text=" ")


def test_a_comment_takes_five_photos_and_no_videos(people, object_storage):
    ana, bogdan = people
    for _ in range(5):
        picked(ana, bogdan, object_storage, finish=False)
    with pytest.raises(proofs.TooManyProofs):
        picked(ana, bogdan, object_storage, finish=False)
    picked(bogdan, bogdan, object_storage, finish=False)  # each member's own five
    with pytest.raises(ValidationFailed):
        services.start_image(
            member=ana,
            target="person",
            target_id=bogdan.pk,
            kind="video",
            content_type="video/mp4",
            size=4,
        )
    with pytest.raises(TargetNotFound):
        picked(AdminFactory.create(), bogdan, object_storage, finish=False)


def test_the_api(browser, people):
    ana, bogdan = people
    url = f"/api/v1/comments/person/{bogdan.pk}"
    browser.force_login(ana.user)
    made = browser.post(url, {"text": "Bravo!"}, format="json")
    assert made.status_code == 201
    first = made.json()
    assert (first["member_id"], first["parent_id"], first["reactions"], first["proofs"]) == (
        str(ana.pk),
        None,
        {"groups": [], "mine": None},
        [],
    )
    browser.force_login(bogdan.user)
    reply = browser.post(url, {"text": "Mersi", "parent_id": first["id"]}, format="json").json()
    reacted = browser.put(
        f"/api/v1/reactions/comment/{first['id']}", {"emoji": FIRE}, format="json"
    )
    assert reacted.status_code == 200
    thread = browser.get(url).json()["results"]
    assert [(c["text"], c["parent_id"]) for c in thread] == [
        ("Bravo!", None),
        ("Mersi", first["id"]),
    ]
    assert thread[0]["reactions"]["mine"] == FIRE
    blank = browser.post(url, {"text": " "}, format="json")
    assert blank.json()["error"]["code"] == "validation_failed"
    mine = browser.delete(f"/api/v1/comments/{first['id']}")
    assert mine.json()["error"]["code"] == "not_your_comment"
    assert browser.delete(f"/api/v1/comments/{reply['id']}").status_code == 204

    browser.force_login(AdminFactory.create().user)
    assert browser.get(url).json()["error"]["code"] == "target_not_found"
    hidden = browser.put(f"/api/v1/reactions/comment/{first['id']}", {"emoji": FIRE}, format="json")
    assert hidden.json()["error"]["code"] == "target_not_found"


def test_photos_over_the_api(browser, people, object_storage):
    ana, bogdan = people
    url = f"/api/v1/comments/person/{bogdan.pk}"
    browser.force_login(ana.user)
    started = browser.post(
        f"{url}/images", {"kind": "photo", "content_type": "image/gif", "size": 4}, format="json"
    )
    assert started.status_code == 201
    proof = started.json()["proof"]
    object_storage.put_object(
        key=Proof.objects.get(pk=proof["id"]).original.key, data=b"gif8", content_type=""
    )
    assert browser.post(f"/api/v1/proofs/{proof['id']}/complete").status_code == 200
    assert [p["id"] for p in browser.get(url).json()["drafts"]] == [proof["id"]]

    made = browser.post(url, {"text": ""}, format="json").json()
    assert [p["id"] for p in made["proofs"]] == [proof["id"]]
    thread = browser.get(url).json()
    assert ([p["id"] for p in thread["results"][0]["proofs"]], thread["drafts"]) == (
        [proof["id"]],
        [],
    )
    browser.force_login(bogdan.user)  # her drafts are hers alone; her posted photo shows
    assert browser.get(url).json()["drafts"] == []
