from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum


class CreditCategory(str, Enum):
    필수교양 = "필수교양"
    중핵교양 = "중핵교양"
    토대교양 = "토대교양"
    전공필수 = "전공필수"
    전공선택 = "전공선택"
    일반선택 = "일반선택"

    @classmethod
    def from_str(cls, value: str) -> "CreditCategory":
        value = (value or "").strip()
        for member in cls:
            if member.value == value:
                return member
        # Loose fallback for LLM output variance (e.g. "전공 필수", "교양필수")
        normalized = value.replace(" ", "")
        for member in cls:
            if member.value == normalized:
                return member
        return cls.일반선택


@dataclass
class TimeSlot:
    day: str  # "월", "화", "수", "목", "금", "토", "일"
    start: int  # 교시 시작 (1부터)
    end: int  # 교시 끝 (포함)

    def overlaps(self, other: "TimeSlot") -> bool:
        return self.day == other.day and self.start <= other.end and other.start <= self.end


@dataclass
class CreditRequirement:
    category: CreditCategory
    required_credits: float


@dataclass
class TranscriptRecord:
    course_code: str
    course_name: str
    credits: float
    grade: str
    semester: str
    category: CreditCategory


@dataclass
class RequiredCourse:
    """A specific course that a curriculum handbook (학사편람) mandates,
    as opposed to CreditRequirement which is just an aggregate credit total
    per category."""

    course_code: str
    course_name: str
    category: CreditCategory
    credits: float
    equivalent_codes: list[str] = field(default_factory=list)  # 학사편람에 명시된 대체/동등 과목 코드
    note: str = ""  # 비고란 원문


@dataclass
class StudentProfile:
    department: str
    year: int
    name: str = ""
    transcript: list[TranscriptRecord] = field(default_factory=list)
    requirements: list[CreditRequirement] = field(default_factory=list)
    required_courses: list[RequiredCourse] = field(default_factory=list)
    double_major_departments: list[str] = field(default_factory=list)

    @property
    def completed_course_codes(self) -> set[str]:
        return {r.course_code for r in self.transcript if r.grade.strip().upper() != "F"}

    def earned_credits_by_category(self) -> dict[CreditCategory, float]:
        totals: dict[CreditCategory, float] = {c: 0.0 for c in CreditCategory}
        for record in self.transcript:
            if record.grade.strip().upper() == "F":
                continue
            totals[record.category] = totals.get(record.category, 0.0) + record.credits
        return totals

    def remaining_credits_by_category(self) -> dict[CreditCategory, float]:
        earned = self.earned_credits_by_category()
        remaining: dict[CreditCategory, float] = {}
        for req in self.requirements:
            remaining[req.category] = max(0.0, req.required_credits - earned.get(req.category, 0.0))
        return remaining

    def satisfied_by_code(self, required_course: RequiredCourse) -> str | None:
        """Which course code (the required one itself or one of its declared
        equivalents) actually satisfies this requirement, or None if unmet."""
        completed = self.completed_course_codes
        for code in [required_course.course_code, *required_course.equivalent_codes]:
            if code in completed:
                return code
        return None

    def missing_required_courses(self) -> list[RequiredCourse]:
        return [rc for rc in self.required_courses if self.satisfied_by_code(rc) is None]

    def required_course_progress(self) -> dict[CreditCategory, dict[str, float]]:
        """Per-category credit progress computed from the specific required
        course list (학사편람), as opposed to remaining_credits_by_category()
        which uses the aggregate CreditRequirement totals."""
        progress: dict[CreditCategory, dict[str, float]] = {}
        for rc in self.required_courses:
            entry = progress.setdefault(rc.category, {"filled": 0.0, "total": 0.0})
            entry["total"] += rc.credits
            if self.satisfied_by_code(rc) is not None:
                entry["filled"] += rc.credits
        for entry in progress.values():
            entry["missing"] = entry["total"] - entry["filled"]
        return progress


@dataclass
class Syllabus:
    course_code: str
    course_name: str
    department: str
    credits: float
    category: CreditCategory
    professor: str
    time_slots: list[TimeSlot] = field(default_factory=list)
    location: str = ""  # 강의실 위치 (예: "공학관 302호") — 캠퍼스 지도 표시에 사용
    team_project: bool = False
    exam_types: list[str] = field(default_factory=lambda: ["기말고사"])  # e.g. ["중간고사", "기말고사"], ["프로젝트발표"]
    attendance_intensity: str = "보통"  # "낮음" | "보통" | "높음"
    tags: list[str] = field(default_factory=list)
    year_restriction: int | None = None
    prerequisites: list[str] = field(default_factory=list)
    allow_retake: bool = False

    def overlaps(self, other: "Syllabus") -> bool:
        return any(a.overlaps(b) for a in self.time_slots for b in other.time_slots)


@dataclass
class Timetable:
    courses: list[Syllabus]
    total_credits: float
    requirement_fill: float  # 이 조합이 채우는 부족 졸업학점 합계 (정렬 기준)
    requirement_breakdown: dict[str, float]  # 교과영역별 채우는 학점


CALENDAR_SOURCE_TYPES = ["공지", "공모전", "행사", "시험일정"]


@dataclass
class CalendarEvent:
    title: str
    source_type: str  # "공지" | "공모전" | "행사" | "시험일정"
    date: str | None = None  # ISO "YYYY-MM-DD" — 문서에 실제 날짜가 명시된 경우
    week_number: int | None = None  # 강의계획서 주차만 명시된 경우 (예: "8주차 중간고사")
    time: str | None = None  # "HH:MM" (24시간), 없으면 종일 일정
    location: str = ""
    description: str = ""

    def resolved_date(self, semester_start: date | None) -> date | None:
        """실제 캘린더 날짜. date가 있으면 그대로, 없고 week_number + 학기 시작일이
        있으면 그로부터 계산, 둘 다 없으면 None(날짜 미확정)."""
        if self.date:
            return date.fromisoformat(self.date)
        if self.week_number is not None and semester_start is not None:
            return semester_start + timedelta(weeks=self.week_number - 1)
        return None
