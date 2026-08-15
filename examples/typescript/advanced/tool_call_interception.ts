/**
 * 06_tool_call_interception.ts — intercept tool calls from the server and
 * execute them on the client side (e.g. browser Geolocation, clipboard).
 *
 * By default the client rejects any `tool_call` envelope from the server
 * with `{error: "not supported"}`.  Supply `onToolCall` to handle them.
 *
 * Requires: npm install @jiuwenswarm/sdk
 * Gateway:  ws://localhost:19000/v1/ws  (start with `jiuwenswarm serve`)
 */

import { JiuwenSwarmClient, ToolCallEnvelope } from "@jiuwenswarm/sdk";

const client = new JiuwenSwarmClient({
  url: "ws://localhost:19000/v1/ws",

  // Return a string result or throw to send an error back to the server.
  onToolCall: async (call: ToolCallEnvelope): Promise<string> => {
    if (call.name === "get_user_location") {
      // Obtain from the browser's Geolocation API
      const pos = await new Promise<GeolocationPosition>((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject)
      );
      return JSON.stringify({
        lat: pos.coords.latitude,
        lng: pos.coords.longitude,
      });
    }

    if (call.name === "read_clipboard") {
      return await navigator.clipboard.readText();
    }

    throw new Error(`Tool not implemented: ${call.name}`);
  },
});

await client.connect();
const session = await client.sessions.create("Tool demo");
client.sessions.setActive(session.id);
await client.send("What city am I in right now?");
