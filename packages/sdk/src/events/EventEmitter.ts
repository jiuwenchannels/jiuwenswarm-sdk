/**
 * Typed EventEmitter with no Node.js dependency.
 *
 * Works identically in browsers, Node.js, and React Native.
 *
 * Usage:
 * ```typescript
 * type MyEvents = {
 *   data: [string, number];
 *   close: [];
 * };
 * const emitter = new EventEmitter<MyEvents>();
 * emitter.on("data", (msg, count) => console.log(msg, count));
 * emitter.emit("data", "hello", 1);
 * ```
 */
export class EventEmitter<
  Events extends Record<string, unknown[]> = Record<string, unknown[]>,
> {
  private readonly _listeners: Partial<{
    [K in keyof Events]: Array<(...args: Events[K]) => void>;
  }> = {};

  /**
   * Register a listener for the given event.
   * Returns `this` for chaining.
   */
  on<K extends keyof Events>(
    event: K,
    listener: (...args: Events[K]) => void,
  ): this {
    if (!this._listeners[event]) {
      (this._listeners as Record<keyof Events, unknown[]>)[event] = [];
    }
    this._listeners[event]!.push(listener);
    return this;
  }

  /**
   * Remove a previously registered listener.
   * No-op if the listener was not registered.
   * Returns `this` for chaining.
   */
  off<K extends keyof Events>(
    event: K,
    listener: (...args: Events[K]) => void,
  ): this {
    const list = this._listeners[event];
    if (!list) return this;
    this._listeners[event] = list.filter(
      (l) => l !== listener,
    ) as typeof list;
    return this;
  }

  /**
   * Emit an event, calling all registered listeners synchronously.
   */
  emit<K extends keyof Events>(event: K, ...args: Events[K]): void {
    const list = this._listeners[event];
    if (!list) return;
    // Iterate over a snapshot so that listeners removed during emission
    // do not affect the current iteration.
    for (const listener of list.slice()) {
      listener(...args);
    }
  }

  /**
   * Remove all listeners for a given event, or all events if omitted.
   */
  removeAllListeners(event?: keyof Events): this {
    if (event === undefined) {
      for (const key of Object.keys(this._listeners)) {
        delete (this._listeners as Record<string, unknown>)[key];
      }
    } else {
      delete this._listeners[event];
    }
    return this;
  }
}
