from datetime import date

from core.calendar_export import build_google_quick_add_url, build_ics
from core.models import CalendarEvent


def test_resolved_date_prefers_explicit_date():
    event = CalendarEvent(title="공모전 마감", source_type="공모전", date="2026-09-15", week_number=3)
    assert event.resolved_date(date(2026, 3, 1)) == date(2026, 9, 15)


def test_resolved_date_from_week_number_and_semester_start():
    event = CalendarEvent(title="중간고사", source_type="시험일정", week_number=8)
    semester_start = date(2026, 3, 2)  # 1주차 월요일
    # 8주차 = 1주차 + 7주 = +49일
    assert event.resolved_date(semester_start) == date(2026, 4, 20)


def test_resolved_date_none_without_semester_start():
    event = CalendarEvent(title="중간고사", source_type="시험일정", week_number=8)
    assert event.resolved_date(None) is None


def test_resolved_date_none_when_nothing_known():
    event = CalendarEvent(title="미정 행사", source_type="행사")
    assert event.resolved_date(date(2026, 3, 1)) is None


def test_quick_add_url_all_day_event():
    event = CalendarEvent(title="공모전 접수 마감", source_type="공모전", date="2026-09-15")
    url = build_google_quick_add_url(event, date(2026, 9, 15))
    assert "dates=20260915%2F20260916" in url
    assert "text=" in url


def test_quick_add_url_timed_event_converts_kst_to_utc():
    event = CalendarEvent(title="설명회", source_type="행사", date="2026-09-15", time="14:00")
    url = build_google_quick_add_url(event, date(2026, 9, 15))
    # 14:00 KST(UTC+9) -> 05:00 UTC
    assert "20260915T050000Z" in url
    assert "20260915T060000Z" in url  # +1시간


def test_build_ics_contains_required_fields_and_escapes_special_chars():
    event = CalendarEvent(
        title="AI, 데이터 공모전",
        source_type="공모전",
        date="2026-09-15",
        description="접수: 팀당 3명; 상금 있음",
        location="온라인",
    )
    ics = build_ics([(1, event, date(2026, 9, 15))])
    assert "BEGIN:VCALENDAR" in ics
    assert "BEGIN:VEVENT" in ics
    assert "UID:cal-event-1@timetable-recommender" in ics
    assert "SUMMARY:AI\\, 데이터 공모전" in ics
    assert "DESCRIPTION:접수: 팀당 3명\\; 상금 있음" in ics
    assert "DTSTART;VALUE=DATE:20260915" in ics
    assert "DTEND;VALUE=DATE:20260916" in ics
    assert "END:VEVENT" in ics
    assert "END:VCALENDAR" in ics


def test_build_ics_timed_event_uses_utc_datetime_not_value_date():
    event = CalendarEvent(title="설명회", source_type="행사", date="2026-09-15", time="14:00")
    ics = build_ics([(2, event, date(2026, 9, 15))])
    assert "DTSTART:20260915T050000Z" in ics
    assert "DTEND:20260915T060000Z" in ics
    assert "VALUE=DATE" not in ics
