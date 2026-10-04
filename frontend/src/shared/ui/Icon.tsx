/** A small inline icon set (24px grid, stroke = currentColor). Add icons here, not in features. */
const PATHS = {
  home: "M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
  crew: "M16 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM8 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm8 1c2.8 0 5 1.8 5 4v2h-6M2 20v-1c0-2.8 2.7-5 6-5s6 2.2 6 5v1z",
  me: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-8 9v-1c0-3.3 3.6-6 8-6s8 2.7 8 6v1",
  copy: "M9 9h11v11H9zM5 15H4V4h11v1",
  check: "m5 12.5 4.5 4.5L19 7",
  plus: "M12 5v14M5 12h14",
  logout: "M15 4h4v16h-4M10 8l-4 4 4 4M6 12h11",
  close: "m6 6 12 12M18 6 6 18",
  share: "M12 3v12M7 8l5-5 5 5M5 13v7h14v-7",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 24 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
