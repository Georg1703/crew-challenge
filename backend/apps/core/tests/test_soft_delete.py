"""SoftDeleteModel, tested on a throwaway model created only for these tests."""

from collections.abc import Iterator

import pytest
import time_machine
from django.db import connection, models
from django.test.utils import isolate_apps

from apps.core.models import SoftDeleteModel

pytestmark = pytest.mark.django_db


@pytest.fixture
def note_model() -> Iterator[type[SoftDeleteModel]]:
    with isolate_apps("apps.core"):

        class Note(SoftDeleteModel):
            text = models.CharField(max_length=20)

            class Meta(SoftDeleteModel.Meta):
                app_label = "core"

            def __str__(self) -> str:
                return self.text

        class Pin(models.Model):
            note = models.ForeignKey(Note, on_delete=models.CASCADE)

            class Meta:
                app_label = "core"

            def __str__(self) -> str:
                return str(self.pk)

        with connection.schema_editor() as editor:
            editor.create_model(Note)
            editor.create_model(Pin)
        Note.Pin = Pin  # type: ignore[attr-defined]
        yield Note  # the test's transaction rolls the tables back


def test_delete_keeps_the_row_and_hides_it(note_model):
    note = note_model.objects.create(text="a")
    with time_machine.travel("2026-11-01 12:00Z", tick=False):
        note.delete()
    assert note.is_deleted
    assert not note_model.objects.filter(pk=note.pk).exists()
    kept = note_model.all_objects.get(pk=note.pk)
    assert kept.deleted_at.isoformat() == "2026-11-01T12:00:00+00:00"


def test_queryset_delete_is_soft_and_counts_only_live_rows(note_model):
    first = note_model.objects.create(text="a")
    note_model.objects.create(text="b")
    first.delete()
    assert note_model.objects.all().delete() == (1, {"core.Note": 1})
    assert note_model.objects.count() == 0
    assert note_model.all_objects.count() == 2
    assert note_model.all_objects.dead().count() == 2


def test_deleting_twice_keeps_the_first_time(note_model):
    note = note_model.objects.create(text="a")
    with time_machine.travel("2026-11-01 12:00Z", tick=False):
        note.delete()
    with time_machine.travel("2026-11-05 12:00Z", tick=False):
        note.delete()
    assert note_model.all_objects.get(pk=note.pk).deleted_at.day == 1


def test_foreign_keys_still_reach_a_deleted_row(note_model):
    note = note_model.objects.create(text="a")
    pin = note_model.Pin.objects.create(note=note)
    note.delete()
    assert note_model.Pin.objects.get(pk=pin.pk).note.text == "a"


def test_restore_and_hard_delete(note_model):
    note = note_model.objects.create(text="a")
    note.delete()
    note.restore()
    assert note_model.objects.filter(pk=note.pk).exists()
    note.hard_delete()
    assert not note_model.all_objects.filter(pk=note.pk).exists()
    other = note_model.objects.create(text="b")
    assert note_model.all_objects.filter(pk=other.pk).hard_delete()[0] == 1
