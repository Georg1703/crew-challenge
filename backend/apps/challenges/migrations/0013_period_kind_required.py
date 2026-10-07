"""Every challenge has a period kind, and a month window needs a period counted in months.

The stage 3 release always writes a kind and never a month window, so it keeps working while
this runs.
"""

import django.db.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("challenges", "0012_month_windows"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="challenge", name="challenge_period_matches_state"),
        migrations.AddConstraint(
            model_name="challenge",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
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
                )
                & ~models.Q(period_kind=""),
                name="challenge_period_matches_state",
            ),
        ),
        migrations.AddConstraint(
            model_name="challenge",
            constraint=models.CheckConstraint(
                condition=~models.Q(window="month") | models.Q(period_kind="month"),
                name="challenge_month_windows_in_months",
            ),
        ),
    ]
