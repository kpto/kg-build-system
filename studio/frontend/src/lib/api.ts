/**
 * Typed fetch wrapper for every endpoint in `studio/docs/API.md`.
 *
 * One error type, `ApiError`, carries `{status, reason, errors}` and, for the
 * `409` concurrency rejection, the current server document: the contract says a
 * stale revision is rejected *with* the document the client must adopt, so the
 * document belongs on the error rather than being a second return channel.
 *
 * `fetch` is read off `globalThis` at call time so tests can install a fake.
 */

import type {
  AuthoringIndex,
  BlueprintResponse,
  BuildResponse,
  CatalogResponse,
  DataFile,
  DiagnosticsResponse,
  DocumentResponse,
  FieldError,
  InferRequest,
  InferResponse,
  NameSuggestRequest,
  NameSuggestResponse,
  PlanResponse,
  PutDocumentRequest,
  PutDocumentResponse,
  SourceResponse,
  StateResponse,
  WorkspaceRequest,
} from "./types";
import type { ProjectDocument } from "./ir";

export const BACKEND_ORIGIN: string =
  process.env.STUDIO_BACKEND_ORIGIN ?? "http://127.0.0.1:8700";

export const WS_URL: string =
  process.env.STUDIO_WS_ORIGIN ??
  `${BACKEND_ORIGIN.replace(/^http/, "ws")}/ws`;

/** Every non-2xx response, plus the network failure case (`status === 0`). */
export class ApiError extends Error {
  readonly status: number;
  readonly reason: string;
  readonly errors: FieldError[];
  /** Only set by `409`: the document the client must adopt. */
  readonly document?: ProjectDocument;
  /** Only set by `409`: the revision `document` corresponds to. */
  readonly revision?: number;
  /** The decoded body, for endpoints whose error payload carries more. */
  readonly data?: unknown;

  constructor(init: {
    status: number;
    reason: string;
    errors?: FieldError[];
    document?: ProjectDocument;
    revision?: number;
    data?: unknown;
  }) {
    super(init.reason);
    this.name = "ApiError";
    this.status = init.status;
    this.reason = init.reason;
    this.errors = init.errors ?? [];
    this.document = init.document;
    this.revision = init.revision;
    this.data = init.data;
  }

  /** The `409` case: the caller adopts `document`/`revision` and warns the user. */
  get conflict(): boolean {
    return this.status === 409 && this.document !== undefined;
  }

  /** FastAPI's `422` detail: per-field messages worth showing in the inspector. */
  get fieldErrors(): readonly FieldError[] {
    return this.errors;
  }
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

function errorMessage(value: unknown, status: number): string {
  if (typeof value === "string" && value.trim()) return value;
  return `Request failed with status ${status}`;
}

function asFieldErrors(value: unknown): FieldError[] {
  if (!Array.isArray(value)) return [];
  const out: FieldError[] = [];
  for (const item of value) {
    if (item && typeof item === "object") {
      const record = item as Record<string, unknown>;
      out.push({
        loc: Array.isArray(record["loc"])
          ? (record["loc"] as readonly (string | number)[])
          : String(record["loc"] ?? ""),
        msg: typeof record["msg"] === "string" ? record["msg"] : String(record["msg"] ?? ""),
      });
    }
  }
  return out;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = `${BACKEND_ORIGIN}${path}`;
  const headers = new Headers(init.headers);
  if (init.body !== undefined && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  let response: Response;
  try {
    response = await fetch(url, { ...init, headers });
  } catch (cause) {
    throw new ApiError({
      status: 0,
      reason: `Cannot reach the studio backend at ${BACKEND_ORIGIN}`,
      data: cause,
    });
  }

  const text = await response.text();
  // FastAPI answers 204 and occasionally an empty body; both are valid JSON here.
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text) as unknown;
    } catch {
      body = text;
    }
  }

  if (!response.ok) {
    const record = (body ?? {}) as Record<string, unknown>;
    // FastAPI nests validation failures under `detail`.
    const detail = typeof record["detail"] === "object" ? (record["detail"] as object) : record;
    const detailRecord = (detail ?? {}) as Record<string, unknown>;
    throw new ApiError({
      status: response.status,
      reason: errorMessage(
        detailRecord["reason"] ?? record["reason"] ?? (typeof record["detail"] === "string" ? record["detail"] : undefined),
        response.status,
      ),
      errors: asFieldErrors(detailRecord["errors"] ?? record["errors"]),
      document: typeof detailRecord["document"] === "object"
        ? (detailRecord["document"] as ProjectDocument)
        : typeof record["document"] === "object"
          ? (record["document"] as ProjectDocument)
          : undefined,
      revision:
        typeof detailRecord["revision"] === "number"
          ? detailRecord["revision"]
          : typeof record["revision"] === "number"
            ? record["revision"]
            : undefined,
      data: body,
    });
  }

  return body as T;
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body ?? {}) });

export const api = {
  /** The resync entry point: document, revision, status and project root. */
  getState(): Promise<StateResponse> {
    return request<StateResponse>("/api/state");
  },

  getDocument(): Promise<DocumentResponse> {
    return request<DocumentResponse>("/api/document");
  },

  /**
   * Whole-document write with the revision the client last saw.
   * `200` → `{revision, document, problems}` · `409` → an `ApiError` carrying the
   * server document · `422` → an `ApiError` carrying per-field errors.
   */
  putDocument(body: PutDocumentRequest): Promise<PutDocumentResponse> {
    return request<PutDocumentResponse>("/api/document", {
      method: "PUT",
      ...json(body),
    });
  },

  getCatalog(): Promise<CatalogResponse> {
    return request<CatalogResponse>("/api/catalog");
  },

  getIndex(): Promise<AuthoringIndex> {
    return request<AuthoringIndex>("/api/index");
  },

  getDiagnostics(): Promise<DiagnosticsResponse> {
    return request<DiagnosticsResponse>("/api/diagnostics");
  },

  getPlan(refresh = false): Promise<PlanResponse> {
    return request<PlanResponse>(`/api/plan${refresh ? "?refresh=1" : ""}`);
  },

  getBlueprint(refresh = false): Promise<BlueprintResponse> {
    return request<BlueprintResponse>(`/api/blueprint${refresh ? "?refresh=1" : ""}`);
  },

  build(): Promise<BuildResponse> {
    return request<BuildResponse>("/api/build", { method: "POST", ...json({}) });
  },

  /** The generated code a ref produced, for "go to code" in the inspector. */
  getSource(ref: string): Promise<SourceResponse> {
    return request<SourceResponse>(`/api/source?ref=${encodeURIComponent(ref)}`);
  },

  suggestName(body: NameSuggestRequest): Promise<NameSuggestResponse> {
    return request<NameSuggestResponse>("/api/names/suggest", { method: "POST", ...json(body) });
  },

  async dataFiles(): Promise<DataFile[]> {
    // The backend answers with an envelope so the response can grow a field
    // without breaking clients; the array is what every caller wants.
    const body = await request<{ files: DataFile[] }>("/api/data/files");
    return body.files;
  },

  infer(body: InferRequest): Promise<InferResponse> {
    return request<InferResponse>("/api/infer", { method: "POST", ...json(body) });
  },

  /** Start a project from empty; the response is the ordinary document envelope. */
  createWorkspace(body: WorkspaceRequest): Promise<DocumentResponse> {
    return request<DocumentResponse>("/api/workspace", { method: "POST", ...json(body) });
  },
};

export type Api = typeof api;
