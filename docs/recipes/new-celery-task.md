# Recipe: new Celery task

1. Put the logic in a service function first and test it there.
2. Add a thin task in `apps/<app>/tasks.py`:
   ```python
   @shared_task(bind=True, autoretry_for=(TransientError,), retry_backoff=True, max_retries=5)
   def start_transcode(self, proof_id: str) -> None:
       services.start_transcode(proof_id=UUID(proof_id))
   ```
   - Arguments are ids (strings), never model instances.
   - The task must be idempotent: running it twice has the same effect as once. Check state in
     the service before acting.
3. Enqueue from services with `transaction.on_commit(lambda: task.delay(str(obj.id)))` so the
   task never runs before the data is committed.
4. Scheduled tasks are registered in `config/celery.py` (`beat_schedule`) with an explicit time
   zone. Jobs that depend on crew-local time loop over crews and use `clock.crew_today(crew)`.
5. Tests call the service directly; one test checks the task wiring with Celery in eager mode.
6. Run `make check`.
