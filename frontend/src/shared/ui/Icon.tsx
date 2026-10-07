import { createElement } from "react";

/*
 * The app's icon set: shapes copied from Lucide (https://lucide.dev, ISC license), 24px grid,
 * stroke = currentColor, stroke width 1.75. Add icons here, never inside a feature.
 */
type Shape =
  | ["path", { d: string }]
  | ["circle", { cx: number; cy: number; r: number }]
  | ["rect", { x: number; y: number; width: number; height: number; rx: number }];

const ICONS = {
  sun: [
    ["circle", { cx: 12, cy: 12, r: 4 }],
    [
      "path",
      {
        d: "M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41",
      },
    ],
  ],
  users: [
    ["path", { d: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" }],
    ["circle", { cx: 9, cy: 7, r: 4 }],
    ["path", { d: "M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" }],
  ],
  user: [
    ["path", { d: "M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" }],
    ["circle", { cx: 12, cy: 7, r: 4 }],
  ],
  userPlus: [
    ["path", { d: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" }],
    ["circle", { cx: 9, cy: 7, r: 4 }],
    ["path", { d: "M19 8v6M22 11h-6" }],
  ],
  bell: [
    ["path", { d: "M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" }],
    ["path", { d: "M10.3 21a1.94 1.94 0 0 0 3.4 0" }],
  ],
  camera: [
    [
      "path",
      {
        d: "M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z",
      },
    ],
    ["circle", { cx: 12, cy: 13, r: 3 }],
  ],
  link: [
    ["path", { d: "M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" }],
    ["path", { d: "M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" }],
  ],
  copy: [
    ["rect", { x: 8, y: 8, width: 14, height: 14, rx: 2 }],
    ["path", { d: "M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" }],
  ],
  share: [
    ["path", { d: "M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" }],
    ["path", { d: "M16 6l-4-4-4 4M12 2v13" }],
  ],
  close: [["path", { d: "M18 6 6 18M6 6l12 12" }]],
  check: [["path", { d: "M20 6 9 17l-5-5" }]],
  plus: [["path", { d: "M5 12h14M12 5v14" }]],
  smilePlus: [
    ["path", { d: "M22 11v1a10 10 0 1 1-9-10" }],
    ["path", { d: "M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01M16 5h6M19 2v6" }],
  ],
  chevronRight: [["path", { d: "m9 18 6-6-6-6" }]],
  chevronLeft: [["path", { d: "m15 18-6-6 6-6" }]],
  logout: [
    ["path", { d: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" }],
    ["path", { d: "M16 17l5-5-5-5M21 12H9" }],
  ],
  download: [
    ["path", { d: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" }],
    ["path", { d: "M7 10l5 5 5-5M12 15V3" }],
  ],
  addSquare: [
    ["rect", { x: 3, y: 3, width: 18, height: 18, rx: 2 }],
    ["path", { d: "M8 12h8M12 8v8" }],
  ],
  calendarX: [
    ["rect", { x: 3, y: 4, width: 18, height: 18, rx: 2 }],
    ["path", { d: "M16 2v4M8 2v4M3 10h18M10 14l4 4M14 14l-4 4" }],
  ],
  clock: [
    ["circle", { cx: 12, cy: 12, r: 10 }],
    ["path", { d: "M12 6v6l4 2" }],
  ],
  alert: [
    ["circle", { cx: 12, cy: 12, r: 10 }],
    ["path", { d: "M12 8v4M12 16h.01" }],
  ],
  phone: [
    ["rect", { x: 5, y: 2, width: 14, height: 20, rx: 2 }],
    ["path", { d: "M12 18h.01" }],
  ],
  minus: [["path", { d: "M5 12h14" }]],
  pencil: [["path", { d: "M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" }]],
  trash: [
    [
      "path",
      { d: "M3 6h18M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" },
    ],
  ],
  flag: [["path", { d: "M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1zM4 22v-7" }]],
  // Challenge icons (keys match apps.challenges.models.ICONS through features/challenges).
  dumbbell: [
    ["path", { d: "m6.5 6.5 11 11M21 21l-1-1M3 3l1 1M18 22l4-4M2 6l4-4M3 10l7-7M14 21l7-7" }],
  ],
  activity: [["path", { d: "M22 12h-4l-3 9L9 3l-3 9H2" }]],
  book: [
    ["path", { d: "M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" }],
    ["path", { d: "M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" }],
  ],
  droplet: [
    [
      "path",
      {
        d: "M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z",
      },
    ],
  ],
  cookie: [
    ["path", { d: "M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5" }],
    ["path", { d: "M8.5 8.5v.01M16 15.5v.01M12 12v.01M11 17v.01M7 14v.01" }],
  ],
  moon: [["path", { d: "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" }]],
  mountain: [["path", { d: "m8 3 4 8 5-5 5 15H2L8 3z" }]],
  heart: [
    [
      "path",
      {
        d: "M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z",
      },
    ],
  ],
  apple: [
    [
      "path",
      {
        d: "M12 20.94c1.5 0 2.75 1.06 4 1.06 3 0 6-8 6-12.22A4.91 4.91 0 0 0 17 5c-2.22 0-4 1.44-5 2-1-.56-2.78-2-5-2a4.9 4.9 0 0 0-5 4.78C2 14 5 22 8 22c1.25 0 2.5-1.06 4-1.06Z",
      },
    ],
    ["path", { d: "M10 2c1 .5 2 2 2 5" }],
  ],
  wallet: [
    ["path", { d: "M21 12V7H5a2 2 0 0 1 0-4h14v4" }],
    ["path", { d: "M3 5v14a2 2 0 0 0 2 2h16v-5" }],
    ["path", { d: "M18 12a2 2 0 0 0 0 4h4v-4Z" }],
  ],
  star: [
    [
      "path",
      {
        d: "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z",
      },
    ],
  ],
  play: [["path", { d: "M6 3l14 9-14 9z" }]],
  pause: [
    ["rect", { x: 14, y: 4, width: 4, height: 16, rx: 1 }],
    ["rect", { x: 6, y: 4, width: 4, height: 16, rx: 1 }],
  ],
  retry: [
    ["path", { d: "M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" }],
    ["path", { d: "M3 3v5h5" }],
  ],
  image: [
    ["rect", { x: 3, y: 3, width: 18, height: 18, rx: 2 }],
    ["circle", { cx: 9, cy: 9, r: 2 }],
    ["path", { d: "m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" }],
  ],
  video: [
    ["path", { d: "m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5" }],
    ["rect", { x: 2, y: 6, width: 14, height: 12, rx: 2 }],
  ],
} satisfies Record<string, Shape[]>;

export type IconName = keyof typeof ICONS;

export function Icon({ name, size = 24 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {(ICONS[name] as Shape[]).map(([tag, attrs], index) =>
        createElement(tag, { key: index, ...attrs }),
      )}
    </svg>
  );
}
