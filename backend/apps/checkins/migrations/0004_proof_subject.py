"""Proof gets who added it and a generic subject, and `check_in` may be empty (0005 fills them
and moves the model to the proofs app). Nullable for one release, so the previous release can
still insert during the deploy; the punishments stage makes them required and drops `check_in`.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("checkins", "0003_proof_duration"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("crews", "0004_crew_max_proposals"),
    ]

    operations = [
        migrations.AlterField(
            model_name="proof",
            name="check_in",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="proofs",
                to="checkins.checkin",
            ),
        ),
        migrations.AddField(
            model_name="proof",
            name="member",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="proofs",
                to="crews.member",
            ),
        ),
        migrations.AddField(
            model_name="proof",
            name="subject_type",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AddField(
            model_name="proof",
            name="subject_id",
            field=models.UUIDField(null=True),
        ),
        migrations.AddIndex(
            model_name="proof",
            index=models.Index(fields=["subject_type", "subject_id"], name="proof_subject"),
        ),
    ]
