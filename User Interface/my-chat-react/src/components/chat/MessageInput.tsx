import React from "react";
import styles from "./MessageInput.module.css";

type Props = {
  input: string;
  loading: boolean;
  onChange(v: string): void;
  onSubmit(e?: React.FormEvent): void;
  footerRight?: React.ReactNode;
  inputRef?: React.RefObject<HTMLInputElement | null>;
};

export default function MessageInput({
  input,
  loading,
  onChange,
  onSubmit,
  footerRight,
  inputRef,
}: Props) {
  return (
    <footer className={styles.footer}>
      <form onSubmit={onSubmit} className={styles.row}>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => onChange(e.target.value)}
          placeholder={loading ? "Thinking…" : "Type a message…"}
          disabled={loading}
          className={styles.input}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className={styles.sendBtn}
          style={{ opacity: loading || !input.trim() ? 0.6 : 1 }}
          onMouseDown={(e) => (e.currentTarget.style.transform = "scale(0.98)")}
          onMouseUp={(e) => (e.currentTarget.style.transform = "scale(1)")}
          onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
        >
          {loading ? "…" : "Send"}
        </button>
      </form>
      <div className={styles.status}>
        <span />
        <span>{footerRight}</span>
      </div>
    </footer>
  );
}
