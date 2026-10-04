import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { useEffect, type ReactNode } from "react";
import { I18nextProvider } from "react-i18next";

import { onUnauthorized } from "@/api";
import { meKey } from "@/features/auth";
import { i18n } from "@/i18n";
import { MotionConfig } from "@/shared/motion";
import { ToastProvider } from "@/shared/ui";

/** Everything the app needs around it. Tests render screens inside the same providers. */
export function Providers({ client, children }: { client: QueryClient; children: ReactNode }) {
  // Any 401 means the session is gone: forget the user; the auth guard sends them to /login.
  useEffect(() => onUnauthorized(() => client.setQueryData(meKey, null)), [client]);

  return (
    <QueryClientProvider client={client}>
      <I18nextProvider i18n={i18n}>
        <MotionConfig reducedMotion="user">
          <ToastProvider>{children}</ToastProvider>
        </MotionConfig>
      </I18nextProvider>
    </QueryClientProvider>
  );
}
