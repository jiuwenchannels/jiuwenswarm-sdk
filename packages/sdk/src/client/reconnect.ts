/**
 * Exponential back-off reconnect scheduler.
 *
 * Default delay sequence (ms): 1 000 → 2 000 → 5 000 → 10 000 → 30 000
 * (capped at the last value for all subsequent attempts).
 *
 * The sequence can be customised via {@link ReconnectConfig}.
 */
import type { ReconnectConfig } from "../protocol/types";

/** Default back-off delays in milliseconds. */
const DEFAULT_DELAYS_MS = [1_000, 2_000, 5_000, 10_000, 30_000];

export class ReconnectScheduler {
  private _attempt = 0;
  private _timer: ReturnType<typeof setTimeout> | null = null;
  private _cancelled = false;

  private readonly _maxAttempts: number;
  private readonly _initialDelayMs: number;
  private readonly _maxDelayMs: number;
  private readonly _factor: number;
  private readonly _useDefaults: boolean;

  constructor(config: ReconnectConfig = {}) {
    this._maxAttempts = config.maxAttempts ?? Infinity;
    this._initialDelayMs = config.initialDelayMs ?? DEFAULT_DELAYS_MS[0];
    this._maxDelayMs = config.maxDelayMs ?? DEFAULT_DELAYS_MS[DEFAULT_DELAYS_MS.length - 1];
    this._factor = config.factor ?? 2;
    // Use the hardcoded default table only when no custom values were supplied
    this._useDefaults =
      config.initialDelayMs === undefined &&
      config.maxDelayMs === undefined &&
      config.factor === undefined;
  }

  /** Number of reconnect attempts made so far. */
  get attempt(): number {
    return this._attempt;
  }

  /** Compute the delay for a given attempt index (0-based), in ms. */
  delayFor(attempt: number): number {
    if (this._useDefaults) {
      return DEFAULT_DELAYS_MS[Math.min(attempt, DEFAULT_DELAYS_MS.length - 1)];
    }
    const raw = this._initialDelayMs * Math.pow(this._factor, attempt);
    return Math.min(raw, this._maxDelayMs);
  }

  /**
   * Schedule the next reconnect callback.
   *
   * @returns `true` if the callback was scheduled, `false` if the maximum
   *   number of attempts has been reached or the scheduler was cancelled.
   */
  schedule(callback: () => void): boolean {
    if (this._cancelled) return false;
    if (this._attempt >= this._maxAttempts) return false;

    const delay = this.delayFor(this._attempt);
    this._attempt++;

    this._timer = setTimeout(() => {
      if (!this._cancelled) callback();
    }, delay);

    return true;
  }

  /**
   * Cancel any pending reconnect and prevent future scheduling.
   * Call {@link reset} to re-enable scheduling afterwards.
   */
  cancel(): void {
    this._cancelled = true;
    if (this._timer !== null) {
      clearTimeout(this._timer);
      this._timer = null;
    }
  }

  /** Reset the scheduler so it can be reused (e.g. after a successful connect). */
  reset(): void {
    this.cancel();
    this._attempt = 0;
    this._cancelled = false;
  }
}
