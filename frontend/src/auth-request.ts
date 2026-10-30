const AUTH_REQUEST_TIMEOUT_MS = 90_000;

/** Bound read-only SDK waits; a late snapshot must still be guarded by its caller. */
export function awaitAuthResult<T>(result: Promise<T>, timeoutMs: number): Promise<T> {
  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => reject(new DOMException("Authentication timed out.", "TimeoutError")), timeoutMs);
    result.then(
      (value) => { clearTimeout(timeoutId); resolve(value); },
      (error) => { clearTimeout(timeoutId); reject(error); },
    );
  });
}

/** Abort the transport and buffer the body before the auth SDK can save a session. */
export async function authFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const externalSignal = init?.signal
    ?? (typeof Request !== "undefined" && input instanceof Request ? input.signal : undefined);
  const onExternalAbort = () => controller.abort(externalSignal?.reason);
  const timeoutId = setTimeout(() => {
    controller.abort(new DOMException("Authentication timed out.", "TimeoutError"));
  }, AUTH_REQUEST_TIMEOUT_MS);
  if (externalSignal?.aborted) onExternalAbort();
  else externalSignal?.addEventListener("abort", onExternalAbort, { once: true });

  let onAbort: () => void = () => undefined;
  const aborted = new Promise<never>((_resolve, reject) => {
    onAbort = () => reject(controller.signal.reason ?? new DOMException("Aborted.", "AbortError"));
    if (controller.signal.aborted) onAbort();
    else controller.signal.addEventListener("abort", onAbort, { once: true });
  });
  try {
    if (controller.signal.aborted) return await aborted;
    const response = await Promise.race([fetch(input, { ...init, signal: controller.signal }), aborted]);
    const body = await Promise.race([response.text(), aborted]);
    // Response.json() inside the SDK now reads a complete body. A stalled or late
    // network response cannot outlive this deadline and silently sign the user in.
    return new Response([101, 204, 205, 304].includes(response.status) ? null : body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  } finally {
    clearTimeout(timeoutId);
    controller.signal.removeEventListener("abort", onAbort);
    externalSignal?.removeEventListener("abort", onExternalAbort);
  }
}
