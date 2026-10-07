"""A proposal says how long it runs: `period_kind` (months, weeks or days) and `period_length`.

The period constraint no longer asks a proposal for an empty `period_kind`, so the previous release
(which leaves it empty) keeps working during the deploy; 0010 fills it.
"""

import django.db.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("challenges", "0008_fill_challenge_rules"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="challenge", name="challenge_period_matches_state"),
        migrations.AddField(
            model_name="challenge",
            name="period_length",
            field=models.PositiveSmallIntegerField(
                default=1, help_text="How many months, weeks or days the challenge runs."
            ),
        ),
        migrations.AlterField(
            model_name="challenge",
            name="period_kind",
            field=models.CharField(
                choices=[("month", "Months"), ("week", "Weeks"), ("day", "Days")],
                default="month",
                help_text="The unit of the period's length, chosen by the creator.",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="challenge",
            name="period_start",
            field=models.DateField(
                blank=True,
                help_text="First day of the period: the 1st for months, a Monday for weeks.",
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="challenge",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    state="proposed",
                    period_start__isnull=True,
                    start_date__isnull=True,
                    end_date__isnull=True,
                )
                | models.Q(
                    state="chosen",
                    period_start__isnull=False,
                    start_date__gte=django.db.models.F("period_start"),
                    end_date__gte=django.db.models.F("start_date"),
                )
                & ~models.Q(period_kind=""),
                name="challenge_period_matches_state",
            ),
        ),
        migrations.AddConstraint(
            model_name="challenge",
            constraint=models.CheckConstraint(
                condition=models.Q(period_length__gte=1), name="challenge_period_length_above_zero"
            ),
        ),
    ]
