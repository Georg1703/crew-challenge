"""Proof becomes yes or no: a challenge that took any kind of proof now asks for a photo or a video.

`proof_kind` leaves the model; its column stays one release (with a database default, so this
release can insert without it) for the previous release, and goes in the punishments stage.
"""

from django.db import migrations, models

KINDS_WITH_PROOF = ("photo", "video", "photo_or_video")


def ask_for_proof(apps, schema_editor):
    Challenge = apps.get_model("challenges", "Challenge")  # its manager sees deleted rows too
    Challenge.objects.filter(proof_kind__in=KINDS_WITH_PROOF).update(proof_required=True)
    Challenge.objects.filter(proof_kind="none").update(proof_required=False)


def kind_from_proof(apps, schema_editor):
    """Back: challenges asking for proof take a photo or a video (the exact old kind is lost)."""
    Challenge = apps.get_model("challenges", "Challenge")
    Challenge.objects.filter(proof_required=True, proof_kind="none").update(
        proof_kind="photo_or_video"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("challenges", "0013_period_kind_required"),
    ]

    operations = [
        migrations.RunPython(ask_for_proof, kind_from_proof),
        migrations.RunSQL(
            sql="ALTER TABLE challenges_challenge ALTER COLUMN proof_kind SET DEFAULT 'none'",
            reverse_sql="ALTER TABLE challenges_challenge ALTER COLUMN proof_kind DROP DEFAULT",
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.RemoveField(model_name="challenge", name="proof_kind")],
        ),
        migrations.AlterField(
            model_name="challenge",
            name="proof_required",
            field=models.BooleanField(
                default=False, help_text="Each check-in asks for a photo or a video; else no proof."
            ),
        ),
    ]
