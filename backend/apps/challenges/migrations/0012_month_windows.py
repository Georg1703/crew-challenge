"""Challenges can be judged per calendar month, and every row gets a period kind.

A proposal made by the stage 2 release while stage 3 deployed could have an empty `period_kind`;
it gets the default (one month) here, before 0013 requires a kind. Going back keeps the kinds:
the earlier constraint allows them.
"""

from django.db import migrations, models


def fill_empty_kinds(apps, schema_editor):
    Challenge = apps.get_model("challenges", "Challenge")
    Challenge.objects.filter(period_kind="").update(period_kind="month", period_length=1)


class Migration(migrations.Migration):
    dependencies = [
        ("challenges", "0011_drop_old_rule_columns"),
    ]

    operations = [
        migrations.AlterField(
            model_name="challenge",
            name="window",
            field=models.CharField(
                choices=[
                    ("day", "Each day"),
                    ("week", "Each week, Monday to Sunday"),
                    ("month", "Each calendar month"),
                    ("period", "The whole period"),
                ],
                default="day",
                help_text="The unit that is judged (apps/challenges/windows.py).",
                max_length=10,
            ),
        ),
        migrations.RunPython(fill_empty_kinds, migrations.RunPython.noop),
    ]
