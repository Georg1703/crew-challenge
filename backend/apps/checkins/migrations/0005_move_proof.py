"""Proof moves to its own app (apps/proofs), to back more than check-ins.

Fills who added each proof and its subject (the check-in), then hands the model to the proofs app
without touching the database: the table stays `checkins_proof` (proofs 0001). Its own migration,
apart from 0004's table changes: Postgres refuses to alter a table with updates pending in the
same transaction.
"""

from django.db import migrations
from django.db.models import F, OuterRef, Subquery


def fill(apps, schema_editor):
    Proof = apps.get_model("checkins", "Proof")  # its manager sees removed proofs too
    CheckIn = apps.get_model("checkins", "CheckIn")
    ContentType = apps.get_model("contenttypes", "ContentType")
    check_in_type, _ = ContentType.objects.get_or_create(app_label="checkins", model="checkin")
    member = CheckIn.objects.filter(pk=OuterRef("check_in_id")).values("member_id")[:1]
    Proof.objects.filter(subject_id__isnull=True).update(
        member_id=Subquery(member), subject_type_id=check_in_type.pk, subject_id=F("check_in_id")
    )


def unfill(apps, schema_editor):
    """Back: proofs added since have no `check_in`; their subject is one."""
    Proof = apps.get_model("checkins", "Proof")
    Proof.objects.filter(check_in__isnull=True).update(check_in_id=F("subject_id"))


class Migration(migrations.Migration):
    dependencies = [
        ("checkins", "0004_proof_subject"),
    ]

    operations = [
        migrations.RunPython(fill, unfill),
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.DeleteModel(name="Proof")],
        ),
    ]
