"""HTML/JSON renderer for the deck-browser chart block."""

from __future__ import annotations

import html
import json
from typing import Any, Dict

from . import data, options

ADDON_TITLE = "New Cards Tracker"


def _chart_payload(cfg: Dict[str, Any]) -> Dict[str, Any]:
    _view, page = options.get_view_state()
    target = int(cfg["daily_target"])
    data.set_deck_filter(cfg["included_deck_ids"])
    return data.get_heatmap(page, target)


def render_chart_html(cfg: Dict[str, Any]) -> str:
    payload = _chart_payload(cfg)
    payload_json = html.escape(json.dumps(payload), quote=False)
    next_disabled = "" if payload["canGoNext"] else "disabled"
    prev_disabled = "" if payload["canGoPrev"] else "disabled"
    today = payload["todayCount"]
    card_word = "card" if today == 1 else "cards"

    return f"""
<div id="ncat-root" class="ncat-root">
  <div class="ncat-summary">Added <strong>{today}</strong> {card_word} today</div>
  <div class="ncat-nav">
    <button type="button" class="ncat-btn" data-ncat="page:-1" title="Previous year" {prev_disabled}>‹</button>
    <button type="button" class="ncat-btn" data-ncat="today" title="This year">○</button>
    <button type="button" class="ncat-btn" data-ncat="page:1" title="Next year" {next_disabled}>›</button>
  </div>
  <div class="ncat-scroll">
    <div class="ncat-board">
      <div id="ncat-grid" class="ncat-grid"></div>
    </div>
  </div>
  <div class="ncat-year">{payload["year"]}</div>
  <div class="ncat-stats">
    <span>Daily average: <strong class="ncat-avg">{payload["dailyAverage"]} cards</strong></span>
    <span>Days on target: <strong class="ncat-avg">{payload["daysOnTarget"]}%</strong></span>
    <span>Longest streak: <strong class="ncat-streak">{payload["longestStreak"]} days</strong></span>
    <span>Current streak: <strong class="ncat-streak">{payload["currentStreak"]} days</strong></span>
  </div>
  <pre id="ncat-data" class="ncat-data" hidden>{payload_json}</pre>
</div>
"""
