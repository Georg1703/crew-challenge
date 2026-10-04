/** The API's single error shape: {"error": {"code", "message", "fields"}}. */
export interface ApiErrorBody {
  code: string;
  message: string;
  fields?: Record<string, string[]>;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: Record<string, string[]>;

  constructor(status: number, body: Partial<ApiErrorBody> | undefined) {
    super(body?.message ?? "Request failed.");
    this.name = "ApiError";
    this.status = status;
    this.code = body?.code ?? (status >= 500 ? "server_error" : "error");
    this.fields = body?.fields ?? {};
  }

  /** The first message for a form field, if the API rejected it. */
  field(name: string): string | undefined {
    return this.fields[name]?.[0];
  }
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

/** Network failures (offline, DNS) get their own code so the UI can say "check your connection". */
export const NETWORK_ERROR = "network_error";
