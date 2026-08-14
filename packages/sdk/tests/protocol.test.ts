import { describe, it, expect } from "vitest";
import {
  parseEnvelope,
  ProtocolError,
  ConnectionError,
} from "../src/protocol/validate";
import { MSG } from "../src/protocol/constants";

describe("parseEnvelope", () => {
  it("returns a typed object for valid JSON with a string type field", () => {
    const raw = JSON.stringify({ type: "ack", protocol_version: "1" });
    const result = parseEnvelope(raw);
    expect(result).toEqual({ type: "ack", protocol_version: "1" });
    expect(result.type).toBe("ack");
  });

  it("preserves all extra fields on the returned object", () => {
    const raw = JSON.stringify({ type: "token", text: "hello", extra: 42 });
    const result = parseEnvelope(raw) as Record<string, unknown>;
    expect(result.type).toBe("token");
    expect(result.text).toBe("hello");
    expect(result.extra).toBe(42);
  });

  it("throws ProtocolError for a non-JSON string", () => {
    expect(() => parseEnvelope("not json at all")).toThrow(ProtocolError);
    expect(() => parseEnvelope("not json at all")).toThrow(/Invalid JSON/);
  });

  it("throws ProtocolError for a JSON array", () => {
    expect(() => parseEnvelope("[1, 2, 3]")).toThrow(ProtocolError);
    expect(() => parseEnvelope("[1, 2, 3]")).toThrow(/Envelope must be a JSON object/);
  });

  it("throws ProtocolError for JSON null", () => {
    expect(() => parseEnvelope("null")).toThrow(ProtocolError);
    expect(() => parseEnvelope("null")).toThrow(/Envelope must be a JSON object/);
  });

  it("throws ProtocolError for a JSON number", () => {
    expect(() => parseEnvelope("42")).toThrow(ProtocolError);
    expect(() => parseEnvelope("42")).toThrow(/Envelope must be a JSON object/);
  });

  it("throws ProtocolError for an object without a type field", () => {
    const raw = JSON.stringify({ message: "hello" });
    expect(() => parseEnvelope(raw)).toThrow(ProtocolError);
    expect(() => parseEnvelope(raw)).toThrow(/missing required string field "type"/);
  });

  it("throws ProtocolError for an object with a non-string type field", () => {
    const raw = JSON.stringify({ type: 99 });
    expect(() => parseEnvelope(raw)).toThrow(ProtocolError);
    expect(() => parseEnvelope(raw)).toThrow(/missing required string field "type"/);
  });

  it("throws ProtocolError for an object with type: null", () => {
    const raw = JSON.stringify({ type: null });
    expect(() => parseEnvelope(raw)).toThrow(ProtocolError);
  });

  it("throws ProtocolError for an object with type: false", () => {
    const raw = JSON.stringify({ type: false });
    expect(() => parseEnvelope(raw)).toThrow(ProtocolError);
  });
});

describe("ProtocolError", () => {
  it("has name ProtocolError and is an instance of Error", () => {
    const err = new ProtocolError("bad envelope");
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(ProtocolError);
    expect(err.name).toBe("ProtocolError");
    expect(err.message).toBe("bad envelope");
  });
});

describe("ConnectionError", () => {
  it("has name ConnectionError and is an instance of Error", () => {
    const err = new ConnectionError("cannot connect");
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(ConnectionError);
    expect(err.name).toBe("ConnectionError");
    expect(err.message).toBe("cannot connect");
  });
});

describe("MSG constants", () => {
  it("all constants are strings", () => {
    for (const value of Object.values(MSG)) {
      expect(typeof value).toBe("string");
    }
  });

  it("includes ACK", () => {
    expect(typeof MSG.ACK).toBe("string");
    expect(MSG.ACK).toBeTruthy();
  });

  it("includes TOKEN", () => {
    expect(typeof MSG.TOKEN).toBe("string");
    expect(MSG.TOKEN).toBeTruthy();
  });

  it("includes DONE", () => {
    expect(typeof MSG.DONE).toBe("string");
    expect(MSG.DONE).toBeTruthy();
  });

  it("includes ERROR", () => {
    expect(typeof MSG.ERROR).toBe("string");
    expect(MSG.ERROR).toBeTruthy();
  });

  it("includes TOOL_CALL", () => {
    expect(typeof MSG.TOOL_CALL).toBe("string");
    expect(MSG.TOOL_CALL).toBeTruthy();
  });

  it("includes CONNECT", () => {
    expect(typeof MSG.CONNECT).toBe("string");
    expect(MSG.CONNECT).toBeTruthy();
  });

  it("includes SESSIONS", () => {
    expect(typeof MSG.SESSIONS).toBe("string");
    expect(MSG.SESSIONS).toBeTruthy();
  });

  it("includes SESSION_CREATED", () => {
    expect(typeof MSG.SESSION_CREATED).toBe("string");
    expect(MSG.SESSION_CREATED).toBeTruthy();
  });

  it("includes CREATE_SESSION", () => {
    expect(typeof MSG.CREATE_SESSION).toBe("string");
    expect(MSG.CREATE_SESSION).toBeTruthy();
  });

  it("includes CHAT", () => {
    expect(typeof MSG.CHAT).toBe("string");
    expect(MSG.CHAT).toBeTruthy();
  });

  it("includes TOOL_RESULT", () => {
    expect(typeof MSG.TOOL_RESULT).toBe("string");
    expect(MSG.TOOL_RESULT).toBeTruthy();
  });

  it("all expected keys are present", () => {
    const keys = Object.keys(MSG);
    expect(keys).toContain("ACK");
    expect(keys).toContain("TOKEN");
    expect(keys).toContain("DONE");
    expect(keys).toContain("ERROR");
    expect(keys).toContain("TOOL_CALL");
    expect(keys).toContain("CONNECT");
    expect(keys).toContain("SESSIONS");
    expect(keys).toContain("SESSION_CREATED");
    expect(keys).toContain("CREATE_SESSION");
    expect(keys).toContain("CHAT");
    expect(keys).toContain("TOOL_RESULT");
  });
});
