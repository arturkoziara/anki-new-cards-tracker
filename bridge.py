"""Handle pycmd messages from the chart web UI."""

from __future__ import annotations

from typing import Any, List, Tuple

from aqt import dialogs, mw

from . import data, options, review_edit

CMD_PREFIX = "ncat:"


def _refresh_deck_browser() -> None:
    if mw.state == "deckBrowser" and mw.deckBrowser:
        mw.deckBrowser.refresh()


def _browse_day(iso_date: str) -> None:
    ids: List[int] = data.card_ids_for_day(iso_date)
    browser = dialogs.open("Browser", mw)
    if not ids:
        browser.search_for("cid:0")
        return
    # Anki accepts OR-joined cid terms for a day's cards
    if len(ids) > 300:
        ids = ids[:300]
    search = " OR ".join(f"cid:{cid}" for cid in ids)
    browser.search_for(search)


def on_js_message(
    handled: Tuple[bool, Any], message: str, context: Any
) -> Tuple[bool, Any]:
    if handled[0]:
        return handled
    if not message.startswith(CMD_PREFIX):
        return handled

    body = message[len(CMD_PREFIX) :]
    if body.startswith("setfield:"):
        review_edit.apply_setfield(body[len("setfield:") :])
        return (True, None)

    if body.startswith("view:"):
        view = body.split(":", 1)[1]
        options.set_view(view)
        _refresh_deck_browser()
        return (True, None)

    if body == "today":
        options.set_page(0)
        _refresh_deck_browser()
        return (True, None)

    if body.startswith("page:"):
        try:
            delta = int(body.split(":", 1)[1])
        except ValueError:
            return (True, None)
        _, page = options.get_view_state()
        options.set_page(page + delta)
        _refresh_deck_browser()
        return (True, None)

    if body.startswith("browse:"):
        iso = body.split(":", 1)[1]
        _browse_day(iso)
        return (True, None)

    return handled
