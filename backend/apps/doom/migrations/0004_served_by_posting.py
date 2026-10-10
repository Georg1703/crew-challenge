"""A spin is served when its owner posts its photos or videos (or taps "Done"), and `done_at` says
when, whichever way. Until now the first proof the crew could see served it: those spins get that
proof's time. The files of spins not served yet are draft files from now on.

Back: nothing to undo; `done_at` stays filled and the drafts stay drafts.
"""

from django.db import migrations, models
from django.db.models import Exists, OuterRef, Subquery

SHOWN = ("processing", "ready")  # proofs.selectors.SHOWN; a migration keeps its own copy


def fill(apps, schema_editor):
    Spin = apps.get_model("doom", "Spin")
    Proof = apps.get_model("proofs", "Proof")  # its manager sees removed proofs too
    ContentType = apps.get_model("contenttypes", "ContentType")
    spin_type = ContentType.objects.filter(app_label="doom", model="spin").first()
    if spin_type is None:
        return  # a new database: no proofs yet
    shown = Proof.objects.filter(
        subject_type=spin_type, subject_id=OuterRef("pk"), status__in=SHOWN, deleted_at=None
    )
    first = shown.order_by("updated_at").values("updated_at")[:1]
    Spin.objects.filter(done_at=None).filter(Exists(shown)).update(done_at=Subquery(first))
    to_serve = Spin.objects.filter(done_at=None).values("pk")
    Proof.objects.filter(subject_type=spin_type, subject_id__in=to_serve).update(post_id=None)


class Migration(migrations.Migration):
    dependencies = [
        ("doom", "0003_fill_proof_post_id_again"),
    ]

    operations = [
        migrations.AlterField(
            model_name="spin",
            name="done_at",
            field=models.DateTimeField(
                blank=True,
                help_text='When it was served: "Done", or its photos and videos posted.',
                null=True,
            ),
        ),
        migrations.RunPython(fill, migrations.RunPython.noop),
    ]
