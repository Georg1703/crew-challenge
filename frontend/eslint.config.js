// ESLint rules that keep the frontend architecture and design system consistent.
// See frontend/AGENTS.md and docs/design-system.md for the reasons behind each rule.
import js from "@eslint/js";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

const FEATURES = "@/features";
const MOTION_PATHS = ["motion", "motion/react", "motion/react-client", "framer-motion"].map(
  (name) => ({
    name,
    message: "Import animation from @/shared/motion so presets stay consistent.",
  }),
);

export default tseslint.config(
  { ignores: ["dist", "coverage", "src/api/schema.gen.ts", "playwright-report", "test-results"] },
  js.configs.recommended,
  ...tseslint.configs.strict,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { globals: { ...globals.browser }, ecmaVersion: 2023 },
    plugins: { react, "react-hooks": reactHooks },
    settings: { react: { version: "detect" } },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "@typescript-eslint/consistent-type-imports": "error",

      // i18n: no user-visible text literals in JSX; use t("...").
      "react/jsx-no-literals": ["error", { noStrings: false, ignoreProps: true }],

      // Design system: no inline styles; style with CSS Modules + tokens.
      "react/forbid-dom-props": ["error", { forbid: ["style"] }],

      // Only src/api talks to the network.
      "no-restricted-globals": [
        "error",
        { name: "fetch", message: "Use the typed client from @/api (src/api/client.ts)." },
      ],

      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: [`${FEATURES}/*/*`],
              message: "Import another feature only through its index: @/features/<name>.",
            },
            {
              group: ["../../*", "../../../*"],
              message: "Use the @/ alias for imports outside this folder's parent.",
            },
          ],
          paths: MOTION_PATHS,
        },
      ],
    },
  },
  // Shared code is the foundation: it must not depend on features or the app shell.
  {
    files: ["src/shared/**/*.{ts,tsx}", "src/api/**/*.{ts,tsx}", "src/i18n/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@/features", "@/features/*"],
              message: "Shared code must not import features.",
            },
            { group: ["@/app", "@/app/*"], message: "Shared code must not import the app shell." },
          ],
          paths: MOTION_PATHS,
        },
      ],
    },
  },
  // The few places allowed to do what the rules above forbid elsewhere.
  { files: ["src/api/**"], rules: { "no-restricted-globals": "off" } },
  {
    files: ["src/shared/motion/**"],
    rules: { "no-restricted-imports": "off" },
  },
  {
    // Shared UI and the /design page may set CSS values inline (the design page renders tokens).
    files: ["src/shared/ui/**", "src/design/**"],
    rules: { "react/forbid-dom-props": "off" },
  },
  {
    files: ["**/*.test.{ts,tsx}", "src/test/**", "e2e/**", "src/design/**"],
    rules: { "react/jsx-no-literals": "off", "no-restricted-globals": "off" },
  },
  {
    files: ["*.config.{js,ts}", "e2e/**"],
    languageOptions: { globals: { ...globals.node } },
  },
);
