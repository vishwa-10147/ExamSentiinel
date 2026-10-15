import { ApiError } from "./apiClient";

/**
 * Reliable answer saving for an exam session.
 *
 * - Keeps only the latest answer per question (highest ``sequence_id``); the server applies
 *   last-write-wins on the same number, so replaying an older one is harmless.
 * - Persists unsent answers in localStorage, so a reload, a crash or a forced sign-in does not
 *   lose them; ``restore()`` hands them back on the next visit.
 * - Retries on its own with backoff after network errors, 5xx and 429 - not only when the browser
 *   reports "online", because flaky Wi-Fi and server hiccups never fire that event.
 * - Drops an answer only when the server refuses it for good (submitted, expired, not in exam).
 * - ``flushNow()`` sends everything before Submit, so the last edits are not lost.
 */

export interface PendingAnswer {
  question_id: string;
  response_data: unknown;
  sequence_id: number;
  is_flagged?: boolean;
  client_timestamp: string;
}

export type SyncStatus = "saved" | "saving" | "offline";

export interface SyncState {
  status: SyncStatus;
  pending: number;
  lastSavedAt: Date | null;
  /** Answers the server refused for good (e.g. the session already ended), newest last. */
  rejected: { question_id: string; reason: string }[];
}

type Send = (answer: PendingAnswer) => Promise<{ server_timestamp?: string } | void>;

const DEBOUNCE_MS = 600;
const RETRY_DELAYS_MS = [1000, 2000, 4000, 8000, 15000];

/** Network errors, rate limits and server-side failures are worth retrying; other 4xx are final. */
export function isRetryable(error: unknown): boolean {
  if (error instanceof ApiError) return error.status === 408 || error.status === 429 || error.status >= 500;
  return true; // fetch() failed: offline, DNS, connection reset, CORS on a proxy error page
}

export class AnswerSync {
  private pending = new Map<string, PendingAnswer>();
  private inFlight = new Set<string>();
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private attempt = 0;
  private flushing: Promise<void> | null = null;
  private state: SyncState = { status: "saved", pending: 0, lastSavedAt: null, rejected: [] };
  private listeners = new Set<(s: SyncState) => void>();
  private readonly storageKey: string;

  constructor(readonly sessionId: string, private readonly send: Send) {
    this.storageKey = `exam_answers_pending_${sessionId}`;
    this.load();
  }

  // ---- public API --------------------------------------------------------------------------

  /** Answers saved locally but not yet confirmed by the server (e.g. from before a reload). */
  restore(): PendingAnswer[] {
    return Array.from(this.pending.values());
  }

  /** Record an answer; it is sent after a short pause in typing. */
  enqueue(answer: Omit<PendingAnswer, "client_timestamp"> & { client_timestamp?: string }): void {
    const current = this.pending.get(answer.question_id);
    if (current && current.sequence_id > answer.sequence_id) return;
    this.pending.set(answer.question_id, { ...answer, client_timestamp: answer.client_timestamp || new Date().toISOString() });
    this.persist();
    this.update({ status: "saving" });
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => void this.flush(), DEBOUNCE_MS);
  }

  /** Send everything now (e.g. the browser came back online). */
  flush(): Promise<void> {
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.debounceTimer = null;
    if (!this.flushing) {
      this.flushing = this.sendAll().finally(() => {
        this.flushing = null;
      });
    }
    return this.flushing;
  }

  /**
   * Send everything and wait, retrying until ``timeoutMs`` passes. Returns how many answers are
   * still unsent (0 = everything is on the server).
   */
  async flushNow(timeoutMs = 10000): Promise<number> {
    const deadline = Date.now() + timeoutMs;
    for (let i = 0; this.pending.size > 0 && Date.now() < deadline; i++) {
      if (this.retryTimer) clearTimeout(this.retryTimer);
      this.retryTimer = null;
      await this.flush();
      if (this.pending.size > 0) await new Promise((r) => setTimeout(r, Math.min(500 * (i + 1), 2000)));
    }
    return this.pending.size;
  }

  subscribe(listener: (s: SyncState) => void): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => this.listeners.delete(listener);
  }

  dispose(): void {
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    if (this.retryTimer) clearTimeout(this.retryTimer);
    this.listeners.clear();
  }

  // ---- internals ---------------------------------------------------------------------------

  private async sendAll(): Promise<void> {
    if (this.pending.size === 0) {
      this.update({ status: "saved" });
      return;
    }
    this.update({ status: "saving" });
    let retry = false;
    for (const answer of Array.from(this.pending.values())) {
      if (this.inFlight.has(answer.question_id)) continue;
      this.inFlight.add(answer.question_id);
      try {
        const result = await this.send(answer);
        // A newer edit may have arrived while this one was in flight: keep that one.
        if (this.pending.get(answer.question_id)?.sequence_id === answer.sequence_id) {
          this.pending.delete(answer.question_id);
        }
        const at = result && result.server_timestamp ? new Date(result.server_timestamp) : new Date();
        this.update({ lastSavedAt: at });
      } catch (error) {
        if (isRetryable(error)) {
          retry = true;
          break; // the connection is probably down: stop and retry everything later
        }
        this.pending.delete(answer.question_id);
        this.update({
          rejected: [...this.state.rejected, { question_id: answer.question_id, reason: (error as Error).message }],
        });
      } finally {
        this.inFlight.delete(answer.question_id);
      }
    }
    this.persist();
    if (retry) {
      this.update({ status: "offline" });
      this.scheduleRetry();
    } else {
      this.attempt = 0;
      this.update({ status: this.pending.size ? "saving" : "saved" });
      if (this.pending.size) this.scheduleRetry(); // edits that arrived during the flush
    }
  }

  private scheduleRetry(): void {
    if (this.retryTimer) return;
    const delay = RETRY_DELAYS_MS[Math.min(this.attempt, RETRY_DELAYS_MS.length - 1)];
    this.attempt += 1;
    this.retryTimer = setTimeout(() => {
      this.retryTimer = null;
      void this.flush();
    }, delay);
  }

  private update(patch: Partial<SyncState>): void {
    this.state = { ...this.state, ...patch, pending: this.pending.size };
    this.listeners.forEach((l) => l(this.state));
  }

  private load(): void {
    try {
      const saved = JSON.parse(window.localStorage.getItem(this.storageKey) || "[]") as PendingAnswer[];
      saved.forEach((a) => this.pending.set(a.question_id, a));
      // Answers queued by the previous version of the exam page.
      const legacyKey = `offline_answers_${this.sessionId}`;
      const legacy = JSON.parse(window.localStorage.getItem(legacyKey) || "[]") as PendingAnswer[];
      legacy.forEach((a) => {
        const current = this.pending.get(a.question_id);
        if (!current || current.sequence_id <= a.sequence_id) {
          this.pending.set(a.question_id, { ...a, client_timestamp: a.client_timestamp || new Date().toISOString() });
        }
      });
      window.localStorage.removeItem(legacyKey);
    } catch {
      // Storage unavailable or corrupt: start empty (answers still go to the server directly).
    }
    this.state = { ...this.state, pending: this.pending.size };
  }

  private persist(): void {
    try {
      if (this.pending.size) window.localStorage.setItem(this.storageKey, JSON.stringify(Array.from(this.pending.values())));
      else window.localStorage.removeItem(this.storageKey);
    } catch {
      // Storage full or blocked: the in-memory queue still retries.
    }
  }
}
