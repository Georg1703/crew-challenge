from django.db import migrations, models


class Migration(migrations.Migration):
    """Drops rounds once 0002 moved their period onto the challenges (a separate transaction)."""

    dependencies = [
        ("challenges", "0002_proposal_pool"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="round",
            name="chosen",
        ),
        migrations.RemoveField(
            model_name="round",
            name="chosen_by",
        ),
        migrations.RemoveField(
            model_name="round",
            name="crew",
        ),
        migrations.RemoveField(
            model_name="vote",
            name="round",
        ),
        migrations.RemoveField(
            model_name="challenge",
            name="round",
        ),
        migrations.AlterField(
            model_name="challenge",
            name="end_date",
            field=models.DateField(blank=True, help_text="Last day of the period.", null=True),
        ),
        migrations.AlterField(
            model_name="challenge",
            name="start_date",
            field=models.DateField(
                blank=True,
                help_text="First day that counts (after period_start when chosen late).",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="challenge",
            name="state",
            field=models.CharField(
                choices=[("proposed", "Proposed"), ("chosen", "Chosen")],
                default="proposed",
                max_length=12,
            ),
        ),
        migrations.AddIndex(
            model_name="challenge",
            index=models.Index(
                fields=["crew", "state", "start_date"],
                name="challenges__crew_id_84b849_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="challenge",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("end_date__isnull", True),
                        ("period_kind", ""),
                        ("period_start__isnull", True),
                        ("start_date__isnull", True),
                        ("state", "proposed"),
                    ),
                    models.Q(
                        ("end_date__gte", models.F("start_date")),
                        ("period_start__isnull", False),
                        ("start_date__gte", models.F("period_start")),
                        ("state", "chosen"),
                        models.Q(("period_kind", ""), _negated=True),
                    ),
                    _connector="OR",
                ),
                name="challenge_period_matches_state",
            ),
        ),
        migrations.AddConstraint(
            model_name="vote",
            constraint=models.UniqueConstraint(
                fields=("challenge", "member"), name="vote_one_per_member_and_challenge"
            ),
        ),
        migrations.DeleteModel(
            name="Round",
        ),
    ]
