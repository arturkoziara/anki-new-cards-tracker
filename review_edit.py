"""Click card text during review and write it back to the note."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from aqt import mw

_TAG = re.compile(r"<[^>]+>")
_KINDS = {"reviewQuestion", "reviewAnswer", "previewQuestion", "previewAnswer"}
_JS_PATH = Path(__file__).resolve().parent / "web" / "review_edit.js"


def _plain(value: str) -> str:
    text = _TAG.sub(" ", value or "")
    return " ".join(text.replace("\xa0", " ").split())


def apply_change(current: str, old: str, new: str, whole: bool) -> Optional[str]:
    """Return the updated field text, or None when the card text is stale."""
    if whole and current == old:
        return new
    if old and old in current:
        return current.replace(old, new, 1)
    return None


def on_card_will_show(text: str, card: Any, kind: str) -> str:
    if kind not in _KINDS or not mw.col:
        return text
    try:
        note = card.note()
    except Exception:
        return text
    visible = _plain(text)
    fields = []
    for name, value in note.items():
        raw = str(value or "")
        if not raw.strip():
            continue
        plain = _plain(raw)
        if not plain:
            continue
        on_card = (
            f'data-edit="{name}"' in text
            or plain in visible
            or raw in text
        )
        if not on_card:
            continue
        fields.append({"name": name, "value": raw, "plain": plain})
    if not fields:
        return text
    try:
        script = _JS_PATH.read_text(encoding="utf-8")
    except OSError:
        return text
    payload = json.dumps(
        {"note": note.id, "side": kind, "fields": fields},
        ensure_ascii=False,
    ).replace("<", "\\u003c")
    return (
        text
        + "<script>window.NCAT_EDIT="
        + payload
        + ";</script><script>"
        + script
        + "</script>"
    )


def apply_setfield(body: str) -> None:
    if not mw.col:
        return
    try:
        data = json.loads(body)
        note_id = int(data["note"])
        field = str(data["field"])
        old = str(data.get("old", ""))
        new = str(data.get("value", ""))
        whole = bool(data.get("whole"))
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        return
    try:
        note = mw.col.get_note(note_id)
    except Exception:
        return
    if field not in note:
        return
    updated = apply_change(str(note[field]), old, new, whole)
    if updated is None or updated == note[field]:
        return
    note[field] = updated
    mw.col.update_note(note)
