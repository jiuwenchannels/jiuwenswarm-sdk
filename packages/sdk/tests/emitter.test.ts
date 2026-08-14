import { describe, it, expect, vi } from "vitest";
import { EventEmitter } from "../src/events/EventEmitter";

type TestEvents = { data: [string, number]; close: [] };

describe("EventEmitter", () => {
  it("on + emit: listener is called with correct arguments", () => {
    const emitter = new EventEmitter<TestEvents>();
    const listener = vi.fn();
    emitter.on("data", listener);
    emitter.emit("data", "hello", 42);
    expect(listener).toHaveBeenCalledOnce();
    expect(listener).toHaveBeenCalledWith("hello", 42);
  });

  it("multiple listeners on the same event are all called", () => {
    const emitter = new EventEmitter<TestEvents>();
    const l1 = vi.fn();
    const l2 = vi.fn();
    const l3 = vi.fn();
    emitter.on("data", l1);
    emitter.on("data", l2);
    emitter.on("data", l3);
    emitter.emit("data", "x", 1);
    expect(l1).toHaveBeenCalledOnce();
    expect(l2).toHaveBeenCalledOnce();
    expect(l3).toHaveBeenCalledOnce();
  });

  it("off removes a specific listener but leaves others", () => {
    const emitter = new EventEmitter<TestEvents>();
    const l1 = vi.fn();
    const l2 = vi.fn();
    emitter.on("data", l1);
    emitter.on("data", l2);
    emitter.off("data", l1);
    emitter.emit("data", "y", 2);
    expect(l1).not.toHaveBeenCalled();
    expect(l2).toHaveBeenCalledOnce();
  });

  it("off is a no-op if listener was not registered", () => {
    const emitter = new EventEmitter<TestEvents>();
    const registered = vi.fn();
    const unregistered = vi.fn();
    emitter.on("data", registered);
    expect(() => emitter.off("data", unregistered)).not.toThrow();
    emitter.emit("data", "z", 3);
    expect(registered).toHaveBeenCalledOnce();
    expect(unregistered).not.toHaveBeenCalled();
  });

  it("emit is a no-op if no listeners are registered for that event", () => {
    const emitter = new EventEmitter<TestEvents>();
    // Should not throw even when no listeners are registered.
    expect(() => emitter.emit("data", "a", 0)).not.toThrow();
    expect(() => emitter.emit("close")).not.toThrow();
  });

  it("removeAllListeners(event) removes all listeners for that event only", () => {
    const emitter = new EventEmitter<TestEvents>();
    const dataListener = vi.fn();
    const closeListener = vi.fn();
    emitter.on("data", dataListener);
    emitter.on("data", vi.fn());
    emitter.on("close", closeListener);
    emitter.removeAllListeners("data");
    emitter.emit("data", "b", 0);
    emitter.emit("close");
    expect(dataListener).not.toHaveBeenCalled();
    expect(closeListener).toHaveBeenCalledOnce();
  });

  it("removeAllListeners() with no argument removes all listeners for all events", () => {
    const emitter = new EventEmitter<TestEvents>();
    const dataListener = vi.fn();
    const closeListener = vi.fn();
    emitter.on("data", dataListener);
    emitter.on("close", closeListener);
    emitter.removeAllListeners();
    emitter.emit("data", "c", 0);
    emitter.emit("close");
    expect(dataListener).not.toHaveBeenCalled();
    expect(closeListener).not.toHaveBeenCalled();
  });

  it("a listener removed during its own invocation does not get called again (snapshot iteration)", () => {
    const emitter = new EventEmitter<TestEvents>();
    const callCount = { value: 0 };
    const selfRemoving = vi.fn(() => {
      callCount.value++;
      emitter.off("data", selfRemoving);
    });
    emitter.on("data", selfRemoving);
    emitter.emit("data", "d", 0);
    // Fire again — selfRemoving should not be called a second time.
    emitter.emit("data", "d", 0);
    expect(selfRemoving).toHaveBeenCalledOnce();
    expect(callCount.value).toBe(1);
  });

  it("listeners added during emission are not called in the same emit cycle", () => {
    const emitter = new EventEmitter<TestEvents>();
    const late = vi.fn();
    const first = vi.fn(() => {
      emitter.on("data", late);
    });
    emitter.on("data", first);
    emitter.emit("data", "e", 0);
    // late was registered inside first, so it must NOT have been called yet.
    expect(late).not.toHaveBeenCalled();
    // But a subsequent emit should call it.
    emitter.emit("data", "e", 1);
    expect(late).toHaveBeenCalledOnce();
  });

  it("chaining: on().on() returns this", () => {
    const emitter = new EventEmitter<TestEvents>();
    const l1 = vi.fn();
    const l2 = vi.fn();
    const result = emitter.on("data", l1).on("close", l2);
    expect(result).toBe(emitter);
    emitter.emit("data", "f", 0);
    emitter.emit("close");
    expect(l1).toHaveBeenCalledOnce();
    expect(l2).toHaveBeenCalledOnce();
  });

  it("close event (zero-arg) fires listeners with no arguments", () => {
    const emitter = new EventEmitter<TestEvents>();
    const listener = vi.fn();
    emitter.on("close", listener);
    emitter.emit("close");
    expect(listener).toHaveBeenCalledOnce();
    expect(listener).toHaveBeenCalledWith();
  });
});
