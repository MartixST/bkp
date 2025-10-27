import React, { useEffect, useRef, useState } from "react";

type Message = { role: "user" | "assistant"; content: string };

const COLOR_PRIMARY = "#58d2e4ff"; 

// .env flags
const API_BASE = (import.meta.env.VITE_API_BASE as string) || "";
const TEST_FETCH =
  String(import.meta.env.VITE_TEST_FETCH || "").toLowerCase() === "true";

function apiUrl(path: string) {
  const base = (API_BASE || "").replace(/\/+$/, "");
  const tail = path.startsWith("/") ? path : `/${path}`;
  return `${base}${tail}`;
}

export default function Chatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [fabHover, setFabHover] = useState(false);

  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hi! Ask me anything." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isOpen]);

  async function sendMessage(e?: React.FormEvent) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const next = [...messages, { role: "user" as const, content: text }];
    setMessages(next);
    setInput("");
    setLoading(true);

    try {
      // ----- TEST FETCH (public service) -----
      if (TEST_FETCH) {
        const res = await fetch("https://jsonplaceholder.typicode.com/posts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: text,
            body: `Echo: ${text}`,
            userId: 1,
          }),
        });
        const status = res.status;
        const data = await res.json();
        const reply = `Test fetch OK (HTTP ${status}). id=${data?.id}; title="${data?.title}"`;
        setMessages((m) => [
          ...m,
          { role: "assistant" as const, content: reply },
        ]);
        return;
      }

      // ----- REAL API (when available) -----
      const res = await fetch(apiUrl("/api/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: next }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const reply =
        data.reply ??
        data.message ??
        (typeof data === "string" ? data : JSON.stringify(data));
      setMessages((m) => [
        ...m,
        { role: "assistant" as const, content: reply },
      ]);
    } catch (err: any) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant" as const,
          content: `⚠️ Error: ${err?.message || err}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  // ---------- Styles ----------
  const z = 9999;

  const fabBtn: React.CSSProperties = {
    position: "fixed",
    right: 24,
    bottom: 24,
    width: 60,
    height: 60,
    borderRadius: "50%",
    background: COLOR_PRIMARY,
    color: "#fff",
    border: "none",
    outline: "none",
    boxShadow: fabHover
      ? "0 14px 36px rgba(19, 168, 188, 0.45)"
      : "0 10px 28px rgba(19, 168, 188, 0.35)",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    lineHeight: 0,
    zIndex: z,
    transform: fabHover ? "scale(1.06)" : "scale(1)",
    transition: "transform 180ms ease, box-shadow 220ms ease",
  };

  const panelBase: React.CSSProperties = {
    position: "fixed",
    right: 24,
    bottom: 90,
    width: 380,
    maxWidth: "calc(100vw - 32px)",
    height: "70vh",
    maxHeight: 640,
    background: "#ffffff",
    borderRadius: 16,
    boxShadow: "0 20px 50px rgba(0,0,0,.25)",
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
    zIndex: z,
    transformOrigin: "bottom right",
    transition: "transform 220ms ease, opacity 220ms ease",
  };

  const header: React.CSSProperties = {
    height: 56,
    background: COLOR_PRIMARY,
    color: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 14px 0 16px",
    borderBottom: "1px solid rgba(255,255,255,.12)",
  };

  const title: React.CSSProperties = {
    fontWeight: 700,
    fontSize: 16,
    letterSpacing: 0.2,
  };

  const closeBtn: React.CSSProperties = {
    border: "none",
    background: "transparent",
    color: "#ffffff",
    cursor: "pointer",
    fontSize: 20,
  };

  const messagesBox: React.CSSProperties = {
    flex: 1,
    background: "#f6f7fb",
    padding: 12,
    overflowY: "auto",
  };

  const lineCommon: React.CSSProperties = {
    display: "flex",
    marginBottom: 10,
  };

  const bubbleUser: React.CSSProperties = {
    marginLeft: "auto",
    background: COLOR_PRIMARY,
    color: "#fff",
    padding: "10px 12px",
    borderRadius: 14,
    maxWidth: "80%",
    lineHeight: 1.4,
    fontSize: 14,
    wordBreak: "break-word",
    boxShadow: "0 6px 16px rgba(19, 168, 188, 0.25)",
  };

  const bubbleBot: React.CSSProperties = {
    marginRight: "auto",
    background: "#fff",
    border: "1px solid #e5e7eb",
    color: "#111",
    padding: "10px 12px",
    borderRadius: 14,
    maxWidth: "80%",
    lineHeight: 1.5,
    fontSize: 14,
    wordBreak: "break-word",
    boxShadow: "0 4px 12px rgba(0,0,0,0.06)",
  };

  const footer: React.CSSProperties = {
    padding: 12,
    borderTop: "1px solid #eef0f4",
    background: "#fff",
  };

  const inputWrap: React.CSSProperties = {
    display: "flex",
    gap: 8,
  };

  const inputStyle: React.CSSProperties = {
    flex: 1,
    border: "1px solid #e5e7eb",
    borderRadius: 12,
    padding: "10px 12px",
    outline: "none",
  };

  const sendBtn: React.CSSProperties = {
    border: "none",
    borderRadius: 12,
    padding: "10px 14px",
    background: COLOR_PRIMARY,
    color: "#fff",
    cursor: "pointer",
    opacity: loading || !input.trim() ? 0.6 : 1,
    transition: "transform 120ms ease",
  };

  const status: React.CSSProperties = {
    fontSize: 11,
    color: "#64748b",
    marginTop: 6,
  };

  const panelStyle = {
    ...panelBase,
    transform: isOpen ? "translateY(0) scale(1)" : "translateY(10px) scale(0.98)",
    opacity: isOpen ? 1 : 0,
    pointerEvents: isOpen ? "auto" : "none",
  } as React.CSSProperties;

  return (
    <>
      {/* Floating Action Button */}
      <button
        aria-label={isOpen ? "Close chat" : "Open chat"}
        style={fabBtn}
        onMouseEnter={() => setFabHover(true)}
        onMouseLeave={() => setFabHover(false)}
        onClick={() => setIsOpen((v) => !v)}
        title={isOpen ? "Close chat" : "Chat with us"}
      >
        {isOpen ? (
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" style={{ display: "block" }}>
            <path d="M6 6l12 12M18 6L6 18" stroke="white" strokeWidth="2" strokeLinecap="round" />
          </svg>
        ) : (
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" style={{ display: "block" }}>
            <path
              d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H9l-4 3v-3H6a2 2 0 0 1-2-2V6z"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </button>

      {/* Chat panel */}
      <section style={panelStyle} aria-hidden={!isOpen}>
        <header style={header}>
          <div style={title}>AI Assistant</div>
          <button style={closeBtn} onClick={() => setIsOpen(false)} aria-label="Close">
            ×
          </button>
        </header>

        <div style={messagesBox}>
          {messages.map((m, i) => (
            <div key={i} style={lineCommon}>
              <div style={m.role === "user" ? bubbleUser : bubbleBot}>{m.content}</div>
            </div>
          ))}
          <div ref={endRef} />
        </div>

        <footer style={footer}>
          <form onSubmit={sendMessage} style={inputWrap}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={loading ? "Thinking…" : "Type a message…"}
              disabled={loading}
              style={inputStyle}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              style={sendBtn}
              onMouseDown={(e) => (e.currentTarget.style.transform = "scale(0.98)")}
              onMouseUp={(e) => (e.currentTarget.style.transform = "scale(1)")}
              onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
            >
              {loading ? "…" : "Send"}
            </button>
          </form>
          <div style={status}>
            Mode: {TEST_FETCH ? "TEST_FETCH" : "REAL_API"}{" "}
            {TEST_FETCH
              ? "→ POST https://jsonplaceholder.typicode.com/posts"
              : `→ ${API_BASE ? apiUrl("/api/chat") : "(VITE_API_BASE is not set)"}`}
          </div>
        </footer>
      </section>
    </>
  );
}
