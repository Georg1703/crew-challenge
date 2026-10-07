"""Give Demo Crew weeks of history, so every part of Echipa and the member page has something to
show: `python manage.py seed_demo_history --username admin`.

Four challenges running since before this month (a number with a target, holding on, chosen
weekdays, three times a week), check-ins with streaks that reach every milestone (3, 7, 14, 30),
a day the whole crew finished, misses, partial days, and photos and videos as proof (1 to 5 a
day). `--username` is the member the history is built around (the longest streaks, the most
challenges). Photos are drawn here; videos are copies of the newest video the crew uploaded
(none uploaded: no videos). Writes rows directly, like seed_demo_challenge, and only with DEBUG.
Runs once: it stops when the demo challenges exist.
"""

import random
import struct
import zlib
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.challenges import selectors as challenges
from apps.challenges.models import Challenge, Participant, PeriodKind
from apps.challenges.windows import windows
from apps.checkins import days
from apps.checkins.models import CheckIn, CheckInEntry, Proof
from apps.core import clock
from apps.crews.models import Crew, Member
from apps.media.models import Upload, crew_folder
from integrations.storage import ObjectStorage, get_object_storage

C = Challenge
MON, WED, FRI = 1, 4, 16  # Challenge.on_days bits


@dataclass
class Spec:
    """One demo challenge. `who` picks members by position (the chosen member is 0)."""

    title: str
    icon: str
    measure: str
    window: str
    proof_kind: str
    began: int  # days before today
    who: list[int]
    streaks: list[int]  # due days in a row up to yesterday, one per member in `who`
    today: dict[int, int] = field(default_factory=dict)  # member -> proofs, for those done today
    unit: str = ""
    on_days: int = 0
    need: int = 1  # check-ins each window asks for
    day_min: int | None = None


SPECS = [
    Spec(
        "Citit (demo)",
        "book",
        C.Measure.QUANTITY,
        C.Window.DAY,
        C.ProofKind.PHOTO,
        began=34,
        who=[0, 1, 2, 3, 4, 5],
        streaks=[30, 16, 9, 3, 22, 5],
        today={1: 5, 2: 2, 4: 1},
        unit="pagini",
        day_min=20,
    ),
    Spec(
        "F\u0103r\u0103 zah\u0103r (demo)",
        "sugar",
        C.Measure.ABSTAIN,
        C.Window.DAY,
        C.ProofKind.NONE,
        began=16,
        who=[0, 1, 2, 3],
        streaks=[7, 16, 4, 10],
        today={1: 0, 3: 0},
    ),
    Spec(
        "Alergare (demo)",
        "running",
        C.Measure.CHECK,
        C.Window.DAY,
        C.ProofKind.VIDEO,
        began=20,
        who=[0, 2, 4],
        streaks=[4, 2, 6],
        on_days=MON | WED | FRI,
    ),
    Spec(
        "Sal\u0103 (demo)",
        "dumbbell",
        C.Measure.CHECK,
        C.Window.WEEK,
        C.ProofKind.PHOTO_OR_VIDEO,
        began=20,
        who=[0, 3, 5],
        streaks=[],
        today={3: 2},
        need=3,
    ),
]
DAYS_LEFT = 24  # every demo challenge ends this many days after today
PERFECT = 3  # days ago: everyone did everything due (the crew-day card)
PALETTES = [
    ((255, 183, 94), (237, 100, 166)),
    ((120, 200, 255), (40, 90, 200)),
    ((150, 230, 170), (30, 130, 90)),
    ((250, 220, 120), (230, 120, 60)),
    ((200, 170, 255), (90, 60, 180)),
    ((255, 160, 140), (150, 50, 70)),
]


def png(width: int, height: int, top: tuple[int, ...], bottom: tuple[int, ...]) -> bytes:
    """A top-to-bottom gradient as a PNG (the standard library has no image encoder)."""
    rows = []
    for y in range(height):
        t = y / max(height - 1, 1)
        pixel = bytes(round(a + (b - a) * t) for a, b in zip(top, bottom, strict=True))
        rows.append(b"\x00" + pixel * width)

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data)
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
        + chunk(b"IEND", b"")
    )


class Command(BaseCommand):
    help = "Give Demo Crew weeks of check-ins and proofs. Local development only."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--username", default="ana", help="The member to build it around.")

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo_history only runs with DEBUG on (local development).")
        crew = Crew.objects.filter(name="Demo Crew").first()
        if crew is None:
            raise CommandError("Run seed_demo first: Demo Crew does not exist.")
        if C.objects.for_crew(crew).filter(title=SPECS[0].title).exists():
            self.stdout.write("The demo history is already there; nothing to do.")
            return
        members = list(Member.objects.filter(crew=crew).select_related("user"))
        chosen = next((m for m in members if m.user.username == options["username"]), None)
        if chosen is None:
            raise CommandError(f"{options['username']} is not in Demo Crew.")
        others = sorted((m for m in members if m != chosen), key=lambda m: m.user.username)
        self.seeder = Seeder(crew, [chosen, *others])
        for spec in SPECS:
            self.seeder.challenge(spec)
        self.seeder.perfect_day(viewer=chosen)
        s = self.seeder
        self.stdout.write(
            self.style.SUCCESS(
                f"Added {len(SPECS)} challenges, {s.check_ins} check-ins, {s.photos} photos "
                f"and {s.videos} videos around {chosen.display_name}."
            )
        )
        if s.video is None:
            self.stdout.write("No video uploaded in Demo Crew yet, so no demo videos.")


class Seeder:
    def __init__(self, crew: Crew, members: list[Member]) -> None:
        self.crew = crew
        self.members = members
        self.zone = ZoneInfo(crew.timezone)
        self.today = clock.crew_today(crew)
        self.now = clock.now()
        self.random = random.Random(7)  # the same history every time
        self.storage: ObjectStorage = get_object_storage()
        self.admin = next(m for m in members if m.role == Member.Role.ADMIN)
        self.video = (
            Upload.objects.filter(
                crew=crew,
                status=Upload.Status.COMPLETE,
                content_type__startswith="video/",
                key__contains="/original",
            )
            .order_by("-completed_at")
            .first()
        )
        self.check_ins = self.photos = self.videos = 0

    # --- challenges ----------------------------------------------------------------------------
    def challenge(self, spec: Spec) -> None:
        start = self.today - timedelta(days=spec.began)
        challenge = C.objects.create(
            crew=self.crew,
            created_by=self.admin,
            title=spec.title,
            icon=spec.icon,
            measure=spec.measure,
            unit=spec.unit,
            window=spec.window,
            on_days=spec.on_days,
            need_value=spec.need,
            day_min=spec.day_min,
            proof_kind=spec.proof_kind,
            state=C.State.CHOSEN,
            period_kind=PeriodKind.CUSTOM,
            period_start=start,
            start_date=start,
            end_date=self.today + timedelta(days=DAYS_LEFT),
            chosen_by=self.admin,
            chosen_at=self.at(start - timedelta(days=1), 20),
        )
        taking_part = [(i, self.members[i]) for i in spec.who if i < len(self.members)]
        for _, member in taking_part:
            Participant.objects.create(crew=self.crew, challenge=challenge, member=member)
        for n, (i, member) in enumerate(taking_part):
            for day in self.history(challenge, spec, n, start):
                self.check_in(challenge, member, day, proofs=self.some_proofs(day))
            if i in spec.today:
                self.check_in(challenge, member, self.today, proofs=spec.today[i])
            elif i == 3 and spec.day_min:  # someone halfway through today
                self.check_in(challenge, member, self.today, proofs=0, partial=True)

    def history(self, challenge: Challenge, spec: Spec, n: int, start: date) -> list[date]:
        """The days before today this member was done: a streak up to yesterday, gaps before."""
        yesterday = self.today - timedelta(days=1)
        if not days.is_fixed(challenge):  # a few times a week: each window met, on any of its days
            picked: list[date] = []
            for window in windows(challenge, start, yesterday):
                span = days.Span(window.first, window.last).days(window.first, window.last)
                picked += self.random.sample(span, int(window.need))
            return sorted(picked)
        past = [start + timedelta(days=d) for d in range((self.today - start).days)]
        due = [day for day in past if days.is_due(challenge, day)]
        streak = spec.streaks[n] if n < len(spec.streaks) else 3
        if streak >= len(due):
            return due
        broken = len(due) - streak - 1  # the miss right before the streak
        earlier = [day for day in due[:broken] if self.random.random() < 0.7]
        return earlier + due[broken + 1 :]

    def perfect_day(self, *, viewer: Member) -> None:
        """Everyone does everything due PERFECT days ago, on the challenges the viewer sees."""
        day = self.today - timedelta(days=PERFECT)
        for challenge in challenges.visible(member=viewer).filter(state=C.State.CHOSEN):
            if not days.is_due(challenge, day):
                continue
            for p in Participant.objects.filter(challenge=challenge).select_related("member"):
                if day in days.span(challenge, p.left_on):
                    self.check_in(challenge, p.member, day, proofs=0)

    # --- rows ----------------------------------------------------------------------------------
    def at(self, day: date, hour: int, minute: int = 0) -> datetime:
        moment = datetime.combine(day, time(hour, minute), tzinfo=self.zone)
        return min(moment, self.now - timedelta(minutes=5))  # nothing in the future today

    def some_proofs(self, day: date) -> int:
        """Proof on about half the recent days and a few older ones; 1 to 5 photos."""
        recent = (self.today - day).days <= 10
        if self.random.random() > (0.5 if recent else 0.15):
            return 0
        return self.random.choices([1, 2, 3, 4, 5], weights=[50, 20, 15, 10, 5])[0]

    def check_in(
        self,
        challenge: Challenge,
        member: Member,
        day: date,
        *,
        proofs: int,
        partial: bool = False,
    ) -> None:
        if CheckIn.objects.filter(challenge=challenge, member=member, day=day).exists():
            return
        when = self.at(day, self.random.randint(7, 21), self.random.randint(0, 59))
        amounts: list[Decimal | None] = [None]
        if challenge.measure == C.Measure.QUANTITY:
            target = int(challenge.day_min or 10)
            amounts = (
                [Decimal(target // 2)]
                if partial
                else [Decimal(n) for n in self.random.choice([[target + 5], [12, target - 7]])]
            )
        total = sum((a for a in amounts if a is not None), Decimal(0)) if amounts[0] else None
        row = CheckIn.objects.create(
            crew=self.crew,
            challenge=challenge,
            member=member,
            day=day,
            status=CheckIn.Status.IN_PROGRESS if partial else CheckIn.Status.DONE,
            amount=total,
        )
        for number, amount in enumerate(amounts, start=1):
            entry = CheckInEntry.objects.create(
                crew=self.crew, check_in=row, number=number, amount=amount
            )
            CheckInEntry.objects.filter(pk=entry.pk).update(created_at=when, updated_at=when)
        CheckIn.objects.filter(pk=row.pk).update(created_at=when, updated_at=when)
        self.check_ins += 1
        if challenge.proof_kind == C.ProofKind.NONE:
            return
        if challenge.proof_kind == C.ProofKind.VIDEO:
            kinds = ["video"] * min(proofs, 2)
        elif challenge.proof_kind == C.ProofKind.PHOTO:
            kinds = ["photo"] * proofs
        else:  # a video now and then, photos otherwise
            kinds = [
                "video" if n == 0 and self.random.random() < 0.35 else "photo"
                for n in range(proofs)
            ]
        for n, kind in enumerate(kinds[:5]):
            self.proof(row, kind, when + timedelta(minutes=n + 1))

    def proof(self, check_in: CheckIn, kind: str, when: datetime) -> None:
        if kind == "video" and self.video is None:
            return
        proof_id = uuid4()
        folder = f"{crew_folder(self.crew.id)}proofs/{proof_id}"
        top, bottom = self.random.choice(PALETTES)
        if kind == "video":
            assert self.video is not None
            extension = self.video.key.rsplit(".", 1)[-1]
            key = f"{folder}/original.{extension}"
            original = self.upload(key, self.video.content_type, when, self.video.size)
            self.storage.copy(source=self.video.key, key=key)  # in S3, no download
            top, bottom = (40, 40, 60), (10, 10, 20)  # a dark poster
            self.videos += 1
        else:
            data = png(800, 600, top, bottom)
            original = self.upload(f"{folder}/original.png", "image/png", when, len(data))
            self.storage.put(key=original.key, data=data, content_type="image/png")
            self.photos += 1
        poster = png(320, 240, top, bottom)
        thumb = self.upload(f"{folder}/thumb.png", "image/png", when, len(poster))
        self.storage.put(key=thumb.key, data=poster, content_type="image/png")
        Proof.objects.create(
            id=proof_id,
            crew=self.crew,
            check_in=check_in,
            kind=kind,
            status=Proof.Status.READY,
            original=original,
            thumb=thumb,
            duration=self.random.randint(12, 140) if kind == "video" else None,
        )
        Proof.objects.filter(pk=proof_id).update(created_at=when, updated_at=when)

    def upload(self, key: str, content_type: str, when: datetime, size: int) -> Upload:
        return Upload.objects.create(
            crew=self.crew,
            key=key,
            content_type=content_type,
            size=size,
            mode=Upload.Mode.SINGLE,
            status=Upload.Status.COMPLETE,
            expires_at=when + timedelta(days=1),
            completed_at=when,
        )
