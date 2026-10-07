"""The old rule columns leave the database (they left the model in 0008, a release ago).

Going back adds them again, empty and nullable; 0008 going back fills them.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("challenges", "0010_fill_period_lengths"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE challenges_challenge
                    DROP COLUMN frequency,
                    DROP COLUMN weekdays,
                    DROP COLUMN times,
                    DROP COLUMN target_scope,
                    DROP COLUMN target_value
            """,
            reverse_sql="""
                ALTER TABLE challenges_challenge
                    ADD COLUMN frequency varchar(20) NULL,
                    ADD COLUMN weekdays smallint NULL CHECK (weekdays >= 0),
                    ADD COLUMN times smallint NULL CHECK (times >= 0),
                    ADD COLUMN target_scope varchar(20) NULL,
                    ADD COLUMN target_value numeric(10, 2) NULL
            """,
        ),
    ]
