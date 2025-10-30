
import styles from "./ChatHeader.module.css";

type Props = { title?: string; onClose(): void };

export default function ChatHeader({ title = "AI Assistant", onClose }: Props) {
  return (
    <header className={styles.header}>
      <div className={styles.title}>{title}</div>
      <button className={styles.closeBtn} onClick={onClose} aria-label="Close">×</button>
    </header>
  );
}
