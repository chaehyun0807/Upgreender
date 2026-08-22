"""SQLite-backed persistence for the student profile and the syllabus
catalog. Everything is stored as JSON blobs since this is a single-user
prototype — no need for a normalized schema."""
from __future__ import annotations

import dataclasses
import json
import sqlite3
from contextlib import contextmanager

from core.config import DATA_DIR, DB_PATH, SAMPLE_PROFILE_PATH, SAMPLE_SYLLABI_PATH
from core.models import (
    CalendarEvent,
    CreditCategory,
    CreditRequirement,
    RequiredCourse,
    StudentProfile,
    Syllabus,
    TimeSlot,
    TranscriptRecord,
)


@contextmanager
def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS student_profile (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL)"
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS syllabi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT NOT NULL,
                course_name TEXT NOT NULL,
                department TEXT NOT NULL,
                category TEXT NOT NULL,
                data TEXT NOT NULL
            )"""
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS selected_timetable (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL)"
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                data TEXT NOT NULL
            )"""
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS app_settings (id INTEGER PRIMARY KEY CHECK (id = 1), semester_start TEXT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS geocode_cache "
            "(location TEXT PRIMARY KEY, lat REAL NOT NULL, lng REAL NOT NULL, matched_query TEXT)"
        )
        try:
            conn.execute("ALTER TABLE geocode_cache ADD COLUMN matched_query TEXT")
        except sqlite3.OperationalError:
            pass  # 이미 있는 컬럼 (기존 DB에 대한 마이그레이션)


def save_profile(profile: StudentProfile) -> None:
    payload = json.dumps(_profile_to_dict(profile), ensure_ascii=False)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO student_profile (id, data) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (payload,),
        )


def load_profile() -> StudentProfile | None:
    with _connect() as conn:
        row = conn.execute("SELECT data FROM student_profile WHERE id = 1").fetchone()
    if row is None:
        return None
    return _profile_from_dict(json.loads(row[0]))


def add_syllabus(syllabus: Syllabus) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO syllabi (course_code, course_name, department, category, data) VALUES (?, ?, ?, ?, ?)",
            (
                syllabus.course_code,
                syllabus.course_name,
                syllabus.department,
                syllabus.category.value,
                json.dumps(_syllabus_to_dict(syllabus), ensure_ascii=False),
            ),
        )
        return cur.lastrowid


def list_syllabi() -> list[tuple[int, Syllabus]]:
    with _connect() as conn:
        rows = conn.execute("SELECT id, data FROM syllabi ORDER BY id DESC").fetchall()
    return [(row[0], _syllabus_from_dict(json.loads(row[1]))) for row in rows]


def update_syllabus(syllabus_id: int, syllabus: Syllabus) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE syllabi SET course_code = ?, course_name = ?, department = ?, category = ?, data = ? WHERE id = ?",
            (
                syllabus.course_code,
                syllabus.course_name,
                syllabus.department,
                syllabus.category.value,
                json.dumps(_syllabus_to_dict(syllabus), ensure_ascii=False),
                syllabus_id,
            ),
        )


def delete_syllabus(syllabus_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM syllabi WHERE id = ?", (syllabus_id,))


def add_calendar_event(event: CalendarEvent) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO calendar_events (source_type, data) VALUES (?, ?)",
            (event.source_type, json.dumps(dataclasses.asdict(event), ensure_ascii=False)),
        )
        return cur.lastrowid


def list_calendar_events() -> list[tuple[int, CalendarEvent]]:
    with _connect() as conn:
        rows = conn.execute("SELECT id, data FROM calendar_events ORDER BY id DESC").fetchall()
    return [(row[0], CalendarEvent(**json.loads(row[1]))) for row in rows]


def update_calendar_event(event_id: int, event: CalendarEvent) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE calendar_events SET source_type = ?, data = ? WHERE id = ?",
            (event.source_type, json.dumps(dataclasses.asdict(event), ensure_ascii=False), event_id),
        )


def delete_calendar_event(event_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))


def save_semester_start(iso_date: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO app_settings (id, semester_start) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET semester_start = excluded.semester_start",
            (iso_date,),
        )


def load_semester_start() -> str | None:
    with _connect() as conn:
        row = conn.execute("SELECT semester_start FROM app_settings WHERE id = 1").fetchone()
    return row[0] if row else None


def get_cached_coords(location: str) -> tuple[float, float, str | None] | None:
    """Returns (lat, lng, matched_query). matched_query differs from
    `location` when the geocoder had to fall back to a shorter/fuzzier
    query (e.g. the exact room number wasn't a registered place)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT lat, lng, matched_query FROM geocode_cache WHERE location = ?", (location,)
        ).fetchone()
    return (row[0], row[1], row[2]) if row else None


def set_cached_coords(location: str, lat: float, lng: float, matched_query: str | None = None) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO geocode_cache (location, lat, lng, matched_query) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(location) DO UPDATE SET lat = excluded.lat, lng = excluded.lng, "
            "matched_query = excluded.matched_query",
            (location, lat, lng, matched_query),
        )


def load_sample_profile() -> StudentProfile | None:
    """Read data/sample_profile.json without saving it — the caller decides
    whether/when to persist it (e.g. after the user reviews it in the UI)."""
    if not SAMPLE_PROFILE_PATH.exists():
        return None
    with open(SAMPLE_PROFILE_PATH, "r", encoding="utf-8") as f:
        return _profile_from_dict(json.load(f))


def save_selected_timetable(courses: list[Syllabus]) -> None:
    payload = json.dumps([_syllabus_to_dict(c) for c in courses], ensure_ascii=False)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO selected_timetable (id, data) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (payload,),
        )


def load_selected_timetable() -> list[Syllabus] | None:
    with _connect() as conn:
        row = conn.execute("SELECT data FROM selected_timetable WHERE id = 1").fetchone()
    if row is None:
        return None
    stored = [_syllabus_from_dict(d) for d in json.loads(row[0])]
    # 저장 당시의 스냅샷이 아니라, 강의계획서 카탈로그의 최신 정보로 항상 다시 맞춘다
    # (예: 등록 후 시간/장소를 수정해도 '내 시간표'에 자동 반영되도록).
    # 카탈로그에서 삭제된 과목은 저장된 스냅샷 그대로 유지한다.
    catalog = {s.course_code: s for _, s in list_syllabi()}
    return [catalog.get(c.course_code, c) for c in stored]


def seed_sample_syllabi() -> int:
    """Load data/sample_syllabi.json into the DB, skipping course codes that
    are already present. Returns the number of newly inserted rows."""
    if not SAMPLE_SYLLABI_PATH.exists():
        return 0
    existing_codes = {s.course_code for _, s in list_syllabi()}
    with open(SAMPLE_SYLLABI_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    inserted = 0
    for entry in raw:
        if entry["course_code"] in existing_codes:
            continue
        add_syllabus(_syllabus_from_dict(entry))
        inserted += 1
    return inserted


def _profile_to_dict(profile: StudentProfile) -> dict:
    return {
        "department": profile.department,
        "year": profile.year,
        "name": profile.name,
        "double_major_departments": profile.double_major_departments,
        "transcript": [dataclasses.asdict(r) | {"category": r.category.value} for r in profile.transcript],
        "requirements": [dataclasses.asdict(r) | {"category": r.category.value} for r in profile.requirements],
        "required_courses": [
            dataclasses.asdict(rc) | {"category": rc.category.value} for rc in profile.required_courses
        ],
    }


def _profile_from_dict(d: dict) -> StudentProfile:
    return StudentProfile(
        department=d["department"],
        year=d["year"],
        name=d.get("name", ""),
        double_major_departments=d.get("double_major_departments", []),
        transcript=[
            TranscriptRecord(
                course_code=r["course_code"],
                course_name=r["course_name"],
                credits=r["credits"],
                grade=r["grade"],
                semester=r["semester"],
                category=CreditCategory.from_str(r["category"]),
            )
            for r in d.get("transcript", [])
        ],
        requirements=[
            CreditRequirement(category=CreditCategory.from_str(r["category"]), required_credits=r["required_credits"])
            for r in d.get("requirements", [])
        ],
        required_courses=[
            RequiredCourse(
                course_code=rc["course_code"],
                course_name=rc["course_name"],
                category=CreditCategory.from_str(rc["category"]),
                credits=rc["credits"],
                equivalent_codes=rc.get("equivalent_codes", []),
                note=rc.get("note", ""),
            )
            for rc in d.get("required_courses", [])
        ],
    )


def _syllabus_to_dict(s: Syllabus) -> dict:
    data = dataclasses.asdict(s)
    data["category"] = s.category.value
    return data


def _syllabus_from_dict(d: dict) -> Syllabus:
    return Syllabus(
        course_code=d["course_code"],
        course_name=d["course_name"],
        department=d["department"],
        credits=d["credits"],
        category=CreditCategory.from_str(d["category"]),
        professor=d["professor"],
        time_slots=[TimeSlot(**t) for t in d.get("time_slots", [])],
        location=d.get("location", ""),
        team_project=d.get("team_project", False),
        exam_types=d.get("exam_types", ["기말고사"]),
        attendance_intensity=d.get("attendance_intensity", "보통"),
        tags=d.get("tags", []),
        year_restriction=d.get("year_restriction"),
        prerequisites=d.get("prerequisites", []),
        allow_retake=d.get("allow_retake", False),
    )
