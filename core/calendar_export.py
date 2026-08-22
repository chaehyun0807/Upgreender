"""iCalendar (.ics) export and Google Calendar "Quick Add" link builder.
No Google API / OAuth needed — both mechanisms are just URL/text generation."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode

from core.models import CalendarEvent

KST_OFFSET_HOURS = 9  # Asia/Seoul, fixed offset (no DST) — avoids a timezone-library dependency


def _escape_ics_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _event_datetime_range_utc(d: date, time_str: str | None) -> tuple[str, str, bool]:
    """Returns (dtstart, dtend, all_day). Timed events are assumed to be in
    KST and converted to UTC; all-day events use bare YYYYMMDD."""
    if time_str:
        hh, mm = (int(x) for x in time_str.split(":"))
        start_utc = datetime(d.year, d.month, d.day, hh, mm) - timedelta(hours=KST_OFFSET_HOURS)
        end_utc = start_utc + timedelta(hours=1)
        return start_utc.strftime("%Y%m%dT%H%M%SZ"), end_utc.strftime("%Y%m%dT%H%M%SZ"), False
    end_day = d + timedelta(days=1)
    return d.strftime("%Y%m%d"), end_day.strftime("%Y%m%d"), True


def build_google_quick_add_url(event: CalendarEvent, resolved: date) -> str:
    dtstart, dtend, _all_day = _event_datetime_range_utc(resolved, event.time)
    params = {"action": "TEMPLATE", "text": event.title, "dates": f"{dtstart}/{dtend}"}
    if event.description:
        params["details"] = event.description
    if event.location:
        params["location"] = event.location
    return "https://calendar.google.com/calendar/render?" + urlencode(params)


def build_ics(events_with_dates: list[tuple[int, CalendarEvent, date]]) -> str:
    """events_with_dates: (event_id, event, resolved_date) for events whose
    date could already be resolved — the caller filters out unresolved ones."""
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//timetable-recommender//KO", "CALSCALE:GREGORIAN"]
    for event_id, event, resolved in events_with_dates:
        dtstart, dtend, all_day = _event_datetime_range_utc(resolved, event.time)
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:cal-event-{event_id}@timetable-recommender")
        lines.append(f"DTSTAMP:{now_utc}")
        if all_day:
            lines.append(f"DTSTART;VALUE=DATE:{dtstart}")
            lines.append(f"DTEND;VALUE=DATE:{dtend}")
        else:
            lines.append(f"DTSTART:{dtstart}")
            lines.append(f"DTEND:{dtend}")
        lines.append(f"SUMMARY:{_escape_ics_text(event.title)}")
        if event.description:
            lines.append(f"DESCRIPTION:{_escape_ics_text(event.description)}")
        if event.location:
            lines.append(f"LOCATION:{_escape_ics_text(event.location)}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
