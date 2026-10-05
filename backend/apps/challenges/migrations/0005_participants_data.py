"""Fold participations into the invitees (renamed to participants in 0006).

One row per member and challenge from now on:
- a participation's end date becomes the row's `left_on`;
- in a scheduled challenge, an invitee without a participation had opted out: the row goes;
- a participation without an invitee (made by hand in Django admin) gets its row.
"""

import uuid

from django.db import migrations, models


def fold_participations(apps, schema_editor):
    Challenge = apps.get_model("challenges", "Challenge")
    Invitee = apps.get_model("challenges", "Invitee")
    Participation = apps.get_model("challenges", "Participation")

    ended = {
        (p.challenge_id, p.member_id): p.ended_on for p in Participation.objects.all()
    }
    for invitee in Invitee.objects.all():
        key = (invitee.challenge_id, invitee.member_id)
        if key in ended and ended[key] is not None:
            invitee.left_on = ended[key]
            invitee.save(update_fields=["left_on"])

    scheduled = Challenge.objects.filter(state="chosen").values_list("pk", flat=True)
    for invitee in Invitee.objects.filter(challenge_id__in=list(scheduled)):
        if (invitee.challenge_id, invitee.member_id) not in ended:
            invitee.delete()

    known = set(Invitee.objects.values_list("challenge_id", "member_id"))
    Invitee.objects.bulk_create(
        Invitee(
            id=uuid.uuid4(),
            crew_id=p.crew_id,
            challenge_id=p.challenge_id,
            member_id=p.member_id,
            left_on=p.ended_on,
        )
        for p in Participation.objects.all()
        if (p.challenge_id, p.member_id) not in known
    )


class Migration(migrations.Migration):
    dependencies = [
        ("challenges", "0004_invitees"),
    ]

    operations = [
        migrations.AddField(
            model_name="invitee",
            name="left_on",
            field=models.DateField(
                blank=True,
                help_text="Last day that counts, when the member left during it.",
                null=True,
            ),
        ),
        migrations.RunPython(fold_participations, migrations.RunPython.noop),
    ]
