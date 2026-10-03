# Recipe: new backend app

Example: adding `challenges`.

1. Check `docs/glossary.md` for the domain words. Add new ones there first.
2. Create the folder with the standard layout:
   ```
   backend/apps/challenges/
   |-- __init__.py
   |-- apps.py            # ChallengesConfig, name = "apps.challenges"
   |-- models.py
   |-- services.py
   |-- selectors.py
   |-- api/__init__.py
   |-- api/serializers.py
   |-- api/views.py
   |-- api/urls.py
   |-- admin.py
   |-- tasks.py
   |-- migrations/__init__.py
   `-- tests/__init__.py
   ```
3. Add `"apps.challenges"` to `INSTALLED_APPS` in `config/settings/base.py`.
4. Include `apps.challenges.api.urls` under `/api/v1/` in `config/urls.py`.
5. Add the app to the import-linter "core does not depend on domain apps" contract in
   `backend/pyproject.toml`.
6. Models inherit `CrewScopedModel` if they belong to a crew (almost always), otherwise
   `TimeStampedModel`.
7. Add factories in `backend/tests/factories/challenges.py`.
8. Create the first migration (`docs/recipes/new-migration.md`).
9. Run `make check`.
