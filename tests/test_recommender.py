from core.models import CreditCategory, CreditRequirement, StudentProfile, Syllabus, TimeSlot, TranscriptRecord
from core.recommender import DEFAULT_FILTERS, apply_preference_filters, hard_filter, recommend_timetables


def make_syllabus(code, category=CreditCategory.전공선택, credits=3, day="월", start=1, end=2, department="컴공", **kwargs):
    return Syllabus(
        course_code=code,
        course_name=f"과목-{code}",
        department=department,
        credits=credits,
        category=category,
        professor="교수",
        time_slots=[TimeSlot(day=day, start=start, end=end)],
        **kwargs,
    )


def make_profile(**kwargs):
    defaults = dict(
        department="컴공",
        year=3,
        transcript=[],
        requirements=[CreditRequirement(category=CreditCategory.전공선택, required_credits=9)],
    )
    defaults.update(kwargs)
    return StudentProfile(**defaults)


def test_hard_filter_excludes_completed_course():
    profile = make_profile(
        transcript=[TranscriptRecord("CSE201", "자료구조", 3, "A+", "2025-1", CreditCategory.전공필수)]
    )
    candidates = [make_syllabus("CSE201", category=CreditCategory.전공필수), make_syllabus("CSE305")]
    filtered = hard_filter(profile, candidates)
    codes = {c.course_code for c in filtered}
    assert "CSE201" not in codes
    assert "CSE305" in codes


def test_hard_filter_allows_retake():
    profile = make_profile(
        transcript=[TranscriptRecord("CSE201", "자료구조", 3, "F", "2025-1", CreditCategory.전공필수)]
    )
    candidates = [make_syllabus("CSE201", category=CreditCategory.전공필수, allow_retake=True)]
    filtered = hard_filter(profile, candidates)
    assert "CSE201" in {c.course_code for c in filtered}


def test_hard_filter_excludes_wrong_department_major():
    profile = make_profile(department="컴공")
    candidates = [make_syllabus("PHIL101", category=CreditCategory.전공선택, department="철학과")]
    filtered = hard_filter(profile, candidates)
    assert filtered == []


def test_hard_filter_excludes_year_restriction():
    profile = make_profile(year=1)
    candidates = [make_syllabus("CSE480", year_restriction=4)]
    filtered = hard_filter(profile, candidates)
    assert filtered == []


def test_hard_filter_excludes_missing_prerequisite():
    profile = make_profile(transcript=[])
    candidates = [make_syllabus("CSE305", prerequisites=["CSE201"])]
    assert hard_filter(profile, candidates) == []


def test_filter_excludes_team_project():
    profile = make_profile()
    candidates = [make_syllabus("A1", team_project=True), make_syllabus("A2", team_project=False)]
    filtered = apply_preference_filters(profile, candidates, {**DEFAULT_FILTERS, "exclude_team_project": True})
    codes = {c.course_code for c in filtered}
    assert codes == {"A2"}


def test_filter_allowed_attendance():
    profile = make_profile()
    candidates = [
        make_syllabus("A1", attendance_intensity="낮음"),
        make_syllabus("A2", attendance_intensity="높음"),
    ]
    filtered = apply_preference_filters(profile, candidates, {**DEFAULT_FILTERS, "allowed_attendance": ["낮음"]})
    codes = {c.course_code for c in filtered}
    assert codes == {"A1"}


def test_filter_allowed_exam_types():
    profile = make_profile()
    candidates = [
        make_syllabus("A1", exam_types=["과제대체"]),
        make_syllabus("A2", exam_types=["기말고사"]),
    ]
    filtered = apply_preference_filters(profile, candidates, {**DEFAULT_FILTERS, "allowed_exam_types": ["과제대체"]})
    codes = {c.course_code for c in filtered}
    assert codes == {"A1"}


def test_filter_allowed_exam_types_matches_any_of_multiple():
    profile = make_profile()
    candidates = [
        make_syllabus("A1", exam_types=["중간고사", "기말고사"]),
        make_syllabus("A2", exam_types=["퀴즈"]),
    ]
    filtered = apply_preference_filters(profile, candidates, {**DEFAULT_FILTERS, "allowed_exam_types": ["중간고사"]})
    codes = {c.course_code for c in filtered}
    assert codes == {"A1"}


def test_filter_only_remaining_requirements():
    profile = make_profile(requirements=[CreditRequirement(category=CreditCategory.전공선택, required_credits=3)])
    candidates = [
        make_syllabus("A1", category=CreditCategory.전공선택),  # 부족 영역 -> 남음
        make_syllabus("A2", category=CreditCategory.일반선택),  # 요건 없음 -> 제외 대상
    ]
    filtered = apply_preference_filters(profile, candidates, {**DEFAULT_FILTERS, "only_remaining_requirements": True})
    codes = {c.course_code for c in filtered}
    assert codes == {"A1"}


def test_empty_filters_allow_everything():
    profile = make_profile()
    candidates = [make_syllabus("A1", team_project=True, attendance_intensity="높음", exam_types=["기말고사"])]
    filtered = apply_preference_filters(profile, candidates, DEFAULT_FILTERS)
    assert {c.course_code for c in filtered} == {"A1"}


def test_recommend_never_returns_time_conflicts():
    profile = make_profile()
    candidates = [
        make_syllabus("A1", day="월", start=1, end=2),
        make_syllabus("A2", day="월", start=2, end=3),  # overlaps with A1
        make_syllabus("A3", day="화", start=1, end=2),
    ]
    results = recommend_timetables(profile, candidates, DEFAULT_FILTERS, max_credits=18, top_n=10)
    for tt in results:
        for i, c1 in enumerate(tt.courses):
            for c2 in tt.courses[i + 1:]:
                assert not c1.overlaps(c2)


def test_recommend_respects_credit_cap():
    profile = make_profile()
    candidates = [make_syllabus(f"C{i}", day="월", start=i, end=i, credits=3) for i in range(1, 6)]
    results = recommend_timetables(profile, candidates, DEFAULT_FILTERS, max_credits=7, top_n=20)
    for tt in results:
        assert tt.total_credits <= 7


def test_recommend_sorts_by_requirement_fill_descending():
    profile = make_profile(requirements=[CreditRequirement(category=CreditCategory.전공선택, required_credits=3)])
    filling = make_syllabus("FILL", category=CreditCategory.전공선택, day="월", start=1, end=2, credits=3)
    non_filling = make_syllabus("OTHER", category=CreditCategory.일반선택, day="화", start=1, end=2, credits=3)
    results = recommend_timetables(profile, [filling, non_filling], DEFAULT_FILTERS, max_credits=3, top_n=10)
    assert results[0].courses[0].course_code == "FILL"
    assert results[0].requirement_fill >= results[-1].requirement_fill


def test_recommend_respects_preference_filters():
    profile = make_profile()
    team_course = make_syllabus("TEAM", team_project=True, day="월", start=1, end=2)
    solo_course = make_syllabus("SOLO", team_project=False, day="화", start=1, end=2)
    results = recommend_timetables(
        profile, [team_course, solo_course], {**DEFAULT_FILTERS, "exclude_team_project": True}, max_credits=18, top_n=10
    )
    for tt in results:
        assert all(not c.team_project for c in tt.courses)


def test_recommend_returns_empty_when_all_candidates_filtered_out():
    profile = make_profile(year=1)
    candidates = [make_syllabus("HIGH", year_restriction=4)]
    results = recommend_timetables(profile, candidates, DEFAULT_FILTERS, max_credits=18, top_n=5)
    assert results == []
