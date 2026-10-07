"""Every challenge gets a period kind and length: proposals and months run 1 month, a custom
period (made by the demo seed) becomes that many days. Going back empties a proposal's kind again
and turns days into custom, as the old constraint wants."""

from django.db import migrations


def fill_periods(apps, schema_editor):
    Challenge = apps.get_model("challenges", "Challenge")
    Challenge.objects.filter(period_kind="").update(period_kind="month", period_length=1)
    for c in Challenge.objects.filter(period_kind="custom"):
        c.period_kind = "day"
        c.period_length = (c.end_date - c.period_start).days + 1
        c.save(update_fields=["period_kind", "period_length"])


def empty_periods(apps, schema_editor):
    Challenge = apps.get_model("challenges", "Challenge")
    Challenge.objects.filter(state="proposed").update(period_kind="")
    Challenge.objects.filter(period_kind="day").update(period_kind="custom")


class Migration(migrations.Migration):
    dependencies = [
        ("challenges", "0009_period_length"),
    ]

    operations = [
        migrations.RunPython(fill_periods, empty_periods),
    ]
