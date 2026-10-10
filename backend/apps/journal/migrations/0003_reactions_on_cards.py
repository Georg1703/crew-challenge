"""Reactions point at cards now (target `entry`): a check-in's move to its first post's card, a
spin's to its drawn card. One whose card is missing is dropped.

Back: nothing to undo; the reactions stay on the cards.
"""

from django.db import migrations


def move(apps, schema_editor):
    Reaction = apps.get_model("reactions", "Reaction")
    JournalEntry = apps.get_model("journal", "JournalEntry")
    CheckInEntry = apps.get_model("checkins", "CheckInEntry")
    ContentType = apps.get_model("contenttypes", "ContentType")
    kind = {
        model: ContentType.objects.filter(app_label=app, model=model).first()
        for app, model in (("checkins", "checkin"), ("checkins", "checkinentry"), ("doom", "spin"))
    }
    if not Reaction.objects.exists():
        return  # a new database: nothing to move
    entry_type, _ = ContentType.objects.get_or_create(app_label="journal", model="journalentry")
    for reaction in Reaction.objects.exclude(target_type=entry_type):
        if reaction.target_type_id == getattr(kind["checkin"], "pk", None):
            subject = (
                CheckInEntry.objects.filter(check_in_id=reaction.target_id)
                .order_by("number")
                .values_list("pk", flat=True)
                .first()
            )
            card = JournalEntry.objects.filter(
                kind="check_in", subject_type=kind["checkinentry"], subject_id=subject
            ).first()
        elif reaction.target_type_id == getattr(kind["spin"], "pk", None):
            card = JournalEntry.objects.filter(
                kind="spin", subject_type=kind["spin"], subject_id=reaction.target_id
            ).first()
        else:
            continue  # another target: not ours to move
        if card is None:
            reaction.delete()
            continue
        reaction.target_type, reaction.target_id = entry_type, card.pk
        reaction.save(update_fields=["target_type", "target_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0002_backfill"),
        ("reactions", "0001_initial"),
    ]

    operations = [migrations.RunPython(move, migrations.RunPython.noop)]
