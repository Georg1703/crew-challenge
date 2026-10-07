import pytest

from apps.reactions import selectors, services, targets
from apps.reactions.models import Reaction
from apps.reactions.services import InvalidEmoji, TargetNotFound
from tests.factories import MemberFactory

pytestmark = pytest.mark.django_db

FIRE = "\U0001f525"
CLAP = "\U0001f44f"
HEART = chr(0x2764) + chr(0xFE0F)  # chr(): ruff would turn the escapes into raw characters


def test_react_replace_and_take_back(member_target):
    ana = MemberFactory.create()
    bogdan = MemberFactory.create(crew=ana.crew)

    services.react(member=ana, target=member_target, target_id=bogdan.pk, emoji=FIRE)
    services.react(member=ana, target=member_target, target_id=bogdan.pk, emoji=FIRE)  # no-op
    first = Reaction.objects.get()
    services.react(member=ana, target=member_target, target_id=bogdan.pk, emoji=CLAP)

    replaced = Reaction.objects.get()
    assert (replaced.emoji, replaced.crew_id, replaced.target) == (CLAP, ana.crew_id, bogdan)
    assert replaced.created_at > first.created_at  # a new emoji counts as used now

    services.unreact(member=ana, target=member_target, target_id=bogdan.pk)
    services.unreact(member=ana, target=member_target, target_id=bogdan.pk)  # nothing left: fine
    assert not Reaction.objects.exists()


def test_targets_must_exist_be_registered_and_belong_to_the_crew(member_target):
    ana = MemberFactory.create()
    stranger = MemberFactory.create()  # another crew; the test `find` returns it anyway

    for target, target_id in (
        ("nothing", ana.pk),
        (member_target, stranger.user_id),  # no such member
        (member_target, stranger.pk),
    ):
        with pytest.raises(TargetNotFound):
            services.react(member=ana, target=target, target_id=target_id, emoji=FIRE)
        with pytest.raises(TargetNotFound):
            services.unreact(member=ana, target=target, target_id=target_id)


@pytest.mark.parametrize(
    "emoji",
    [
        FIRE,
        HEART,
        "\U0001f44d\U0001f3fd",  # thumbs up, medium skin tone
        chr(0x200D).join(["\U0001f468", "\U0001f469", "\U0001f467"]),  # family, joined by ZWJ
        "\U0001f1f2\U0001f1e9",  # flag of Moldova
        "1" + chr(0xFE0F) + chr(0x20E3),  # keycap 1
        "#" + chr(0xFE0F) + chr(0x20E3),  # keycap #
    ],
)
def test_one_emoji_of_any_shape_is_accepted(emoji):
    assert services.check_emoji(emoji) == emoji


@pytest.mark.parametrize(
    "text", ["", "a", "fire", " " + FIRE, FIRE + " ", "<b>", "1", "#", FIRE * 33, chr(0x200D)]
)
def test_anything_but_one_emoji_is_refused(text):
    with pytest.raises(InvalidEmoji) as error:
        services.check_emoji(text)
    assert error.value.fields == {"emoji": ["Pick one emoji."]}


def test_summaries_group_by_first_use_and_know_mine(member_target):
    ana = MemberFactory.create()
    bogdan = MemberFactory.create(crew=ana.crew)
    cristina = MemberFactory.create(crew=ana.crew)
    quiet = MemberFactory.create(crew=ana.crew)

    def react(by, emoji, on=bogdan):
        services.react(member=by, target=member_target, target_id=on.pk, emoji=emoji)

    react(cristina, CLAP)
    react(ana, FIRE)
    react(bogdan, CLAP)
    react(ana, FIRE, on=cristina)

    found = selectors.summaries(
        member=ana, target=member_target, ids=[bogdan.pk, cristina.pk, quiet.pk]
    )
    assert found[bogdan.pk] == selectors.Summary(
        groups=[
            selectors.Group(CLAP, [cristina.pk, bogdan.pk]),
            selectors.Group(FIRE, [ana.pk]),
        ],
        mine=FIRE,
    )
    assert found[cristina.pk].mine == FIRE
    assert found[quiet.pk] == selectors.Summary()
    assert selectors.summary(member=bogdan, target=member_target, target_id=bogdan.pk).mine == CLAP
    assert selectors.summaries(member=ana, target="nothing", ids=[bogdan.pk]) == {
        bogdan.pk: selectors.Summary()
    }
    assert selectors.summaries(member=ana, target=member_target, ids=[]) == {}


def test_another_crew_never_sees_reactions(member_target):
    ana = MemberFactory.create()
    services.react(member=ana, target=member_target, target_id=ana.pk, emoji=FIRE)
    outsider = MemberFactory.create()
    assert selectors.summary(member=outsider, target=member_target, target_id=ana.pk).groups == []


def test_registering_twice_is_fine_but_a_clash_is_not(member_target):
    from django.core.exceptions import ImproperlyConfigured

    from apps.crews.models import Crew

    same = targets.get(member_target)
    assert same is not None
    targets.register(same)
    with pytest.raises(ImproperlyConfigured):
        targets.register(targets.Target(key=member_target, model=Crew, find=same.find))  # type: ignore[arg-type]


def test_every_registered_target_deletes_its_reactions():
    """A generic key has no FK: each target model needs a GenericRelation to Reaction."""
    from django.contrib.contenttypes.fields import GenericRelation

    for target in targets.all_targets():
        relations = [
            f
            for f in target.model._meta.get_fields()
            if isinstance(f, GenericRelation) and f.related_model is Reaction
        ]
        assert relations, f"{target.model.__name__} needs a GenericRelation to Reaction"
