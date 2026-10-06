"""Invitee becomes Participant; Participation is gone (its data moved in 0005)."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("challenges", "0005_participants_data"),
        ("crews", "0004_crew_max_proposals"),
    ]

    operations = [
        migrations.DeleteModel(name="Participation"),
        migrations.RemoveConstraint(model_name="invitee", name="invitee_once_per_member"),
        migrations.RenameModel(old_name="Invitee", new_name="Participant"),
        migrations.AlterField(
            model_name="participant",
            name="challenge",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="participants",
                to="challenges.challenge",
            ),
        ),
        migrations.AlterField(
            model_name="participant",
            name="member",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="participations",
                to="crews.member",
            ),
        ),
        migrations.AddConstraint(
            model_name="participant",
            constraint=models.UniqueConstraint(
                fields=("challenge", "member"), name="participant_one_per_member"
            ),
        ),
    ]
