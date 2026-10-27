"""What a push notification says, in the recipient's language. The in-app list says the same
through the frontend's i18n; these lines exist because a push is built on the server."""

import json
from pathlib import Path
from typing import Any

# kind, then what was acted on ("on": the target's key); "*" for any. In texts.json: Python
# sources stay ASCII (AGENTS.md), Romanian does not.
LINES: dict[str, dict[str, dict[str, str]]] = json.loads(
    Path(__file__).with_name("texts.json").read_text(encoding="utf-8")
)


def line(*, language: str, kind: str, actor: str, facts: dict[str, Any]) -> str:
    """One line for a notification; Romanian when the language is unknown."""
    by_kind = LINES.get(language, LINES["ro"])[kind]
    template = by_kind.get(str(facts.get("on")), by_kind["*"])
    return template.format(actor=actor, emoji=facts.get("emoji", ""), text=facts.get("text", ""))
