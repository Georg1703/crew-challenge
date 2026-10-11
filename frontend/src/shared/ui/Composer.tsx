import { useId, type FormEvent, type Ref } from "react";

import { Button } from "./Button";
import styles from "./Composer.module.css";
import { Icon } from "./Icon";
import { Quote } from "./Quote";

/**
 * A message box under a conversation: a text box that grows with what is typed (up to about five
 * lines, then it scrolls) and a send button. `replying` shows what the message answers (a reply
 * icon and the quote), with a button to stop. Enter is a new line; the button sends, once there is
 * text and nothing is sending.
 */
export function Composer({
  value,
  onChange,
  onSend,
  label,
  placeholder,
  sendLabel,
  sending = false,
  maxLength,
  replying,
  ref,
}: {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  /** The text box's name for screen readers: "Comment". */
  label: string;
  placeholder?: string;
  sendLabel: string;
  sending?: boolean;
  maxLength?: number;
  /** What the message answers: its writer and text, and the stop button's name. */
  replying?: {
    name: string;
    seed: string;
    text: string;
    stopLabel: string;
    onStop: () => void;
  };
  ref?: Ref<HTMLTextAreaElement>;
}) {
  const id = useId();
  const empty = value.trim() === "";
  const send = (event: FormEvent) => {
    event.preventDefault();
    if (!empty && !sending) onSend();
  };
  return (
    <form className={styles.composer} onSubmit={send}>
      {replying && (
        <div className={styles.replying}>
          <span className={styles.replyIcon}>
            <Icon name="reply" size={20} />
          </span>
          <span className={styles.replyingQuote}>
            <Quote name={replying.name} seed={replying.seed} text={replying.text} />
          </span>
          <Button
            variant="ghost"
            className={styles.stop}
            icon={<Icon name="close" size={18} />}
            aria-label={replying.stopLabel}
            onClick={replying.onStop}
          />
        </div>
      )}
      <div className={styles.row}>
        <label className={styles.label} htmlFor={id}>
          {label}
        </label>
        {/* The grid's hidden copy of the text sizes the box: no measuring in script. */}
        <div className={styles.grow} data-value={value}>
          <textarea
            ref={ref}
            id={id}
            className={styles.input}
            rows={1}
            value={value}
            placeholder={placeholder}
            maxLength={maxLength}
            onChange={(event) => onChange(event.target.value)}
          />
        </div>
        <Button
          type="submit"
          className={styles.send}
          icon={<Icon name="send" size={20} />}
          aria-label={sendLabel}
          loading={sending}
          disabled={empty}
        />
      </div>
    </form>
  );
}
