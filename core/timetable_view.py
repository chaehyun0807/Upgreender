"""Shared HTML/CSS weekly timetable renderer, used by both the Home page
(선택한 추천 시간표를 보여줌) and the recommendation results page."""
from __future__ import annotations

from core.models import Syllabus

DAY_ORDER = ["월", "화", "수", "목", "금", "토", "일"]

PASTELS = [
    "#f3d9d9",  # pink
    "#f5edc0",  # yellow
    "#cfe8d9",  # mint
    "#d6e0f5",  # blue
    "#e3d9f2",  # lavender
    "#f6ddc0",  # peach
    "#d9f0f0",  # teal
    "#e8d9ea",  # purple
]


def _assign_colors(courses: list[Syllabus]) -> dict[str, str]:
    colors: dict[str, str] = {}
    for course in courses:
        if course.course_code not in colors:
            colors[course.course_code] = PASTELS[len(colors) % len(PASTELS)]
    return colors


def render_timetable_html(courses: list[Syllabus]) -> str:
    if not courses:
        return "<p style='color:#888;'>표시할 시간표가 없습니다.</p>"

    days_used = [d for d in DAY_ORDER if any(t.day == d for c in courses for t in c.time_slots)]
    days = days_used or DAY_ORDER[:5]

    all_periods = [t.start for c in courses for t in c.time_slots] + [t.end for c in courses for t in c.time_slots]
    min_p = min(all_periods) if all_periods else 1
    max_p = max(all_periods) if all_periods else 9
    num_periods = max_p - min_p + 1

    colors = _assign_colors(courses)

    label_w = 44
    row_h = 60
    header_h = 34

    def row_of(period: int) -> int:
        return period - min_p + 2  # +2: grid is 1-indexed, row 1 is the header

    def col_of(day: str) -> int:
        return days.index(day) + 2  # +2: grid is 1-indexed, col 1 is the period label

    cells = ['<div style="grid-column:1;grid-row:1;"></div>']

    for day in days:
        c = col_of(day)
        cells.append(
            f'<div style="grid-column:{c};grid-row:1;display:flex;align-items:center;'
            f'justify-content:center;font-weight:600;font-size:14px;color:#333;">{day}</div>'
        )

    for p in range(min_p, max_p + 1):
        r = row_of(p)
        cells.append(
            f'<div style="grid-column:1;grid-row:{r};display:flex;align-items:flex-start;'
            f'justify-content:flex-end;padding:4px 8px 0 0;font-size:13px;color:#888;">{p}</div>'
        )

    occupied: set[tuple[str, int]] = set()
    for course in courses:
        color = colors[course.course_code]
        for t in course.time_slots:
            if t.day not in days:
                continue
            r1 = row_of(t.start)
            r2 = row_of(t.end) + 1
            c = col_of(t.day)
            for p in range(t.start, t.end + 1):
                occupied.add((t.day, p))
            cells.append(
                f'<div style="grid-column:{c};grid-row:{r1} / {r2};background:{color};'
                f'border-radius:8px;margin:1px;padding:6px 8px;">'
                f'<div style="font-weight:700;font-size:13px;color:#2b2b2b;line-height:1.3;">{course.course_name}</div>'
                f'<div style="font-size:11px;color:#555;margin-top:2px;">{course.professor}</div>'
                f"</div>"
            )

    for day in days:
        c = col_of(day)
        for p in range(min_p, max_p + 1):
            if (day, p) in occupied:
                continue
            r = row_of(p)
            cells.append(
                f'<div style="grid-column:{c};grid-row:{r};border-left:1px solid #eee;'
                f'border-top:1px solid #eee;"></div>'
            )

    grid_template_columns = f"{label_w}px " + " ".join(["1fr"] * len(days))
    grid_template_rows = f"{header_h}px " + " ".join([f"{row_h}px"] * num_periods)

    return (
        f'<div style="display:grid;grid-template-columns:{grid_template_columns};'
        f"grid-template-rows:{grid_template_rows};border:1px solid #ddd;border-radius:14px;"
        f"background:white;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;\">"
        + "".join(cells)
        + "</div>"
    )
