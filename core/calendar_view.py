"""HTML/CSS month-grid calendar renderer, in the same visual style as
core/timetable_view.py."""
from __future__ import annotations

import calendar as _calendar
from datetime import date

from core.models import CalendarEvent

WEEKDAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"]

SOURCE_COLORS = {
    "공지": "#d6e0f5",     # blue
    "공모전": "#f6ddc0",   # peach
    "행사": "#cfe8d9",     # mint
    "시험일정": "#f3d9d9",  # pink
}

MAX_CHIPS_PER_DAY = 3


def render_month_calendar_html(year: int, month: int, events_by_day: dict[date, list[CalendarEvent]]) -> str:
    cal = _calendar.Calendar(firstweekday=6)  # 일요일 시작
    weeks = cal.monthdayscalendar(year, month)  # 0 = 이번 달이 아닌 날

    cells = []
    for day in WEEKDAY_LABELS:
        cells.append(
            f'<div style="padding:6px;text-align:center;font-weight:600;font-size:13px;'
            f'color:#555;background:#fafafa;">{day}</div>'
        )

    today = date.today()
    for week in weeks:
        for day_num in week:
            if day_num == 0:
                cells.append('<div style="background:#fafafa;min-height:88px;"></div>')
                continue
            d = date(year, month, day_num)
            is_today = d == today
            events = events_by_day.get(d, [])
            chips = "".join(
                f'<div style="background:{SOURCE_COLORS.get(e.source_type, "#eee")};border-radius:5px;'
                f'padding:2px 5px;margin-top:2px;font-size:11px;color:#2b2b2b;overflow:hidden;'
                f'text-overflow:ellipsis;white-space:nowrap;" title="{e.title}">{e.title}</div>'
                for e in events[:MAX_CHIPS_PER_DAY]
            )
            overflow = len(events) - MAX_CHIPS_PER_DAY
            if overflow > 0:
                chips += f'<div style="font-size:10px;color:#888;margin-top:2px;">+{overflow}개</div>'
            day_number_style = (
                "background:#4a7dff;color:white;border-radius:50%;width:22px;height:22px;"
                "display:flex;align-items:center;justify-content:center;font-size:12px;"
                if is_today
                else "font-size:12px;color:#333;"
            )
            cells.append(
                f'<div style="border:1px solid #eee;min-height:88px;padding:5px;vertical-align:top;">'
                f'<div style="{day_number_style}">{day_num}</div>{chips}</div>'
            )

    return (
        '<div style="display:grid;grid-template-columns:repeat(7,1fr);border:1px solid #ddd;'
        'border-radius:14px;overflow:hidden;background:white;'
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;\">"
        + "".join(cells)
        + "</div>"
    )
