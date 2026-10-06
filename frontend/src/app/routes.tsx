import type { RouteObject } from "react-router";

import { NotFoundRoute } from "./NotFoundRoute";
import { RequireAuth } from "./RequireAuth";
import { AppShell } from "./layout/AppShell";

/** Route table. Screens load lazily so each tab only downloads its own code. */
export const routes: RouteObject[] = [
  {
    path: "/login",
    lazy: () => import("@/features/auth").then((m) => ({ Component: m.LoginRoute })),
  },
  {
    path: "/join/:code",
    lazy: () => import("@/features/auth").then((m) => ({ Component: m.JoinRoute })),
  },
  {
    element: <RequireAuth />,
    children: [
      {
        path: "challenges/new",
        lazy: () => import("@/features/challenges").then((m) => ({ Component: m.ProposeRoute })),
      },
      {
        path: "challenges/:id/edit",
        lazy: () => import("@/features/challenges").then((m) => ({ Component: m.ProposeRoute })),
      },
      {
        path: "welcome",
        lazy: () => import("@/features/auth").then((m) => ({ Component: m.WelcomeRoute })),
      },
      {
        element: <AppShell />,
        children: [
          {
            index: true,
            lazy: () => import("@/features/home").then((m) => ({ Component: m.HomeRoute })),
          },
          {
            path: "crew",
            lazy: () => import("@/features/crew").then((m) => ({ Component: m.CrewRoute })),
          },
          {
            path: "crew/members",
            lazy: () => import("@/features/crew").then((m) => ({ Component: m.MembersRoute })),
          },
          {
            path: "crew/members/:id",
            lazy: () => import("@/features/crew").then((m) => ({ Component: m.MemberRoute })),
          },
          {
            path: "challenges",
            lazy: () =>
              import("@/features/challenges").then((m) => ({ Component: m.ChallengesRoute })),
          },
          {
            path: "challenges/:id",
            lazy: () =>
              import("@/features/challenges").then((m) => ({ Component: m.ChallengeRoute })),
          },
          {
            path: "me",
            lazy: () => import("@/features/me").then((m) => ({ Component: m.MeRoute })),
          },
        ],
      },
    ],
  },
  ...(import.meta.env.DEV
    ? [
        {
          path: "/design",
          lazy: () => import("@/design/DesignRoute").then((m) => ({ Component: m.DesignRoute })),
        },
      ]
    : []),
  { path: "*", Component: NotFoundRoute },
];
