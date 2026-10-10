"""From now on a proof without a post is a draft file: proofs added while the previous release
ran (it did not record posts yet) belonged to a check-in already, so they get its first entry, as
in 0006.

Back: nothing to undo; the column stays filled.
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
        ("checkins", "0007_check_in_pending"),
    ]

    operations = [migrations.RunPython(fill, migrations.RunPython.noop)]
