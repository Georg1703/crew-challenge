"""Each proof of a check-in records the post that published it: the day's first entry (until now a
proof backed the whole day). Proofs added while this release runs get the same later, in the
migration of the release that starts reading it.

Back: nothing to undo; the column stays filled and nothing reads it yet.
"""

from django.db import migrations
from django.db.models import OuterRef, Subquery


def fill(apps, schema_editor):
    Proof = apps.get_model("proofs", "Proof")  # its manager sees removed proofs too
    CheckInEntry = apps.get_model("checkins", "CheckInEntry")
    ContentType = apps.get_model("contenttypes", "ContentType")
    check_in_type = ContentType.objects.filter(app_label="checkins", model="checkin").first()
    if check_in_type is None:
        return  # a new database: no proofs yet
    first = (
        CheckInEntry.objects.filter(check_in_id=OuterRef("subject_id"))
        .order_by("number")
        .values("pk")[:1]
    )
    Proof.objects.filter(subject_type=check_in_type, post_id__isnull=True).update(
        post_id=Subquery(first)
    )


class Migration(migrations.Migration):
    dependencies = [
        ("checkins", "0005_move_proof"),
        ("proofs", "0002_proof_post_id"),
    ]

    operations = [migrations.RunPython(fill, migrations.RunPython.noop)]
