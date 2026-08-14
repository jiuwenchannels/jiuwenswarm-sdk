import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ReconnectScheduler } from "../src/client/reconnect";

describe("ReconnectScheduler", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ---------------------------------------------------------------------------
  // Default delay sequence
  // ---------------------------------------------------------------------------

  it("default delay sequence: attempt 0 → 1000 ms", () => {
    const s = new ReconnectScheduler();
    expect(s.delayFor(0)).toBe(1000);
  });

  it("default delay sequence: attempt 1 → 2000 ms", () => {
    const s = new ReconnectScheduler();
    expect(s.delayFor(1)).toBe(2000);
  });

  it("default delay sequence: attempt 2 → 5000 ms", () => {
    const s = new ReconnectScheduler();
    expect(s.delayFor(2)).toBe(5000);
  });

  it("default delay sequence: attempt 3 → 10000 ms", () => {
    const s = new ReconnectScheduler();
    expect(s.delayFor(3)).toBe(10000);
  });

  it("default delay sequence: attempt 4 → 30000 ms", () => {
    const s = new ReconnectScheduler();
    expect(s.delayFor(4)).toBe(30000);
  });

  it("default delay sequence: attempt 5 → 30000 ms (capped)", () => {
    const s = new ReconnectScheduler();
    expect(s.delayFor(5)).toBe(30000);
  });

  it("default delay sequence: large attempt index is capped at 30000 ms", () => {
    const s = new ReconnectScheduler();
    expect(s.delayFor(100)).toBe(30000);
  });

  // ---------------------------------------------------------------------------
  // Custom config: exponential formula with cap
  // ---------------------------------------------------------------------------

  it("custom config: exponential formula with no cap", () => {
    const s = new ReconnectScheduler({ initialDelayMs: 500, factor: 3, maxDelayMs: 999999 });
    // attempt 0: 500 * 3^0 = 500
    expect(s.delayFor(0)).toBe(500);
    // attempt 1: 500 * 3^1 = 1500
    expect(s.delayFor(1)).toBe(1500);
    // attempt 2: 500 * 3^2 = 4500
    expect(s.delayFor(2)).toBe(4500);
  });

  it("custom config: delay is capped at maxDelayMs", () => {
    const s = new ReconnectScheduler({ initialDelayMs: 1000, factor: 2, maxDelayMs: 3000 });
    // attempt 0: 1000 * 2^0 = 1000  < 3000 → 1000
    expect(s.delayFor(0)).toBe(1000);
    // attempt 1: 1000 * 2^1 = 2000  < 3000 → 2000
    expect(s.delayFor(1)).toBe(2000);
    // attempt 2: 1000 * 2^2 = 4000  > 3000 → 3000
    expect(s.delayFor(2)).toBe(3000);
    // attempt 3: capped
    expect(s.delayFor(3)).toBe(3000);
  });

  // ---------------------------------------------------------------------------
  // schedule() fires callback after correct delay
  // ---------------------------------------------------------------------------

  it("schedule() calls the callback after the correct delay", () => {
    const s = new ReconnectScheduler();
    const cb = vi.fn();
    s.schedule(cb);
    expect(cb).not.toHaveBeenCalled();
    vi.advanceTimersByTime(999);
    expect(cb).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1); // total 1000 ms
    expect(cb).toHaveBeenCalledOnce();
  });

  it("schedule() increments the attempt counter", () => {
    const s = new ReconnectScheduler();
    expect(s.attempt).toBe(0);
    s.schedule(vi.fn());
    expect(s.attempt).toBe(1);
    vi.advanceTimersByTime(30000);
    s.schedule(vi.fn());
    expect(s.attempt).toBe(2);
  });

  it("schedule() uses the delay corresponding to the current attempt before incrementing", () => {
    const s = new ReconnectScheduler();
    // First schedule: attempt 0 → delay 1000 ms
    const cb1 = vi.fn();
    s.schedule(cb1);
    vi.advanceTimersByTime(1000);
    expect(cb1).toHaveBeenCalledOnce();

    // Second schedule: attempt 1 → delay 2000 ms
    const cb2 = vi.fn();
    s.schedule(cb2);
    vi.advanceTimersByTime(1999);
    expect(cb2).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(cb2).toHaveBeenCalledOnce();
  });

  it("schedule() returns false once maxAttempts is reached", () => {
    const s = new ReconnectScheduler({ maxAttempts: 2 });
    expect(s.schedule(vi.fn())).toBe(true);
    vi.advanceTimersByTime(30000);
    expect(s.schedule(vi.fn())).toBe(true);
    vi.advanceTimersByTime(30000);
    // Now attempt === maxAttempts (2)
    expect(s.schedule(vi.fn())).toBe(false);
  });

  it("schedule() returns true when scheduling is allowed", () => {
    const s = new ReconnectScheduler({ maxAttempts: 5 });
    expect(s.schedule(vi.fn())).toBe(true);
  });

  // ---------------------------------------------------------------------------
  // cancel()
  // ---------------------------------------------------------------------------

  it("cancel() prevents the scheduled callback from firing", () => {
    const s = new ReconnectScheduler();
    const cb = vi.fn();
    s.schedule(cb);
    s.cancel();
    vi.advanceTimersByTime(10000);
    expect(cb).not.toHaveBeenCalled();
  });

  it("cancel() makes subsequent schedule() calls return false", () => {
    const s = new ReconnectScheduler();
    s.cancel();
    expect(s.schedule(vi.fn())).toBe(false);
  });

  // ---------------------------------------------------------------------------
  // reset()
  // ---------------------------------------------------------------------------

  it("reset() resets attempt to 0 and re-enables scheduling", () => {
    const s = new ReconnectScheduler({ maxAttempts: 1 });
    s.schedule(vi.fn());
    vi.advanceTimersByTime(30000);
    // maxAttempts reached
    expect(s.schedule(vi.fn())).toBe(false);
    s.reset();
    expect(s.attempt).toBe(0);
    expect(s.schedule(vi.fn())).toBe(true);
  });

  it("reset() after cancel() allows scheduling again", () => {
    const s = new ReconnectScheduler();
    s.cancel();
    expect(s.schedule(vi.fn())).toBe(false);
    s.reset();
    const cb = vi.fn();
    expect(s.schedule(cb)).toBe(true);
    vi.advanceTimersByTime(1000);
    expect(cb).toHaveBeenCalledOnce();
  });
});
