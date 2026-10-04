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
