"""A challenge's rule becomes a window and a need (docs/plans/periods.md, stage 2).

The new fields are added here and filled in 0008. The old ones become nullable, so the new code can
leave them out while the previous release still reads them; they leave the model in 0008 and the
database in a later release (docs/recipes/new-migration.md).
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("challenges", "0006_participant"),
    ]

    operations = [
        migrations.AddField(
            model_name="challenge",
            name="window",
            field=models.CharField(
                choices=[
                    ("day", "Each day"),
                    ("week", "Each week, Monday to Sunday"),
                    ("period", "The whole period"),
                ],
                default="day",
                help_text="The unit that is judged (apps/challenges/windows.py).",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="challenge",
            name="on_days",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text=(
                    "Weekdays that count, as a bit mask (Monday = 1 ... Sunday = 64); "
                    "0 = every day."
                ),
            ),
        ),
        migrations.AddField(
            model_name="challenge",
            name="need_kind",
            field=models.CharField(
                choices=[("count", "A number of check-ins"), ("amount", "A total amount")],
                default="count",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="challenge",
            name="need_value",
            field=models.DecimalField(
                decimal_places=2,
                default=1,
                help_text="What each window needs: a number of check-ins, or a total.",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="challenge",
            name="day_min",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="The least amount for a day's check-in to count (numbers only).",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="challenge",
            constraint=models.CheckConstraint(
                condition=models.Q(need_value__gt=0), name="challenge_need_above_zero"
            ),
        ),
        migrations.AddConstraint(
            model_name="challenge",
            constraint=models.CheckConstraint(
                condition=models.Q(need_kind="count") | models.Q(measure="quantity"),
                name="challenge_a_total_needs_numbers",
            ),
        ),
        migrations.AddConstraint(
            model_name="challenge",
            constraint=models.CheckConstraint(
                condition=models.Q(day_min__isnull=True)
                | models.Q(measure="quantity", need_kind="count"),
                name="challenge_a_day_minimum_needs_counted_numbers",
            ),
        ),
        migrations.AddConstraint(
            model_name="challenge",
            constraint=models.CheckConstraint(
                condition=~models.Q(window="day") | models.Q(need_kind="count", need_value=1),
                name="challenge_a_day_needs_one_check_in",
            ),
        ),
        migrations.AddConstraint(
            model_name="challenge",
            constraint=models.CheckConstraint(
                condition=models.Q(on_days=0) | models.Q(window="day"),
                name="challenge_chosen_days_only_per_day",
            ),
        ),
        migrations.AlterField(
            model_name="challenge",
            name="frequency",
            field=models.CharField(
                choices=[
                    ("daily", "Every day"),
                    ("weekdays", "Chosen days of the week"),
                    ("times_per_week", "A number of times a week"),
                    ("times_per_period", "A number of times in the period"),
                    ("once", "Once, by the end"),
                ],
                default="daily",
                max_length=20,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="challenge",
            name="weekdays",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Bit mask of chosen days: Monday = 1, Tuesday = 2, ... Sunday = 64.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="challenge",
            name="target_scope",
            field=models.CharField(
                choices=[
                    ("none", "No target"),
                    ("per_check_in", "Each check-in"),
                    ("per_week", "Each week"),
                    ("per_period", "The whole period"),
                ],
                default="none",
                max_length=20,
                null=True,
            ),
        ),
    ]
