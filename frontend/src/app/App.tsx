import { useState } from "react";
import { createBrowserRouter, RouterProvider } from "react-router";

import { Providers } from "./providers";
import { createQueryClient } from "./queryClient";
import { routes } from "./routes";

const router = createBrowserRouter(routes);

export function App() {
  const [client] = useState(createQueryClient);
  return (
    <Providers client={client}>
      <RouterProvider router={router} />
    </Providers>
  );
}
