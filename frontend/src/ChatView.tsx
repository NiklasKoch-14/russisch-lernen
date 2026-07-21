import { useEffect, useState } from "react";
import { answerPlacement, getProfile, sendPracticeTurn, startPlacement } from "./api";
import type { ChatMessage } from "./types";

type Mode = "loading" | "placement" | "practice";

export default function ChatView() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<Mode>("loading");
  const [placementSessionId, setPlacementSessionId] = useState<number | null>(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    getProfile()
      .then((profile) => {
        if (profile.cefr_level === "UNPLACED") {
          return startPlacement().then((res) => {
            setPlacementSessionId(res.session_id);
            setMessages([{ role: "assistant", content: res.question }]);
            setMode("placement");
          });
        }
        setMode("practice");
      })
      .catch(() => {
        // Profile/placement lookup failed (e.g. backend unreachable); leave
        // the view in "loading" so the input stays disabled.
      });
  }, []);

  async function handleSend() {
    if (!input.trim() || sending) return;
    const userMessage = input.trim();
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setInput("");
    setSending(true);
    try {
      if (mode === "placement" && placementSessionId !== null) {
        const res = await answerPlacement(placementSessionId, userMessage);
        if (res.finished) {
          setMessages((prev) => [...prev, { role: "assistant", content: `Dein Level: ${res.level}` }]);
          setMode("practice");
        } else if (res.question) {
          setMessages((prev) => [...prev, { role: "assistant", content: res.question! }]);
        }
      } else {
        const res = await sendPracticeTurn(userMessage);
        setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
      }
    } finally {
      setSending(false);
    }
  }

  return (
    <div>
      <div data-testid="messages">
        {messages.map((m, i) => (
          <p key={i} data-role={m.role}>
            {m.content}
          </p>
        ))}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSend();
        }}
        placeholder="Deine Nachricht..."
        disabled={mode === "loading" || sending}
      />
      <button onClick={handleSend} disabled={mode === "loading" || sending}>
        Senden
      </button>
    </div>
  );
}
