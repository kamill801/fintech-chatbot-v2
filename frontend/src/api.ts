import type {
  Correction,
  Profile,
  Settings,
  SharePayload,
  Summary,
  Transaction,
  TransactionDetail,
  TransactionDraft,
  TransactionResult,
  SpendingReflection,
  PlanDraft,
  PlanRevisionPreview,
  SpendingPlanState,
} from "./types";
import { getAccessToken } from "./auth-client";
import { createClientId } from "./utils";

interface Envelope<T> {
  data: T;
  meta: { correlation_id: string };
}

interface ApiFailure {
  error?: { code?: string; message?: string };
}

interface RequestOptions extends RequestInit {
  idempotencyKey?: string;
}

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
    public readonly correlationId: string | null = null,
  ) {
    super(message);
  }
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL?.trim() ?? "").replace(/\/+$/, "");
const REQUEST_TIMEOUT_MS = 90_000;

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

function abortReason(signal: AbortSignal): unknown {
  return signal.reason ?? new DOMException("The request was aborted.", "AbortError");
}

function readTextWithAbort(response: Response, signal: AbortSignal): Promise<string> {
  if (signal.aborted) return Promise.reject(abortReason(signal));

  return new Promise((resolve, reject) => {
    let settled = false;
    const onAbort = () => {
      if (settled) return;
      settled = true;
      signal.removeEventListener("abort", onAbort);
      reject(abortReason(signal));
    };

    signal.addEventListener("abort", onAbort, { once: true });
    response.text().then(
      (text) => {
        if (settled) return;
        settled = true;
        signal.removeEventListener("abort", onAbort);
        resolve(text);
      },
      (error) => {
        if (settled) return;
        settled = true;
        signal.removeEventListener("abort", onAbort);
        reject(error);
      },
    );
  });
}

function createRequestSignal(externalSignal?: AbortSignal): {
  signal: AbortSignal;
  cleanup: () => void;
  didTimeout: () => boolean;
  didCancel: () => boolean;
} {
  const controller = new AbortController();
  let timedOut = false;
  let cancelled = false;
  const timeoutId: ReturnType<typeof setTimeout> = setTimeout(() => {
    timedOut = true;
    controller.abort(new DOMException("Request timed out.", "TimeoutError"));
  }, REQUEST_TIMEOUT_MS);

  const onExternalAbort = () => {
    if (controller.signal.aborted) return;
    cancelled = true;
    controller.abort(abortReason(externalSignal as AbortSignal));
  };

  if (externalSignal?.aborted) {
    onExternalAbort();
  } else {
    externalSignal?.addEventListener("abort", onExternalAbort, { once: true });
  }

  return {
    signal: controller.signal,
    cleanup: () => {
      clearTimeout(timeoutId);
      externalSignal?.removeEventListener("abort", onExternalAbort);
    },
    didTimeout: () => timedOut,
    didCancel: () => cancelled,
  };
}

function connectionError(error: unknown, requestSignal: ReturnType<typeof createRequestSignal>): ApiError {
  if (requestSignal.didTimeout()) {
    return new ApiError("request_timeout", "요청 시간이 오래 걸려요. 잠시 후 다시 시도해 주세요.", 0);
  }
  if (requestSignal.didCancel()) {
    return new ApiError("request_cancelled", "요청이 취소됐어요.", 0);
  }
  if (error instanceof ApiError) return error;
  return new ApiError("offline", "네트워크에 연결할 수 없어요.", 0);
}

async function parseResponse<T>(response: Response, signal: AbortSignal): Promise<(Envelope<T> & ApiFailure) | null> {
  const text = await readTextWithAbort(response, signal);
  if (!text.trim()) return null;
  try {
    return JSON.parse(text) as Envelope<T> & ApiFailure;
  } catch {
    return null;
  }
}

async function request<T>(path: string, init: RequestOptions = {}): Promise<T> {
  const { idempotencyKey, signal: externalSignal, ...requestInit } = init;
  const headers = new Headers(requestInit.headers);
  headers.set("Accept", "application/json");
  const accessToken = await getAccessToken();
  if (!accessToken) {
    throw new ApiError("unauthorized", "로그인이 필요해요.", 401);
  }
  headers.set("Authorization", `Bearer ${accessToken}`);
  if (requestInit.body) headers.set("Content-Type", "application/json");
  if (requestInit.method && requestInit.method !== "GET") {
    headers.set("Idempotency-Key", idempotencyKey ?? createClientId());
  }

  const requestSignal = createRequestSignal(externalSignal ?? undefined);
  try {
    const response = await fetch(apiUrl(path), { ...requestInit, headers, signal: requestSignal.signal });
    if (response.status === 204) return undefined as T;

    const payload = await parseResponse<T>(response, requestSignal.signal);
    if (!response.ok) {
      throw new ApiError(
        payload?.error?.code ?? "request_failed",
        payload?.error?.message ?? "요청을 처리하지 못했어요.",
        response.status,
        payload?.meta?.correlation_id ?? response.headers.get("X-Correlation-Id"),
      );
    }
    if (!payload?.data) {
      throw new ApiError("invalid_response", "서버 응답을 읽지 못했어요.", response.status, response.headers.get("X-Correlation-Id"));
    }
    return payload.data;
  } catch (error) {
    throw connectionError(error, requestSignal);
  } finally {
    requestSignal.cleanup();
  }
}

export const ledgerApi = {
  async profile(): Promise<Profile | null> {
    return (await request<{ profile: Profile | null }>("/api/v1/me/profile")).profile;
  },
  async saveProfile(profile: Profile): Promise<Profile> {
    const data = await request<{ profile: Profile }>("/api/v1/me/profile", {
      method: "PUT",
      body: JSON.stringify(profile),
    });
    return data.profile;
  },
  async settings(): Promise<Settings> {
    return (await request<{ settings: Settings }>("/api/v1/me/settings")).settings;
  },
  async saveSettings(patch: Partial<Settings>): Promise<Settings> {
    const data = await request<{ settings: Settings }>("/api/v1/me/settings", {
      method: "PUT",
      body: JSON.stringify(patch),
    });
    return data.settings;
  },
  async transactions(): Promise<Transaction[]> {
    return (await request<{ transactions: Transaction[] }>("/api/v1/me/transactions"))
      .transactions;
  },
  async plan(): Promise<SpendingPlanState | null> {
    const data = await request<{ plan: null } | SpendingPlanState>("/api/v1/me/plan");
    return data.plan ? (data as SpendingPlanState) : null;
  },
  async previewPlan(draft: PlanDraft): Promise<SpendingPlanState> {
    return request<SpendingPlanState>("/api/v1/me/plan/preview", {
      method: "POST",
      body: JSON.stringify(draft),
    });
  },
  async activatePlan(draft: PlanDraft, previewToken?: string): Promise<SpendingPlanState> {
    return request<SpendingPlanState>("/api/v1/me/plan", {
      method: "PUT",
      body: JSON.stringify({ ...draft, confirmed: true, preview_token: previewToken }),
    });
  },
  async previewPlanRevision(
    draft: PlanDraft,
    baseVersion: number,
    reason: string,
  ): Promise<{ revision_preview: PlanRevisionPreview; plan: SpendingPlanState["plan"]; progress: SpendingPlanState["progress"]; preview_token?: string }> {
    return request("/api/v1/me/plan/revision-preview", {
      method: "POST",
      body: JSON.stringify({ ...draft, base_version: baseVersion, reason }),
    });
  },
  async applyPlanRevision(
    draft: PlanDraft,
    baseVersion: number,
    reason: string,
    previewToken?: string,
  ): Promise<SpendingPlanState> {
    return request<SpendingPlanState>("/api/v1/me/plan/revisions", {
      method: "POST",
      body: JSON.stringify({ ...draft, base_version: baseVersion, reason, apply: true, preview_token: previewToken }),
    });
  },
  async checkInPlan(decision: "maintain" | "adjust", note: string): Promise<SpendingPlanState> {
    return request<SpendingPlanState>("/api/v1/me/plan/check-ins", {
      method: "POST",
      body: JSON.stringify({ decision, note }),
    });
  },
  async matchPlannedExpense(plannedExpenseId: string, transactionId: string): Promise<SpendingPlanState> {
    return request<SpendingPlanState>(`/api/v1/me/plan/planned-expenses/${plannedExpenseId}/match`, {
      method: "POST",
      body: JSON.stringify({ transaction_id: transactionId }),
    });
  },
  async transaction(id: string): Promise<TransactionDetail> {
    return request<TransactionDetail>(`/api/v1/me/transactions/${id}`);
  },
  async createTransaction(draft: TransactionDraft, idempotencyKey?: string): Promise<TransactionResult> {
    return request<TransactionResult>("/api/v1/me/transactions", {
      method: "POST",
      body: JSON.stringify(draft),
      idempotencyKey,
    });
  },
  async updateTransaction(id: string, draft: Partial<TransactionDraft>): Promise<TransactionResult> {
    return request<TransactionResult>(`/api/v1/me/transactions/${id}`, {
      method: "PUT",
      body: JSON.stringify(draft),
    });
  },
  async deleteTransaction(id: string): Promise<void> {
    await request(`/api/v1/me/transactions/${id}`, { method: "DELETE" });
  },
  async answerReason(id: string, reason: string): Promise<TransactionResult> {
    return request<TransactionResult>(`/api/v1/me/transactions/${id}/reason`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },
  async reflectTransaction(
    id: string,
    reflection: SpendingReflection,
    reflection_note: string,
  ): Promise<Transaction> {
    const data = await request<{ transaction: Transaction }>(
      `/api/v1/me/transactions/${id}/reflection`,
      {
        method: "PUT",
        body: JSON.stringify({ reflection, reflection_note }),
      },
    );
    return data.transaction;
  },
  async correctJudgment(
    id: string,
    corrected_label: Correction["corrected_label"],
    correction_reason: string,
  ): Promise<Correction> {
    const data = await request<{ correction: Correction }>(
      `/api/v1/me/judgments/${id}/corrections`,
      {
        method: "POST",
        body: JSON.stringify({ corrected_label, correction_reason }),
      },
    );
    return data.correction;
  },
  async summary(): Promise<Summary> {
    return (await request<{ summary: Summary }>("/api/v1/me/summary")).summary;
  },
  async shareView(id: string): Promise<void> {
    await request(`/api/v1/me/judgments/${id}/share-view`, { method: "POST" });
  },
  async share(id: string): Promise<SharePayload> {
    return (
      await request<{ share: SharePayload }>(`/api/v1/me/judgments/${id}/share`, {
        method: "POST",
      })
    ).share;
  },
  async shareSuccess(id: string): Promise<void> {
    await request(`/api/v1/me/judgments/${id}/share-success`, { method: "POST" });
  },
  async deleteData(): Promise<void> {
    await request("/api/v1/me/data", { method: "DELETE" });
  },
};
