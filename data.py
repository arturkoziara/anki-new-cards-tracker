"""Rollover-aware daily card creation counts using Anki day_cutoff."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Set, Tuple

from aqt import mw


SECONDS_PER_DAY = 86400

_included_deck_ids: Set[int] = set()


def set_deck_filter(deck_ids: Iterable[int]) -> None:
    """Restrict counts to these decks and their subdecks; empty means all decks."""
    global _included_deck_ids
    effective: Set[int] = set()
    col = mw.col
    for did in deck_ids:
        did = int(did)
        if col is not None and col.decks.get(did, default=False):
            effective.update(int(x) for x in col.decks.deck_and_child_ids(did))
    _included_deck_ids = effective


def _deck_clause() -> str:
    if not _included_deck_ids:
        return ""
    ids = ",".join(str(i) for i in sorted(_included_deck_ids))
    return f" AND (CASE WHEN odid != 0 THEN odid ELSE did END) IN ({ids})"


@dataclass
class DayCount:
    day_start: int  # unix seconds at start of this Anki day
    label: str
    iso_date: str
    count: int
    is_today: bool


@dataclass
class RangeResult:
    view: str
    page_offset: int
    start: date
    end: date
    days: List[DayCount]
    today_count: int
    target_streak: int
    range_label: str
    can_go_next: bool


def _day_cutoff() -> int:
    return int(mw.col.sched.day_cutoff)


def today_anki_date() -> date:
    """Calendar date label for the current Anki day (local time of day start)."""
    start = _day_cutoff() - SECONDS_PER_DAY
    return datetime.fromtimestamp(start).date()


def _anki_day_start_for_date(d: date) -> int:
    """
    Unix start of the Anki day whose local label date equals `d`.

    Uses day_cutoff alignment, with a ±1 day check for DST edges.
    """
    today = today_anki_date()
    delta_days = (today - d).days
    approx = _day_cutoff() - SECONDS_PER_DAY - delta_days * SECONDS_PER_DAY
    for candidate in (approx, approx - SECONDS_PER_DAY, approx + SECONDS_PER_DAY):
        if datetime.fromtimestamp(candidate).date() == d:
            return candidate
    return approx


def _bounds_ms(day_start: int) -> Tuple[int, int]:
    return day_start * 1000, (day_start + SECONDS_PER_DAY) * 1000


def _week_range(today: date, page_offset: int) -> Tuple[date, date]:
    end = today + timedelta(days=7 * page_offset)
    start = end - timedelta(days=6)
    return start, end


def _month_range(today: date, page_offset: int) -> Tuple[date, date]:
    y, m = today.year, today.month
    m_index = y * 12 + (m - 1) + page_offset
    y2, m2 = divmod(m_index, 12)
    m2 += 1
    start = date(y2, m2, 1)
    last_day = monthrange(y2, m2)[1]
    end = date(y2, m2, last_day)
    if page_offset == 0 and end > today:
        end = today
    return start, end


def _period_for_view(view: str, page_offset: int) -> Tuple[date, date]:
    today = today_anki_date()
    page_offset = min(0, page_offset)
    if view == "month":
        return _month_range(today, page_offset)
    return _week_range(today, page_offset)


def _counts_by_day_start(from_start: int, to_start: int) -> Dict[int, int]:
    """
    Count cards per Anki day start for day_start in
    [from_start, to_start] inclusive (unix seconds).
    """
    col = mw.col
    if col is None:
        return {}

    cutoff = _day_cutoff()
    start_ms = from_start * 1000
    end_ms = (to_start + SECONDS_PER_DAY) * 1000

    rows = col.db.all(
        """
        SELECT
          CAST(
            ? - 86400 * (1 + CAST((? - 1 - id / 1000.0) / 86400 AS INT))
            AS INT
          ) AS day_start,
          COUNT()
        FROM cards
        WHERE id >= ? AND id < ?"""
        + _deck_clause()
        + """
        GROUP BY day_start
        """,
        cutoff,
        cutoff,
        start_ms,
        end_ms,
    )

    # Pre-fill zeros for every day in the window
    result: Dict[int, int] = {}
    ds = from_start
    while ds <= to_start:
        result[ds] = 0
        ds += SECONDS_PER_DAY

    for day_start, count in rows:
        ds = int(day_start)
        if ds in result:
            result[ds] = int(count)
    return result


def today_count() -> int:
    day_start = _day_cutoff() - SECONDS_PER_DAY
    counts = _counts_by_day_start(day_start, day_start)
    return counts.get(day_start, 0)


def target_streak(target: int, lookback_days: int = 120) -> int:
    """Consecutive days from today backwards with count >= target."""
    cutoff = _day_cutoff()
    today_start = cutoff - SECONDS_PER_DAY
    from_start = cutoff - SECONDS_PER_DAY * lookback_days
    counts = _counts_by_day_start(from_start, today_start)

    streak = 0
    for i in range(lookback_days):
        day_start = cutoff - SECONDS_PER_DAY * (i + 1)
        if counts.get(day_start, 0) >= target:
            streak += 1
        else:
            break
    return streak


def _format_range_label(view: str, start: date, end: date) -> str:
    if view == "month":
        return start.strftime("%B %Y")
    if start.year == end.year and start.month == end.month:
        return f"{start.strftime('%b')} {start.day}–{end.day}, {end.year}"
    if start.year == end.year:
        return (
            f"{start.strftime('%b')} {start.day} – "
            f"{end.strftime('%b')} {end.day}, {end.year}"
        )
    return f"{start.strftime('%b %d, %Y')} – {end.strftime('%b %d, %Y')}"


def _safe_day_label(d: date) -> str:
    return f"{d.strftime('%a')} {d.day}"


def get_range(view: str, page_offset: int, target: int) -> RangeResult:
    view = "month" if view == "month" else "week"
    page_offset = min(0, int(page_offset))
    today = today_anki_date()
    start, end = _period_for_view(view, page_offset)

    date_list: List[date] = []
    day_starts: List[int] = []
    d = start
    while d <= end:
        date_list.append(d)
        day_starts.append(_anki_day_start_for_date(d))
        d += timedelta(days=1)

    if day_starts:
        counts = _counts_by_day_start(min(day_starts), max(day_starts))
    else:
        counts = {}

    days: List[DayCount] = []
    for d, ds in zip(date_list, day_starts):
        days.append(
            DayCount(
                day_start=ds,
                label=_safe_day_label(d),
                iso_date=d.isoformat(),
                count=counts.get(ds, 0),
                is_today=(d == today),
            )
        )

    return RangeResult(
        view=view,
        page_offset=page_offset,
        start=start,
        end=end,
        days=days,
        today_count=today_count(),
        target_streak=target_streak(target),
        range_label=_format_range_label(view, start, end),
        can_go_next=page_offset < 0,
    )


def _ytd_rates(
    counts_by_date: Dict[date, int], year: int, today: date, target: int
) -> Tuple[int, int]:
    """Daily average and percent of days on target for one year, through today."""
    start = date(year, 1, 1)
    if year > today.year:
        return 0, 0
    end = today if year == today.year else date(year, 12, 31)
    total = days = on_target = 0
    cursor = start
    while cursor <= end:
        count = counts_by_date.get(cursor, 0)
        total += count
        days += 1
        if count >= target:
            on_target += 1
        cursor += timedelta(days=1)
    if not days:
        return 0, 0
    return round(total / days), round(100 * on_target / days)


def _streak_stats(
    counts_by_date: Dict[date, int], today: date, target: int
) -> Tuple[int, int, int, int]:
    """Average, percent of days on target, longest streak, current streak."""
    active = [d for d, count in counts_by_date.items() if count > 0 and d <= today]
    if not active:
        return 0, 0, 0, 0
    start = min(active)
    days: List[int] = []
    cursor = start
    while cursor <= today:
        days.append(counts_by_date.get(cursor, 0))
        cursor += timedelta(days=1)
    total = sum(days)
    average = round(total / len(days)) if days else 0
    on_target = sum(1 for count in days if count >= target)
    percent = round(100 * on_target / len(days)) if days else 0

    longest = run = 0
    for count in days:
        if count >= target:
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    # A shortfall today does not wipe the run until the day is over.
    sequence = days[:-1] if days and days[-1] < target else days
    current = 0
    for count in reversed(sequence):
        if count >= target:
            current += 1
        else:
            break
    return average, percent, longest, current


def get_heatmap(page_offset: int, target: int) -> Dict[str, Any]:
    """One calendar year of added-card counts, plus streak stats."""
    today = today_anki_date()
    page_offset = min(0, int(page_offset))
    year = today.year + page_offset
    grid_start = date(year, 1, 1)
    grid_end = date(year, 12, 31)
    history_start = date(today.year - 6, 1, 1)
    query_start = min(history_start, grid_start)
    query_end = max(grid_end, today)

    start_ids = [_anki_day_start_for_date(query_start), _anki_day_start_for_date(query_end)]
    raw = _counts_by_day_start(min(start_ids), max(start_ids))
    by_date: Dict[date, int] = {}
    for day_start, count in raw.items():
        by_date[datetime.fromtimestamp(day_start).date()] = count

    days: List[Dict[str, Any]] = []
    cursor = grid_start
    while cursor <= grid_end:
        days.append(
            {
                "isoDate": cursor.isoformat(),
                "count": by_date.get(cursor, 0),
                "weekday": cursor.weekday(),  # Monday = 0
                "isToday": cursor == today,
                "isFuture": cursor > today,
            }
        )
        cursor += timedelta(days=1)

    average, percent = _ytd_rates(by_date, year, today, target)
    _average, _percent, longest, current = _streak_stats(by_date, today, target)
    return {
        "year": year,
        "canGoNext": page_offset < 0,
        "canGoPrev": year > today.year - 12,
        "dailyTarget": target,
        "todayCount": by_date.get(today, 0),
        "dailyAverage": average,
        "daysOnTarget": percent,
        "longestStreak": longest,
        "currentStreak": current,
        "days": days,
    }


def card_ids_for_day(iso_date: str) -> List[int]:
    try:
        y, m, day = (int(x) for x in iso_date.split("-"))
        d = date(y, m, day)
    except ValueError:
        return []
    if mw.col is None:
        return []
    day_start = _anki_day_start_for_date(d)
    start_ms, end_ms = _bounds_ms(day_start)
    return list(
        mw.col.db.list(
            "SELECT id FROM cards WHERE id >= ? AND id < ?"
            + _deck_clause()
            + " ORDER BY id",
            start_ms,
            end_ms,
        )
    )
