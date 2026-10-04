import type { TFunction } from "i18next";

import { isApiError } from "@/api";

/** A user-facing message for any error: translated by code, falling back to the API's message. */
export function errorMessage(t: TFunction, error: unknown): string {
  if (isApiError(error)) {
    return t(`errors.${error.code}`, { defaultValue: error.message });
  }
  return t("common.somethingWrong");
}
