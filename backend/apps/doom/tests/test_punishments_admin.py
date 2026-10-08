"""Punishments edited in the Django admin: the app's rules, numbers that close up, and a drawn one
stays (here, not in challenges: a spin is what keeps it)."""

from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.challenges.admin import ChallengeAdmin, PunishmentInline
from apps.challenges.models import Challenge, Punishment
from apps.doom import services
from apps.doom.models import Spin
from apps.doom.tests.test_services import SWIM, Pick, at, check_in, scheduled

pytestmark = pytest.mark.django_db

FOUR = [
    {"text": "20 burpees", "proof_required": True},
    {"text": "No phone after 21:00"},
    {"text": "Cold shower"},
    {"text": "Plank, 2 minutes"},
]


def texts(challenge: Challenge) -> list[tuple[int, str]]:
    return list(
        Punishment.objects.filter(challenge=challenge)
        .order_by("position")
        .values_list("position", "text")
    )


def edit(challenge: Challenge, rows: list[dict[str, Any]], add: tuple[str, ...] = ()):
    """Post the punishments inline: `rows` change the current ones in order, `add` new texts.
    Returns the bound formset and a function that saves it the way the admin does."""
    request = RequestFactory().post("/")
    users = get_user_model().objects
    request.user = users.filter(username="root").first() or users.create_superuser("root", "", "x")
    formset_class = PunishmentInline(Challenge, admin.site).get_formset(request, challenge)
    current = list(Punishment.objects.filter(challenge=challenge).order_by("position"))
    prefix = formset_class.get_default_prefix()
    data: dict[str, Any] = {
        f"{prefix}-TOTAL_FORMS": str(len(current) + len(add)),
        f"{prefix}-INITIAL_FORMS": str(len(current)),
    }
    for n, (row, change) in enumerate(zip(current, rows, strict=True)):
        fields = {"id": row.pk, "text": row.text, "proof_required": row.proof_required} | change
        data |= {f"{prefix}-{n}-{k}": ("on" if v is True else v) for k, v in fields.items() if v}
    for n, text in enumerate(add, start=len(current)):
        data[f"{prefix}-{n}-text"] = text
    formset = formset_class(data, instance=challenge, prefix=prefix)

    def save() -> None:
        ChallengeAdmin(Challenge, admin.site).save_formset(
            request, SimpleNamespace(instance=challenge), formset, change=True
        )

    return formset, save


@pytest.fixture
def swim(crew):
    ana, bogdan = crew
    return scheduled(ana, bogdan, date(2026, 11, 2), {**SWIM, "punishments": FOUR})


def test_remove_reword_and_add_keep_the_numbers_1_to_n(swim):
    formset, save = edit(
        swim, [{}, {"DELETE": True}, {"text": "Cold shower, 2 minutes"}, {}], add=("Sing",)
    )
    assert formset.is_valid(), formset.non_form_errors()
    save()
    assert texts(swim) == [
        (1, "20 burpees"),
        (2, "Cold shower, 2 minutes"),
        (3, "Plank, 2 minutes"),
        (4, "Sing"),
    ]
    assert Punishment.objects.get(challenge=swim, position=4).crew_id == swim.crew_id


@pytest.mark.parametrize(
    ("rows", "add", "error"),
    [
        ([{"DELETE": True}] * 3 + [{}], (), "Add 2 to 8 punishments, or none."),
        ([{}, {}, {}, {}], ("cold SHOWER",), "Each punishment must be different."),
    ],
)
def test_the_apps_rules_hold(swim, rows, add, error):
    formset, _ = edit(swim, rows, add)
    assert not formset.is_valid()
    assert error in formset.non_form_errors()


def test_a_drawn_punishment_can_be_reworded_not_removed(crew, swim):
    _, bogdan = crew
    check_in(bogdan, swim, date(2026, 11, 2))
    with at("2026-11-09 08:00Z"):
        services.open_spins()
        spin = Spin.objects.filter(member=bogdan).first()
        assert spin is not None
        services.draw(by=bogdan, spin_id=spin.pk, rng=Pick(0))  # "20 burpees"

    formset, _ = edit(swim, [{"DELETE": True}, {}, {}, {}])
    assert not formset.is_valid()
    [refused] = formset.non_form_errors()
    assert "protected related objects: spin Bogdan" in refused  # Django's own guard

    formset, save = edit(swim, [{"text": "30 burpees"}, {}, {}, {}])
    assert formset.is_valid()
    save()
    spin.refresh_from_db()
    assert spin.punishment is not None
    assert spin.punishment.text == "30 burpees"
