/**
 * Living design system page (development only, /design).
 * Shows every token and component in every state, in light and dark. Change src/styles/tokens.css
 * or a component in src/shared/ui and watch everything here update.
 */
import { useState } from "react";

import { motion, springs, type SpringName } from "@/shared/motion";
import {
  Avatar,
  Badge,
  Button,
  Card,
  Icon,
  Segmented,
  Sheet,
  Skeleton,
  Spinner,
  TabBar,
  TextField,
  useToast,
} from "@/shared/ui";

import styles from "./design.module.css";
import { colorTokens, radiusTokens, shadowTokens, spaceTokens, textTokens } from "./tokens";

type Theme = "system" | "light" | "dark";

function applyTheme(theme: Theme) {
  if (theme === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = theme;
}

export function DesignRoute() {
  const [theme, setTheme] = useState<Theme>("system");
  const [sheetOpen, setSheetOpen] = useState(false);
  const [segment, setSegment] = useState("ro");
  const toast = useToast();

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <h1>Design system</h1>
        <p className={styles.muted}>
          Placeholder theme. Tokens: src/styles/tokens.css. Components: src/shared/ui.
        </p>
        <Segmented<Theme>
          label="Theme"
          value={theme}
          onChange={(value) => {
            setTheme(value);
            applyTheme(value);
          }}
          options={[
            { value: "system", label: "System" },
            { value: "light", label: "Light" },
            { value: "dark", label: "Dark" },
          ]}
        />
      </header>

      <Section title="Color">
        <div className={styles.swatches}>
          {colorTokens.map((name) => (
            <div key={name} className={styles.swatch}>
              <span className={styles.chip} style={{ background: `var(--color-${name})` }} />
              <code>--color-{name}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Typography">
        {textTokens.map((size) => (
          <p key={size} style={{ fontSize: `var(--text-${size})` }}>
            --text-{size} Provocarea lunii: citește două cărți
          </p>
        ))}
      </Section>

      <Section title="Space, radius, shadow">
        <div className={styles.row}>
          {spaceTokens.map((space) => (
            <div key={space} className={styles.spaceItem}>
              <span className={styles.spaceBar} style={{ width: `var(--space-${space})` }} />
              <code>{space}</code>
            </div>
          ))}
        </div>
        <div className={styles.row}>
          {radiusTokens.map((radius) => (
            <div
              key={radius}
              className={styles.box}
              style={{ borderRadius: `var(--radius-${radius})` }}
            >
              <code>radius-{radius}</code>
            </div>
          ))}
          {shadowTokens.map((shadow) => (
            <div
              key={shadow}
              className={styles.box}
              style={{ boxShadow: `var(--shadow-${shadow})` }}
            >
              <code>shadow-{shadow}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Motion (tap a ball)">
        <div className={styles.row}>
          {(Object.keys(springs) as SpringName[]).map((name) => (
            <SpringDemo key={name} name={name} />
          ))}
        </div>
      </Section>

      <Section title="Buttons">
        {(["primary", "secondary", "ghost", "danger"] as const).map((variant) => (
          <div key={variant} className={styles.row}>
            <Button variant={variant}>{variant}</Button>
            <Button variant={variant} icon={<Icon name="plus" />}>
              with icon
            </Button>
            <Button variant={variant} loading>
              loading
            </Button>
            <Button variant={variant} disabled>
              disabled
            </Button>
          </div>
        ))}
        <Button size="lg" fullWidth>
          Large, full width
        </Button>
      </Section>

      <Section title="Text fields">
        <TextField label="Default" placeholder="Placeholder" />
        <TextField label="With hint" hint="At least 8 characters." />
        <TextField label="With error" defaultValue="ab" error="This username is taken." />
        <TextField label="Disabled" defaultValue="Disabled" disabled />
      </Section>

      <Section title="Badges and avatars">
        <div className={styles.row}>
          <Badge>neutral</Badge>
          <Badge tone="accent">accent</Badge>
          <Badge tone="success">success</Badge>
          <Badge tone="danger">danger</Badge>
        </div>
        <div className={styles.row}>
          {["Ana", "Bogdan Popa", "Cristina", "Dan", "Elena M", "Florin"].map((name, i) => (
            <Avatar key={name} name={name} seed={`seed-${i * 7}`} size={i % 2 ? "md" : "lg"} />
          ))}
        </div>
      </Section>

      <Section title="Feedback">
        <div className={styles.row}>
          <Button variant="secondary" onClick={() => toast("Saved", "success")}>
            Success toast
          </Button>
          <Button variant="secondary" onClick={() => toast("Something went wrong.", "error")}>
            Error toast
          </Button>
          <Button variant="secondary" onClick={() => toast("Ana just checked in")}>
            Info toast
          </Button>
          <Button variant="secondary" onClick={() => setSheetOpen(true)}>
            Open sheet
          </Button>
        </div>
        <div className={styles.row}>
          <Spinner label="Loading" />
        </div>
        <Card>
          <Skeleton lines={2} />
        </Card>
        <Sheet
          open={sheetOpen}
          onClose={() => setSheetOpen(false)}
          title="A bottom sheet"
          closeLabel="Close"
        >
          <p className={styles.muted}>Sheets slide up with the gentle spring.</p>
          <Button fullWidth onClick={() => setSheetOpen(false)}>
            Done
          </Button>
        </Sheet>
      </Section>

      <Section title="Segmented control">
        <Segmented
          label="Language"
          value={segment}
          onChange={setSegment}
          options={[
            { value: "ro", label: "Română" },
            { value: "en", label: "English" },
          ]}
        />
      </Section>

      <Section title="Tab bar">
        <div className={styles.tabbarFrame}>
          <TabBar
            label="Preview"
            tabs={[
              { to: "/design", label: "Home", icon: "home", end: true },
              { to: "/crew", label: "Crew", icon: "crew" },
              { to: "/me", label: "Me", icon: "me" },
            ]}
          />
        </div>
      </Section>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>{title}</h2>
      {children}
    </section>
  );
}

function SpringDemo({ name }: { name: SpringName }) {
  const [on, setOn] = useState(false);
  return (
    <button type="button" className={styles.springTrack} onClick={() => setOn((v) => !v)}>
      <motion.span
        className={styles.ball}
        animate={{ x: on ? 96 : 0, scale: on ? 1.15 : 1 }}
        transition={springs[name]}
      />
      <code>{name}</code>
    </button>
  );
}
