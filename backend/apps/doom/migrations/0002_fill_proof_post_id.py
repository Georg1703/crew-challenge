"""Each proof the crew can see on a spin records the post that published it: the spin itself (a
spin is served once). Uploading and failed ones published nothing and stay empty. Proofs added
while this release runs get the same later, in the migration of the release that starts reading it.

Back: nothing to undo; the column stays filled and nothing reads it yet.
"""

from django.db import migrations
from django.db.models import F

SHOWN = ("processing", "ready")  # proofs.selectors.SHOWN; a migration keeps its own copy


def fill(apps, schema_editor):
    Proof = apps.get_model("proofs", "Proof")  # its manager sees removed proofs too
    ContentType = apps.get_model("contenttypes", "ContentType")
    spin_type = ContentType.objects.filter(app_label="doom", model="spin").first()
    if spin_type is None:
        return  # a new database: no proofs yet
    Proof.objects.filter(subject_type=spin_type, status__in=SHOWN, post_id__isnull=True).update(
        post_id=F("subject_id")
    )


class Migration(migrations.Migration):
    dependencies = [
        ("doom", "0001_initial"),
        ("proofs", "0002_proof_post_id"),
    ]

    operations = [migrations.RunPython(fill, migrations.RunPython.noop)]
