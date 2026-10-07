# Recipe: new migration

1. Change the model in `apps/<app>/models.py`.
2. Run `make makemigrations app=<app>`. Name non-trivial migrations:
   `make makemigrations app=crews` then rename the file to describe the change
   (`0003_member_avatar_seed.py`).
3. Read the generated migration. Check defaults, nullability, and indexes.
4. Deploys run migrations before new code starts, while the old code may still be serving.
   Keep every migration compatible with the previous release:
   - Add a column as nullable or with a database default (`db_default=`, next to `default=`):
     the previous release inserts rows without it, and a default only in Python does not help
     there. Backfill in a data migration if needed.
   - Remove or rename a column in two releases: stop using it first, remove it later.
5. Data migrations use `apps.get_model(...)`, never direct model imports, and must be reversible
   or explicitly `migrations.RunPython.noop` on reverse with a comment explaining why.
6. Run `make check` (it fails if migrations are missing).
