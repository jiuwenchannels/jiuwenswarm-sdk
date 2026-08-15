/**
 * Envelope type string constants.
 *
 * Using `MSG.TOKEN` instead of the raw string `"token"` prevents typos and
 * enables IDE auto-complete across the codebase.
 */
export const MSG = {
  // Inbound (server → client) — core
  ACK: "ack",
  SESSIONS: "sessions",
  SESSION_CREATED: "session_created",
  TOKEN: "token",
  DONE: "done",
  ERROR: "error",
  TOOL_CALL: "tool_call",

  // Inbound — stream events
  REASONING: "reasoning",
  STATUS: "status",
  TOOL_RESULT_SERVER: "tool_result_server",
  USAGE: "usage",
  CONFIRM_INTERRUPT: "confirm_interrupt",

  // Inbound — skills
  SKILLS_LIST: "skills_list",
  SKILL_TOGGLED: "skill_toggled",

  // Inbound — E2A protocol (newer server format)
  E2A_CHUNK: "e2a.chunk",
  E2A_COMPLETE: "e2a.complete",
  E2A_ERROR: "e2a.error",

  // Outbound (client → server) — core
  CONNECT: "connect",
  CREATE_SESSION: "create_session",
  CHAT: "chat",
  TOOL_RESULT: "tool_result",

  // Outbound — stream control
  INTERRUPT: "chat.interrupt",

  // Outbound — skills
  SKILLS: "skills",
  SKILL_TOGGLE: "skill_toggle",

  // Outbound — HITL
  HITL_ANSWER: "hitl_answer",
} as const;

export type MsgType = (typeof MSG)[keyof typeof MSG];
