# Recipe: new endpoint (backend → contract → frontend)

Example: `POST /api/v1/crew/invites` (admin creates an invite).

## Backend
1. **Service.** Add the write to `apps/crews/services.py`:
   ```python
   def create_invite(*, crew: Crew, created_by: Member) -> Invite: ...
   ```
   Business rules and permissions that depend on data belong here. Raise `DomainError`
   subclasses with a stable `code`.
2. **Service tests** in `apps/crews/tests/test_services.py`: happy path and every rule.
3. **Serializers** in `api/serializers.py`: one input serializer (`CreateInviteIn`) and one output
   serializer (`InviteOut`). Suffix `In` / `Out`. No logic in serializers.
4. **View** in `api/views.py`: permission classes, `@extend_schema(request=..., responses=...)`,
   validate → call service → serialize.
5. **URL** in `api/urls.py`, following `docs/architecture/api-conventions.md`.
6. **API tests** in `api` tests: status codes, permission denied for non-admins, response shape,
   error `code` values.

## Contract
7. Run `make schema`. Review the diff of `contracts/openapi.yaml`.

## Frontend
8. Add a hook in `frontend/src/features/crew/api.ts`:
   ```ts
   export function useCreateInvite() {
     const qc = useQueryClient();
     return useMutation({
       mutationFn: async () => unwrap(await api.POST('/api/v1/crew/invites')),
       onSuccess: () => qc.invalidateQueries({ queryKey: ['crew', 'invites'] }),
     });
   }
   ```
9. Map new error codes in `src/i18n/ro.json` and `en.json` under `errors.<code>`.
10. Use the hook from a component; add or update a component test.
11. Run `make check`.
