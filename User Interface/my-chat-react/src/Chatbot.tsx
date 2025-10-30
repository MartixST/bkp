import React, { useEffect, useRef, useState } from "react";
import { type Message } from "./types/chat";
import ChatHeader from "./components/chat/ChatHeader";
import MessageList from "./components/chat/MessageList";
import MessageInput from "./components/chat/MessageInput";
import LoadingIndicator from "./components/chat/LoadingIndicator";
import styles from "./Chatbot.module.css";
import "./styles/theme.css"; 

const API_BASE = (import.meta.env.VITE_API_BASE as string) || "";
const TEST_FETCH = String(import.meta.env.VITE_TEST_FETCH || "").toLowerCase() === "true";

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
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 0);
  }, [isOpen]);

  async function sendMessage(e?: React.FormEvent) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const next = [...messages, { role: "user" as const, content: text }];
    setMessages(next);
    setInput("");
    setLoading(true);

    try {
      if (TEST_FETCH) {
        const res = await fetch("https://jsonplaceholder.typicode.com/posts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: text, body: `Echo: ${text}`, userId: 1 }),
        });
        const status = res.status;
        const data = await res.json();
        const reply = `Test fetch OK (HTTP ${status}). id=${data?.id}; title="${data?.title}"`;
        setMessages((m) => [...m, { role: "assistant" as const, content: reply }]);
        return;
      }

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

      setMessages((m) => [...m, { role: "assistant" as const, content: reply }]);
    } catch (err: any) {
      setMessages((m) => [
        ...m,
        { role: "assistant" as const, content: `⚠️ Error: ${err?.message || err}` },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  const statusRight = TEST_FETCH
    ? "→ POST https://jsonplaceholder.typicode.com/posts"
    : `→ ${API_BASE ? apiUrl("/api/chat") : "(VITE_API_BASE is not set)"}`;

  return (
    <>
      {/* FAB */}
      <button
        aria-label={isOpen ? "Close chat" : "Open chat"}
        className={`${styles.fab} ${fabHover ? styles.fabHover : ""}`}
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

      {/* Panel */}
      <section
        className={`${styles.panel} ${isOpen ? styles.panelOpen : styles.panelClosed}`}
        aria-hidden={!isOpen}
      >
        <ChatHeader onClose={() => setIsOpen(false)} />
        <MessageList messages={messages} loading={loading} LoadingIndicator={LoadingIndicator} />
        <MessageInput
          inputRef={inputRef}
          input={input}
          loading={loading}
          onChange={setInput}
          onSubmit={sendMessage}
          footerRight={
            <>Mode: {TEST_FETCH ? "TEST_FETCH" : "REAL_API"} {statusRight}</>
          }
        />
      </section>
    </>
  );
}
