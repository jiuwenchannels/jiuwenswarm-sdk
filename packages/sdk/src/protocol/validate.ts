/**
 * Envelope parsing and validation.
 */
import type { InboundEnvelope } from "./types";

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

/** Thrown when a received message cannot be parsed as a valid envelope. */
export class ProtocolError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ProtocolError";
  }
}

/** Thrown when a WebSocket connection cannot be established. */
export class ConnectionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ConnectionError";
  }
}

// ---------------------------------------------------------------------------
// Parsing
// ---------------------------------------------------------------------------

/**
 * Parse a raw WebSocket message string into an inbound envelope.
 *
 * @throws {ProtocolError} If the message is not valid JSON, not an object,
 *   or does not have a string `"type"` field.
 */
export function parseEnvelope(raw: string): InboundEnvelope {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new ProtocolError(`Invalid JSON: ${raw.slice(0, 120)}`);
  }

  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    throw new ProtocolError("Envelope must be a JSON object");
  }

  const env = data as Record<string, unknown>;
  if (typeof env["type"] !== "string") {
    throw new ProtocolError('Envelope missing required string field "type"');
  }

  return env as unknown as InboundEnvelope;
}
