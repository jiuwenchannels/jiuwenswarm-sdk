/**
 * Envelope type string constants.
 *
 * Using `MSG.TOKEN` instead of the raw string `"token"` prevents typos and
 * enables IDE auto-complete across the codebase.
 */
export const MSG = {
  // Inbound (server → client)
  ACK: "ack",
  SESSIONS: "sessions",
  SESSION_CREATED: "session_created",
  TOKEN: "token",
  DONE: "done",
  ERROR: "error",
  TOOL_CALL: "tool_call",

  // Outbound (client → server)
  CONNECT: "connect",
  CREATE_SESSION: "create_session",
  CHAT: "chat",
  TOOL_RESULT: "tool_result",
} as const;

export type MsgType = (typeof MSG)[keyof typeof MSG];
