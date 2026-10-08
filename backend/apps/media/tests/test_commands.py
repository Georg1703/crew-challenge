from io import StringIO

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_repick_posters_reports_and_dry_runs(object_storage):
    out = StringIO()
    call_command("repick_posters", "--dry-run", stdout=out)
    assert out.getvalue().startswith("Would drop 0 blank poster(s).")

    out = StringIO()
    call_command("repick_posters", stdout=out)
    assert out.getvalue().startswith("Dropped 0 blank poster(s).")
