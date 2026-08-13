/**
 * 03_streaming_react.tsx — React component that streams agent output.
 *
 * Requires: npm install @jiuwenswarm/sdk react
 * Gateway:  ws://localhost:19000/v1/ws  (start with `jiuwenswarm serve`)
 */

import { useEffect, useRef, useState } from "react";
import { JiuwenSwarmClient } from "@jiuwenswarm/sdk";

export function ChatWidget() {
  const clientRef = useRef<JiuwenSwarmClient | null>(null);
  const [output, setOutput] = useState("");
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const client = new JiuwenSwarmClient({
      url: "ws://localhost:19000/v1/ws",
      onToken: (text) => setOutput((prev) => prev + text),
      onDone: () => setConnected(true),
      onError: (msg) => console.error(msg),
    });

    client.on("connected", () => setConnected(true));
    client.on("disconnected", () => setConnected(false));

    client.connect().then(async () => {
      const session = await client.sessions.create("React chat");
      client.sessions.setActive(session.id);
    });

    clientRef.current = client;
    return () => client.disconnect();
  }, []);

  const handleSend = async (message: string) => {
    setOutput("");
    await clientRef.current?.send(message);
  };

  return (
    <div>
      <p>Status: {connected ? "connected" : "disconnected"}</p>
      <pre>{output}</pre>
      <button onClick={() => handleSend("Summarise the Python GIL.")}>
        Ask
      </button>
    </div>
  );
}
