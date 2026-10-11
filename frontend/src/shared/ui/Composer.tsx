import {
  useId,
  useRef,
  type ClipboardEvent,
  type FormEvent,
  type ReactNode,
  type Ref,
} from "react";

import { Button } from "./Button";
import styles from "./Composer.module.css";
import { Icon } from "./Icon";
import { Quote } from "./Quote";

/**
 * A message box under a conversation: an emoji button, a text box that grows with what is typed
 * (up to about five lines, then it scrolls), an image button and a send button. `replying` shows
 * what the message answers (a reply icon and the quote), with a button to stop; `above` holds the
 * files picked for it (their tiles). Images can also be pasted. Enter is a new line; the button
 * sends once there is text or an `attached` file, nothing is `waiting` (uploading) and nothing is
 * sending.
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
  onEmoji,
  emojiLabel,
  onFiles,
  filesLabel,
  attached = 0,
  waiting = false,
  above,
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
  /** The emoji button (it opens a picker the caller shows). */
  onEmoji?: () => void;
  emojiLabel?: string;
  /** Images picked with the image button, or pasted. */
  onFiles?: (files: File[]) => void;
  filesLabel?: string;
  /** Files ready to go with it: the text may then be empty. */
  attached?: number;
  /** A file still uploads: sending waits. */
  waiting?: boolean;
  /** Over the box: the picked files' tiles. */
  above?: ReactNode;
  ref?: Ref<HTMLTextAreaElement>;
}) {
  const id = useId();
  const picker = useRef<HTMLInputElement>(null);
  const ready = (value.trim() !== "" || attached > 0) && !waiting;
  const send = (event: FormEvent) => {
    event.preventDefault();
    if (ready && !sending) onSend();
  };
  const paste = (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const images = [...event.clipboardData.files].filter((f) => f.type.startsWith("image/"));
    if (!onFiles || images.length === 0) return; // text pastes as text
    event.preventDefault();
    onFiles(images);
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
      {above}
      <div className={styles.row}>
        {onEmoji && (
          <Button
            variant="ghost"
            className={styles.tool}
            icon={<Icon name="smilePlus" size={22} />}
            aria-label={emojiLabel}
            onClick={onEmoji}
          />
        )}
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
            onPaste={paste}
          />
        </div>
        {onFiles && (
          <>
            <Button
              variant="ghost"
              className={styles.tool}
              icon={<Icon name="image" size={22} />}
              aria-label={filesLabel}
              onClick={() => picker.current?.click()}
            />
            <input
              ref={picker}
              type="file"
              accept="image/*"
              multiple
              hidden
              onChange={(event) => {
                onFiles([...(event.target.files ?? [])]);
                event.target.value = ""; // the same file can be picked again
              }}
            />
          </>
        )}
        <Button
          type="submit"
          className={styles.send}
          icon={<Icon name="send" size={20} />}
          aria-label={sendLabel}
          loading={sending}
          disabled={!ready}
        />
      </div>
    </form>
  );
}
