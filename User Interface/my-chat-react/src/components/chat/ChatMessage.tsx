import type { Message } from "../../types/chat";
import styles from "./ChatMessage.module.css";

type Props = { msg: Message };

export default function ChatMessage({ msg }: Props) {
  const bubble = msg.role === "user" ? styles.user : styles.bot;
  return (
    <div className={styles.line}>
      <div className={bubble}>{msg.content}</div>
    </div>
  );
}
