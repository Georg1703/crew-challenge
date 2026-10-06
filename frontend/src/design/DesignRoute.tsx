/**
 * Living design system page (development only, /design).
 * Shows every token and component in every state, in light and dark. Change src/styles/tokens.css
 * or a component in src/shared/ui and watch everything here update.
 */
import { useState } from "react";

import { motion, springs, type SpringName } from "@/shared/motion";
import {
  Avatar,
  AvatarStack,
  Banner,
  Button,
  Card,
  ChallengeChip,
  CheckList,
  ChipGroup,
  DayBar,
  DayBars,
  DayBarsAxis,
  DayDivider,
  DayMark,
  type DayState,
  FeedCard,
  HoldButton,
  Icon,
  IconPicker,
  IconTile,
  List,
  ListRow,
  MiniWeek,
  OptionList,
  ProgressBar,
  ProgressRing,
  ProofAddTile,
  ProofMosaic,
  ProofTile,
  ProofViewer,
  type RingSegment,
  type ViewerItem,
  QrCode,
  Segmented,
  Sheet,
  Skeleton,
  Spinner,
  Stack,
  StatGroup,
  StatusPill,
  StepProgress,
  Stepper,
  StoryAvatar,
  type StorySegment,
  TabBar,
  TextArea,
  TextField,
  Toggle,
  WeekStrip,
  useToast,
} from "@/shared/ui";

import styles from "./design.module.css";
import {
  colorTokens,
  radiusTokens,
  shadowTokens,
  sizeTokens,
  spaceTokens,
  textTokens,
} from "./tokens";
import { applyTheme, type Theme } from "@/shared/lib/theme";

// Sample pictures for the proof components: the app's own icons (no network on /design).
const PICTURES = ["/icons/icon-512.png", "/icons/icon-maskable-512.png", "/icons/icon-192.png"];
const VIEWER: ViewerItem[] = PICTURES.map((src, i) => ({
  key: src,
  kind: "photo",
  src,
  caption: `Ana, Walk, Monday 5 October (${i + 1})`,
}));

const STORIES: {
  name: string;
  seed: string;
  segments: StorySegment[];
  subtitle: string;
  fresh: number;
}[] = [
  { name: "You", seed: "you", segments: ["done", "done"], subtitle: "2/2", fresh: 0 },
  { name: "Ana", seed: "ana", segments: ["done", "started", "todo"], subtitle: "1/3", fresh: 3 },
  { name: "Bogdan", seed: "bogdan", segments: ["todo"], subtitle: "0/1", fresh: 12 },
  { name: "Dan", seed: "dan", segments: [], subtitle: "-", fresh: 0 },
];

export function DesignRoute() {
  const [theme, setTheme] = useState<Theme>("system");
  const [upload, setUpload] = useState(0.4);
  const [viewer, setViewer] = useState<number | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [bannerOpen, setBannerOpen] = useState(false);
  const [segment, setSegment] = useState("ro");
  const [often, setOften] = useState("daily");
  const [people, setPeople] = useState(["ana", "bogdan"]);
  const [days, setDays] = useState<number[]>([0, 2, 4]);
  const [times, setTimes] = useState(3);
  const [proof, setProof] = useState(true);
  const [icon, setIcon] = useState("dumbbell");
  const [ring, setRing] = useState<RingSegment[]>(["full", "partial", "empty"]);
  const [pages, setPages] = useState(12);
  const toast = useToast();

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <h1>Design system</h1>
        <p className={styles.muted}>
          Crew Challenges design system. Rules: docs/design-system.md. Tokens:
          src/styles/tokens.css. Components: src/shared/ui.
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
          <p
            key={size}
            style={{
              fontSize: `var(--text-${size})`,
              lineHeight: `var(--leading-${size})`,
              fontWeight:
                size === "body" || size === "small"
                  ? "var(--weight-regular)"
                  : "var(--weight-bold)",
            }}
          >
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

      <Section title="Sizes">
        <div className={styles.row}>
          {sizeTokens.map((size) => (
            <div key={size} className={styles.spaceItem}>
              <span className={styles.spaceBar} style={{ width: `var(--${size})` }} />
              <code>{size}</code>
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

      <Section title="Status pills and avatars">
        <div className={styles.row}>
          <StatusPill>neutral</StatusPill>
          <StatusPill tone="accent">accent</StatusPill>
          <StatusPill tone="success">success</StatusPill>
          <StatusPill tone="warning">warning</StatusPill>
          <StatusPill tone="danger">danger</StatusPill>
        </div>
        <div className={styles.row}>
          {["Ana", "Bogdan Popa", "Cristina", "Dan", "Elena M"].map((name, i) => (
            <Avatar
              key={name}
              name={name}
              seed={`seed-${i * 7}`}
              size={(["sm", "md", "lg"] as const)[i % 3]}
              ring={i === 1 ? "done" : i === 2 ? "todo" : undefined}
            />
          ))}
          <AvatarStack
            label="Six members"
            members={["Ana", "Bogdan", "Cristina", "Dan", "Elena", "Florin"].map((name, i) => ({
              id: name,
              name,
              seed: `seed-${i * 7}`,
            }))}
          />
        </div>
      </Section>

      <Section title="Lists">
        <List label="Members">
          <ListRow
            leading={<Avatar name="Bogdan" seed="seed-7" />}
            title="Bogdan"
            subtitle="Admin"
            trailing={<StatusPill tone="success">Checked in</StatusPill>}
          />
          <ListRow
            leading={
              <IconTile tone="accent">
                <Icon name="link" size={20} />
              </IconTile>
            }
            title="Invite K7P4QD"
            subtitle="Expires in 5 days"
            trailing={
              <Button variant="ghost" size="md">
                Cancel
              </Button>
            }
          />
          <ListRow
            to="/design"
            leading={
              <IconTile>
                <Icon name="users" size={20} />
              </IconTile>
            }
            title="A row that is a link"
            subtitle="The whole row is the tap target"
            trailing={<Icon name="chevronRight" size={20} />}
          />
        </List>
      </Section>

      <Section title="QR code">
        <QrCode value="https://crew.example/join/k7p4qdx2mn" label="QR code for the invite link" />
      </Section>

      <Section title="Cards">
        <Stack gap="sm">
          <Card>
            <p>A default card groups related content.</p>
          </Card>
          <Card tone="accent">
            <p>An accent card highlights the one thing that needs you.</p>
          </Card>
        </Stack>
      </Section>

      <Section title="Banners">
        <Banner title="Your turn to pick" message="Pick next month's challenge by the 25th." />
        <Banner tone="warning" title="No internet" message="We continue when it is back." />
        <Banner
          tone="danger"
          title="Wrong username or password"
          message="Check them and try again."
        />
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
          <Button variant="secondary" onClick={() => setBannerOpen(true)}>
            Show banner
          </Button>
        </div>
        <div className={styles.row}>
          <Spinner label="Loading" />
        </div>
        <Card>
          <Skeleton lines={2} />
        </Card>
        <Banner
          open={bannerOpen}
          floating
          title="A new version of the app is ready."
          actions={
            <>
              <Button variant="ghost" onClick={() => setBannerOpen(false)}>
                Later
              </Button>
              <Button onClick={() => setBannerOpen(false)}>Update</Button>
            </>
          }
        />
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

      <Section title="Form controls">
        <StepProgress current={2} total={5} label="Step 2 of 5" />
        <OptionList
          label="How often"
          value={often}
          onChange={setOften}
          options={[
            { value: "daily", title: "Every day", description: "One check-in a day, 7 of 7" },
            {
              value: "weekdays",
              title: "Chosen days",
              description: "For example Monday to Friday",
            },
            { value: "times", title: "A number of times a week", description: "Any days you like" },
          ]}
        />
        <CheckList
          label="Who takes part"
          values={people}
          onChange={setPeople}
          options={[
            {
              value: "ana",
              title: "Ana",
              description: "Proposed it",
              leading: <Avatar name="Ana" seed="a1b2c3d4" size="sm" />,
              disabled: true,
            },
            {
              value: "bogdan",
              title: "Bogdan",
              leading: <Avatar name="Bogdan" seed="e5f6" size="sm" />,
            },
            {
              value: "cristina",
              title: "Cristina",
              leading: <Avatar name="Cristina" seed="c9" size="sm" />,
            },
          ]}
        />
        <ChipGroup
          label="Days"
          values={days}
          onChange={setDays}
          options={["M", "T", "W", "T", "F", "S", "S"].map((day, index) => ({
            value: index,
            label: day,
            name: `Day ${index + 1}`,
          }))}
        />
        <Stepper
          label="Times a week"
          value={times}
          min={1}
          max={7}
          onChange={setTimes}
          decreaseLabel="Fewer"
          increaseLabel="More"
          suffix="times"
        />
        <IconPicker
          label="Icon"
          value={icon}
          onChange={setIcon}
          options={(["dumbbell", "activity", "book", "droplet", "cookie", "phone"] as const).map(
            (name) => ({ value: name, icon: name, name }),
          )}
        />
        <TextArea label="Rules" hint="What counts and what does not." />
        <Toggle
          label="Proof is required"
          description="Without it the check-in does not count."
          checked={proof}
          onChange={setProof}
        />
      </Section>

      <Section title="Check-in">
        <ProgressRing
          segments={ring}
          label="Today's ring"
          done={<span className={styles.muted}>Day done</span>}
        >
          <span className={styles.muted}>
            {ring.filter((r) => r === "full").length} of {ring.length}
          </span>
        </ProgressRing>
        <HoldButton
          label="Hold to check in"
          doneLabel="Checked in"
          done={ring.every((r) => r === "full")}
          onConfirm={() =>
            setRing((current) => {
              const next = current.findIndex((r) => r !== "full");
              return current.map((r, i) => (i === next ? "full" : r));
            })
          }
        />
        <Button variant="ghost" onClick={() => setRing(["full", "partial", "empty"])}>
          Reset the ring
        </Button>
        <ProgressBar value={pages} max={20} label={`${pages} of 20 pages`} />
        <Button variant="secondary" onClick={() => setPages((p) => (p >= 20 ? 0 : p + 5))}>
          Add 5 pages
        </Button>
        <WeekStrip
          label="This week"
          days={(
            ["done", "missed", "done", "partial", "todo", "future", "not_due"] as DayState[]
          ).map((state, i) => ({
            key: String(i),
            letter: "MTWTFSS"[i] ?? "",
            name: `Day ${i + 1}: ${state}${i === 0 || i === 2 ? ", with proof" : ""}`,
            state,
            today: i === 4,
            proof: i === 0 || i === 2,
          }))}
        />
        <div className={styles.row}>
          {(
            ["done", "partial", "todo", "missed", "not_due", "future", "outside"] as DayState[]
          ).map((state) => (
            <DayMark key={state} state={state} label={state} />
          ))}
        </div>
        <div className={styles.bars}>
          <DayBarsAxis days={Array.from({ length: 30 }, (_, i) => i + 1)} todayIndex={9} />
          {["ddddmddddd", "dmdddddddt"].map((row, r) => (
            <DayBars
              key={r}
              label={r ? "Bogdan" : "Ana"}
              proofs={Array.from({ length: 30 }, (_, i) => row[i] === "d" && i % 3 === 0)}
              states={Array.from({ length: 30 }, (_, i): DayState => {
                const mark = row[i];
                if (mark === "d") return "done";
                if (mark === "m") return "missed";
                if (mark === "t") return "todo";
                return "future";
              })}
            />
          ))}
        </div>
        <div className={styles.row}>
          {(
            ["done", "partial", "todo", "missed", "not_due", "future", "outside"] as DayState[]
          ).map((state) => (
            <DayBar key={state} state={state} label={state} />
          ))}
          <DayBar state="done" label="done, with proof" proof />
        </div>
      </Section>

      <Section title="Proofs">
        <div className={styles.proofs}>
          <ProofTile
            kind="photo"
            src={PICTURES[0]}
            label="Photo"
            onOpen={() => setViewer(0)}
            onRemove={() => toast("Photo removed", "info")}
            removeLabel="Remove photo"
          />
          <ProofTile kind="video" src={PICTURES[1]} label="Video" onOpen={() => setViewer(1)} />
          <ProofTile
            kind="photo"
            src={PICTURES[2]}
            state="uploading"
            progress={upload}
            label={`Uploading, ${Math.round(upload * 100)}%. Tap to add 20%`}
            onOpen={() => setUpload((p) => (p >= 1 ? 0 : Math.min(p + 0.2, 1)))}
          />
          <ProofTile kind="video" src={PICTURES[0]} state="paused" label="Waiting to upload" />
          <ProofTile kind="video" src={PICTURES[1]} state="processing" label="Being prepared" />
          <ProofTile kind="photo" src={PICTURES[2]} state="failed" label="Could not upload" />
          <ProofTile kind="video" state="processing" label="Being prepared, no poster yet" />
          <ProofTile
            kind="video"
            src={PICTURES[0]}
            duration="0:42"
            label="Video, 42 seconds"
            onOpen={() => setViewer(0)}
          />
          <ProofTile kind="video" label="Video, no poster yet" />
          <ProofTile kind="photo" label="Photo, no thumbnail" />
          <ProofAddTile
            accept="image/*,video/*"
            label="Add a photo or video"
            onPick={(file) => toast(`Picked ${file.name}`, "info")}
          />
        </div>
        <div className={styles.mosaics}>
          {[1, 2, 3, 5].map((count) => (
            <ProofMosaic
              key={count}
              proofs={[...PICTURES, ...PICTURES].slice(0, count).map((src, i) => ({
                key: String(i),
                kind: i === 1 ? "video" : "photo",
                state: count === 3 && i === 2 ? "processing" : "ready",
                src: count === 3 && i === 2 ? null : src,
                duration: i === 1 ? "1:05" : undefined,
                label: `Proof ${i + 1} of ${count}`,
              }))}
              onOpen={(i) => setViewer(Math.min(i, VIEWER.length - 1))}
              moreLabel={`${count - 3} more proofs`}
            />
          ))}
        </div>
        <Stack gap="sm">
          <FeedCard
            person={{ id: "ana", name: "Ana", seed: "ana" }}
            ring="done"
            text="Ana checked in"
            challenge={{ icon: "activity", label: "Walk" }}
            time="5 min ago"
            proofs={[...PICTURES, ...PICTURES].slice(0, 5).map((src, i) => ({
              key: String(i),
              kind: i === 1 ? "video" : "photo",
              state: i === 2 ? "processing" : "ready",
              src,
              duration: i === 1 ? "0:42" : undefined,
              label: `Proof ${i + 1}`,
            }))}
            onOpenProof={(i) => setViewer(Math.min(i, VIEWER.length - 1))}
            moreLabel="2 more proofs"
            week={{
              label: "Last 7 days: 6 done, today done",
              days: (["done", "done", "missed", "done", "done", "done", "done"] as DayState[]).map(
                (state, i) => ({ key: String(i), state, today: i === 6 }),
              ),
            }}
            facts={["5 days in a row", "day 12 of 30", "5 proofs"]}
          />
          <FeedCard
            person={{ id: "bogdan", name: "Bogdan", seed: "bogdan" }}
            ring="todo"
            text="Bogdan read"
            challenge={{ icon: "book", label: "Read" }}
            time="yesterday 21:40"
            amount={{
              value: "+12 pages",
              detail: "20 today",
              progress: { value: 20, max: 30, label: "20 of 30 pages" },
            }}
          />
          <FeedCard
            people={{
              members: [
                { id: "ana", name: "Ana", seed: "ana" },
                { id: "dan", name: "Dan", seed: "dan" },
              ],
              label: "Ana and Dan",
            }}
            text="Ana and Dan checked in"
            challenge={{ icon: "droplet", label: "Water" }}
            time="08:10"
          />
          <FeedCard
            person={{ id: "ana", name: "Ana", seed: "ana" }}
            tone="success"
            text="Ana kept it up"
            challenge={{ icon: "activity", label: "Walk" }}
            highlight={{ value: "7", text: "days in a row" }}
          />
          <FeedCard
            people={{
              members: STORIES.map((story) => ({
                id: story.seed,
                name: story.name,
                seed: story.seed,
              })),
              label: "The whole crew",
            }}
            tone="success"
            text="The whole crew finished the day"
          />
        </Stack>
        <ProofViewer
          items={VIEWER}
          index={viewer ?? 0}
          onIndexChange={setViewer}
          open={viewer !== null}
          onClose={() => setViewer(null)}
          label="Proofs"
          closeLabel="Close"
          previousLabel="Previous proof"
          nextLabel="Next proof"
        />
      </Section>

      <Section title="Crew">
        <div className={styles.stories}>
          {STORIES.map((story) => (
            <StoryAvatar
              key={story.seed}
              name={story.name}
              seed={story.seed}
              segments={story.segments}
              title={story.name}
              subtitle={story.subtitle}
              complete={story.segments.length > 0 && story.segments.every((s) => s === "done")}
              fresh={story.fresh}
              label={`${story.name}, ${story.subtitle}`}
              to="/design"
            />
          ))}
        </div>
        <StoryAvatar
          name="Ana Pop"
          seed="ana"
          size="lg"
          segments={["done", "started"]}
          label="Ana Pop, 1 of 2 today"
        />
        <div className={styles.row}>
          {(
            [
              ["done", "done", "missed", "done", "done", "not_due", "todo"],
              ["done", "missed", "missed", "done", "outside", "outside", "done"],
            ] as DayState[][]
          ).map((week, w) => (
            <MiniWeek
              key={w}
              label={`Last 7 days: ${week.join(", ")}`}
              days={week.map((state, i) => ({ key: String(i), state, today: i === 6 }))}
            />
          ))}
        </div>
        <DayDivider title="Today" summary="5 check-ins, 9 proofs" />
        <DayDivider title="Yesterday" />
        <StatGroup
          stats={[
            { key: "streak", value: "12", label: "days in a row", tone: "success" },
            { key: "best", value: "21", label: "longest" },
            { key: "month", value: "86%", label: "this month" },
          ]}
        />
        <div className={styles.row}>
          <ChallengeChip icon="activity" label="Walk" />
          <ChallengeChip icon="book" label="A very long challenge name that runs out of room" />
        </div>
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
              { to: "/design", label: "Today", icon: "sun", end: true },
              { to: "/crew", label: "Crew", icon: "users" },
              { to: "/me", label: "Me", icon: "user" },
            ]}
            action={{
              label: `Check in. Uploading proof, ${Math.round(upload * 100)}%`,
              icon: "check",
              count: 2,
              progress: upload,
              onClick: () => toast("The check-in sheet opens", "info"),
            }}
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
