"""Core recommendation engine.

Pipeline: hard filter (structurally impossible candidates) -> preference
filters (toggle/multiselect, no weights) -> time-conflict-free combination
search (DFS + pruning over course groups) -> sort by how much of the
remaining graduation requirement each combination fills.
"""
from __future__ import annotations

from core.models import StudentProfile, Syllabus, Timetable

DEFAULT_FILTERS = {
    "exclude_team_project": False,   # True면 팀 프로젝트 과목을 후보에서 제외
    "allowed_attendance": [],        # 비어있으면 전체 허용, 값이 있으면 그 출석강도만 허용
    "allowed_exam_types": [],        # 비어있으면 전체 허용, 값이 있으면 그 시험/평가 방식만 허용
    "only_remaining_requirements": False,  # True면 이미 다 채운 교과영역의 과목은 제외
}

# DFS 탐색이 지수적으로 폭발하지 않도록 두는 안전장치.
MAX_CANDIDATES_FOR_SEARCH = 18
NODE_BUDGET = 300_000


def hard_filter(profile: StudentProfile, candidates: list[Syllabus]) -> list[Syllabus]:
    """Drop candidates that are structurally impossible for this student,
    independent of any time-conflict or preference reasoning."""
    completed = profile.completed_course_codes
    allowed_departments = {profile.department, *profile.double_major_departments}

    filtered = []
    for course in candidates:
        if course.course_code in completed and not course.allow_retake:
            continue
        if course.year_restriction is not None and profile.year < course.year_restriction:
            continue
        if course.category.value.startswith("전공") and course.department not in allowed_departments:
            continue
        missing_prereqs = [p for p in course.prerequisites if p not in completed]
        if missing_prereqs:
            continue
        filtered.append(course)
    return filtered


def apply_preference_filters(
    profile: StudentProfile, candidates: list[Syllabus], filters: dict
) -> list[Syllabus]:
    """User-selected filters — a course either matches or is dropped. No scoring."""
    remaining = profile.remaining_credits_by_category()
    allowed_attendance = filters.get("allowed_attendance") or []
    allowed_exam_types = filters.get("allowed_exam_types") or []

    filtered = []
    for course in candidates:
        if filters.get("exclude_team_project") and course.team_project:
            continue
        if allowed_attendance and course.attendance_intensity not in allowed_attendance:
            continue
        if allowed_exam_types and not set(course.exam_types) & set(allowed_exam_types):
            continue
        if filters.get("only_remaining_requirements") and remaining.get(course.category, 0.0) <= 0:
            continue
        filtered.append(course)
    return filtered


def _group_by_course_code(courses: list[Syllabus]) -> list[list[Syllabus]]:
    groups: dict[str, list[Syllabus]] = {}
    for course in courses:
        groups.setdefault(course.course_code, []).append(course)
    return list(groups.values())


def _search_combinations(
    groups: list[list[Syllabus]], max_credits: float, node_budget: int = NODE_BUDGET
) -> list[list[Syllabus]]:
    """DFS over course groups: at each group, either skip it or pick one of
    its section alternatives, pruning on credit cap and time conflicts."""
    results: list[list[Syllabus]] = []
    nodes = 0

    def backtrack(idx: int, selected: list[Syllabus], total_credits: float) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > node_budget:
            return
        if idx == len(groups):
            if selected:
                results.append(list(selected))
            return

        backtrack(idx + 1, selected, total_credits)  # skip this course entirely

        for section in groups[idx]:
            if total_credits + section.credits > max_credits:
                continue
            if any(section.overlaps(chosen) for chosen in selected):
                continue
            selected.append(section)
            backtrack(idx + 1, selected, total_credits + section.credits)
            selected.pop()

    backtrack(0, [], 0.0)
    return results


def _requirement_fill(courses: list[Syllabus], profile: StudentProfile) -> tuple[float, dict[str, float]]:
    """How many of the student's remaining required credits this combination
    fills, broken down by category. Used purely as a sort key — not a score."""
    remaining = profile.remaining_credits_by_category()
    breakdown: dict[str, float] = {}
    for course in courses:
        filled = min(course.credits, remaining.get(course.category, 0.0))
        if filled > 0:
            breakdown[course.category.value] = breakdown.get(course.category.value, 0.0) + filled
    return sum(breakdown.values()), breakdown


def recommend_timetables(
    profile: StudentProfile,
    candidates: list[Syllabus],
    filters: dict,
    max_credits: float,
    top_n: int = 5,
) -> list[Timetable]:
    filtered = hard_filter(profile, candidates)
    filtered = apply_preference_filters(profile, filtered, filters)
    if not filtered:
        return []

    remaining = profile.remaining_credits_by_category()
    filtered.sort(key=lambda c: min(c.credits, remaining.get(c.category, 0.0)), reverse=True)
    capped = filtered[:MAX_CANDIDATES_FOR_SEARCH]

    groups = _group_by_course_code(capped)
    combos = _search_combinations(groups, max_credits)

    timetables = []
    for combo in combos:
        if not combo:
            continue
        fill, breakdown = _requirement_fill(combo, profile)
        timetables.append(
            Timetable(
                courses=combo,
                total_credits=sum(c.credits for c in combo),
                requirement_fill=fill,
                requirement_breakdown=breakdown,
            )
        )
    timetables.sort(key=lambda t: t.requirement_fill, reverse=True)
    return timetables[:top_n]
