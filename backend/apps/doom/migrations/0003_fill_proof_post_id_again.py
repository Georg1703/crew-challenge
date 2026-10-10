"""From now on a proof without a post is a draft file, and a spin's proofs are posted with the
spin as they start: every proof of a spin still without one gets the spin (0002 left uploading
and failed ones out, and the previous release recorded none).

Back: nothing to undo; the column stays filled.
"""

from django.db import migrations
from django.db.models import F


def fill(apps, schema_editor):
    Proof = apps.get_model("proofs", "Proof")  # its manager sees removed proofs too
    ContentType = apps.get_model("contenttypes", "ContentType")
    spin_type = ContentType.objects.filter(app_label="doom", model="spin").first()
    if spin_type is None:
        return  # a new database: no proofs yet
    Proof.objects.filter(subject_type=spin_type, post_id__isnull=True).update(
        post_id=F("subject_id")
    )


class Migration(migrations.Migration):
    dependencies = [
        ("doom", "0002_fill_proof_post_id"),
    ]

    operations = [migrations.RunPython(fill, migrations.RunPython.noop)]
