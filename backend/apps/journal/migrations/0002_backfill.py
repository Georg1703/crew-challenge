"""The cards of everything posted so far, written by the code the app uses (`journal_backfill`), so
the stored journal is complete from the deploy on. First, as `doom` 0004 did: spins the release
before served with a proof during its deploy get that proof's time in `done_at`.

Once released, this migration's body becomes a no-op (an old migration must not run today's code);
the command stays as the repair tool. Back: nothing to undo (the cards go with 0001's table).
"""

import io

from django.core.management import call_command
from django.db import migrations
from django.db.models import Exists, OuterRef, Subquery

SHOWN = ("processing", "ready")  # proofs.selectors.SHOWN; a migration keeps its own copy


def serve_shown(apps, schema_editor):
    Spin = apps.get_model("doom", "Spin")
    Proof = apps.get_model("proofs", "Proof")
    ContentType = apps.get_model("contenttypes", "ContentType")
    spin_type = ContentType.objects.filter(app_label="doom", model="spin").first()
    if spin_type is None:
        return  # a new database: no proofs yet
    shown = Proof.objects.filter(
        subject_type=spin_type, subject_id=OuterRef("pk"), status__in=SHOWN, deleted_at=None
    ).exclude(post_id=None)
    first = shown.order_by("updated_at").values("updated_at")[:1]
    Spin.objects.filter(done_at=None).filter(Exists(shown)).update(done_at=Subquery(first))


def backfill(apps, schema_editor):
    call_command("journal_backfill", stdout=io.StringIO())


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0001_journal_entry"),
        ("checkins", "0008_fill_proof_post_id_again"),
        ("doom", "0004_served_by_posting"),
    ]

    operations = [
        migrations.RunPython(serve_shown, migrations.RunPython.noop),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
