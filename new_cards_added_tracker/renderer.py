"""HTML/JSON renderer for the deck-browser chart block."""

from __future__ import annotations

import html
import json
from typing import Any, Dict

from . import data, options

ADDON_TITLE = "New Cards Tracker"


def _chart_payload(cfg: Dict[str, Any]) -> Dict[str, Any]:
    view, page = options.get_view_state()
    target = int(cfg["daily_target"])
    result = data.get_range(view, page, target)

    met_today = result.today_count >= target
    return {
        "view": result.view,
        "pageOffset": result.page_offset,
        "rangeLabel": result.range_label,
        "canGoNext": result.can_go_next,
        "dailyTarget": target,
        "todayCount": result.today_count,
        "metToday": met_today,
        "targetStreak": result.target_streak,
        "days": [
            {
                "label": day.label,
                "isoDate": day.iso_date,
                "count": day.count,
                "isToday": day.is_today,
                "met": day.count >= target,
            }
            for day in result.days
        ],
    }


def render_chart_html(cfg: Dict[str, Any]) -> str:
    payload = _chart_payload(cfg)
    payload_json = html.escape(json.dumps(payload), quote=False)

    today_class = "ncat-met" if payload["metToday"] else "ncat-under"
    streak = payload["targetStreak"]
    streak_html = (
        f'<span class="ncat-streak">Target streak: <strong>{streak}</strong></span>'
        if streak > 0
        else ""
    )

    week_active = "is-active" if payload["view"] == "week" else ""
    month_active = "is-active" if payload["view"] == "month" else ""
    next_disabled = "" if payload["canGoNext"] else "disabled"
    range_label = html.escape(str(payload["rangeLabel"]))
    badge = "target met" if payload["metToday"] else "under target"

    return f"""
<div id="ncat-root" class="ncat-root">
  <div class="ncat-title">{ADDON_TITLE}</div>
  <div class="ncat-header">
    <div class="ncat-today {today_class}">
      Today: <strong>{payload["todayCount"]}</strong> / {payload["dailyTarget"]}
      <span class="ncat-today-badge">{badge}</span>
    </div>
    {streak_html}
  </div>
  <div class="ncat-controls">
    <div class="ncat-views">
      <button type="button" class="ncat-btn {week_active}" data-ncat="view:week">Week</button>
      <button type="button" class="ncat-btn {month_active}" data-ncat="view:month">Month</button>
    </div>
    <div class="ncat-pager">
      <button type="button" class="ncat-btn" data-ncat="page:-1" title="Previous">‹</button>
      <span class="ncat-range-label">{range_label}</span>
      <button type="button" class="ncat-btn" data-ncat="page:1" title="Next" {next_disabled}>›</button>
    </div>
  </div>
  <div class="ncat-chart-wrap">
    <canvas id="ncat-chart" height="200"></canvas>
  </div>
  <p class="ncat-hint">Click a bar to browse cards added that day</p>
  <pre id="ncat-data" class="ncat-data" hidden>{payload_json}</pre>
</div>
"""
