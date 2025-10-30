import React, { useEffect, useRef } from "react";
import type { Message } from "../../types/chat";
import ChatMessage from "./ChatMessage";
import styles from "./MessageList.module.css";

type Props = {
  messages: Message[];
  loading?: boolean;
  LoadingIndicator?: React.ComponentType;
};

export default function MessageList({ messages, loading, LoadingIndicator }: Props) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className={styles.box}>
      {messages.map((m, i) => <ChatMessage key={i} msg={m} />)}
      {loading && LoadingIndicator ? <LoadingIndicator /> : null}
      <div ref={endRef} />
    </div>
  );
}
