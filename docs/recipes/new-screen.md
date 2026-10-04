# Recipe: new screen

Example: a "Challenge" screen in a `challenge` feature.

1. Create or reuse the feature folder `frontend/src/features/challenge/` with `api.ts`,
   `routes/`, `components/`, and `index.ts`.
2. Add the route component `routes/ChallengeRoute.tsx`. Data comes from hooks in `api.ts`.
3. Export the route from `index.ts` and register it lazily in `src/app/routes.tsx`:
   ```ts
   { path: 'challenge', lazy: () => import('@/features/challenge').then(m => ({ Component: m.ChallengeRoute })) }
   ```
4. If it belongs in the bottom tab bar, add it to the tabs in `src/app/layout/AppShell.tsx`.
5. Strings: add keys under `challenge.*` to `ro.json` and `en.json`.
6. Build it from `Screen` and other `shared/ui` components. Layout-only CSS goes in a CSS Module
   using tokens. Need a new kind of element? Add it to `shared/ui` with all states and show it on
   `/design` first (`docs/design-system.md`).
7. Motion: pick one signature animation for the screen using `shared/motion` presets; check it
   with reduced motion turned on.
8. States: design loading (skeleton), empty, and error states. The screen must look complete in
   each.
9. Check at 360 px width, with safe-area insets, and in dark mode.
10. Add a test with `renderScreen()` and `vi.spyOn(api, ...)`; add a Playwright step
    (`frontend/e2e/`) if the screen is part of a main flow.
11. Run `make check`.
