"""Fill each challenge's window and need from its old fields; the old fields leave the model.

`frequency`, `weekdays`, `times`, `target_scope` and `target_value` stay in the database (nullable,
see 0007) so the previous release keeps working during the deploy; a later release drops them.
Going back fills the old fields of rows made after this migration from their window and need.
"""

from decimal import Decimal

from django.db import migrations

OLD_FIELDS = ("frequency", "weekdays", "times", "target_scope", "target_value")


def rule(c) -> dict:
    """The window and need written in the old fields (also in docs/plans/periods.md)."""
    total = c.target_value
    if c.target_scope == "per_week" and total:
        return {"window": "week", "need_kind": "amount", "need_value": total}
    if c.target_scope == "per_period" and total:
        return {"window": "period", "need_kind": "amount", "need_value": total}
    day_min = total if c.target_scope == "per_check_in" and total else None
    times = Decimal(c.times or 1)  # every times_* challenge has times; 1 if a row lacks it
    if c.frequency == "times_per_week":
        return {"window": "week", "need_value": times, "day_min": day_min}
    if c.frequency == "times_per_period":
        return {"window": "period", "need_value": times, "day_min": day_min}
    if c.frequency == "once":
        return {"window": "period", "day_min": day_min}
    on_days = c.weekdays if c.frequency == "weekdays" else 0
    return {"window": "day", "on_days": on_days or 0, "day_min": day_min}


def old_fields(c) -> dict:
    """The old fields for a window and need, for a row made after this migration."""
    fields = {"weekdays": 0, "times": None, "target_scope": "none", "target_value": None}
    if c.day_min:
        fields.update(target_scope="per_check_in", target_value=c.day_min)
    if c.need_kind == "amount":
        scope = "per_week" if c.window == "week" else "per_period"
        fields.update(target_scope=scope, target_value=c.need_value)
        return {**fields, "frequency": "daily"}
    times = int(c.need_value)
    if c.window == "week":
        return {**fields, "frequency": "times_per_week", "times": times}
    if c.window == "period":
        if times == 1:
            return {**fields, "frequency": "once"}
        return {**fields, "frequency": "times_per_period", "times": times}
    if c.on_days:
        return {**fields, "frequency": "weekdays", "weekdays": c.on_days}
    return {**fields, "frequency": "daily"}


def fill_rules(apps, schema_editor):
    Challenge = apps.get_model("challenges", "Challenge")
    for c in Challenge.objects.all():  # soft-deleted rows too: the default manager isn't used here
        for field, value in {"need_kind": "count", "need_value": 1, **rule(c)}.items():
            setattr(c, field, value)
        c.save(update_fields=["window", "on_days", "need_kind", "need_value", "day_min"])


def fill_old_fields(apps, schema_editor):
    Challenge = apps.get_model("challenges", "Challenge")
    for c in Challenge.objects.filter(frequency__isnull=True):
        for field, value in old_fields(c).items():
            setattr(c, field, value)
        c.save(update_fields=list(OLD_FIELDS))


class Migration(migrations.Migration):
    dependencies = [
        ("challenges", "0007_challenge_rules"),
    ]

    operations = [
        migrations.RunPython(fill_rules, fill_old_fields),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name="challenge", name=name) for name in OLD_FIELDS
            ],
        ),
    ]
