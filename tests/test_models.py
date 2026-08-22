from core.models import CreditCategory, RequiredCourse, StudentProfile, TranscriptRecord


def make_profile(transcript, required_courses):
    return StudentProfile(
        department="컴공",
        year=3,
        transcript=transcript,
        requirements=[],
        required_courses=required_courses,
    )


def test_satisfied_by_code_direct_match():
    profile = make_profile(
        transcript=[TranscriptRecord("CSE201", "자료구조", 3, "A+", "2025-1", CreditCategory.전공필수)],
        required_courses=[RequiredCourse("CSE201", "자료구조", CreditCategory.전공필수, 3)],
    )
    rc = profile.required_courses[0]
    assert profile.satisfied_by_code(rc) == "CSE201"
    assert profile.missing_required_courses() == []


def test_satisfied_by_code_via_equivalent():
    profile = make_profile(
        transcript=[TranscriptRecord("CSE201", "자료구조", 3, "A+", "2025-1", CreditCategory.전공필수)],
        required_courses=[
            RequiredCourse("CSE201-02", "자료구조", CreditCategory.전공필수, 3, equivalent_codes=["CSE201"])
        ],
    )
    rc = profile.required_courses[0]
    assert profile.satisfied_by_code(rc) == "CSE201"
    assert profile.missing_required_courses() == []


def test_missing_required_course_when_not_taken():
    profile = make_profile(
        transcript=[],
        required_courses=[RequiredCourse("CSE305", "운영체제", CreditCategory.전공필수, 3)],
    )
    rc = profile.required_courses[0]
    assert profile.satisfied_by_code(rc) is None
    assert profile.missing_required_courses() == [rc]


def test_failed_course_does_not_satisfy_requirement():
    profile = make_profile(
        transcript=[TranscriptRecord("CSE305", "운영체제", 3, "F", "2025-1", CreditCategory.전공필수)],
        required_courses=[RequiredCourse("CSE305", "운영체제", CreditCategory.전공필수, 3)],
    )
    rc = profile.required_courses[0]
    assert profile.satisfied_by_code(rc) is None
    assert profile.missing_required_courses() == [rc]


def test_required_course_progress_tracks_filled_and_missing_per_category():
    profile = make_profile(
        transcript=[TranscriptRecord("CSE101", "프로그래밍입문", 3, "A+", "2025-1", CreditCategory.전공필수)],
        required_courses=[
            RequiredCourse("CSE101", "프로그래밍입문", CreditCategory.전공필수, 3),
            RequiredCourse("CSE305", "운영체제", CreditCategory.전공필수, 3),
            RequiredCourse("GEN101", "글쓰기", CreditCategory.필수교양, 2),
        ],
    )
    progress = profile.required_course_progress()
    assert progress[CreditCategory.전공필수] == {"filled": 3.0, "total": 6.0, "missing": 3.0}
    assert progress[CreditCategory.필수교양] == {"filled": 0.0, "total": 2.0, "missing": 2.0}
    assert CreditCategory.전공선택 not in progress


def test_required_course_progress_via_equivalent_counts_as_filled():
    profile = make_profile(
        transcript=[TranscriptRecord("CSE201", "자료구조", 3, "A+", "2025-1", CreditCategory.전공필수)],
        required_courses=[
            RequiredCourse("CSE201-02", "자료구조", CreditCategory.전공필수, 3, equivalent_codes=["CSE201"])
        ],
    )
    progress = profile.required_course_progress()
    assert progress[CreditCategory.전공필수] == {"filled": 3.0, "total": 3.0, "missing": 0.0}


def test_missing_required_courses_preserves_order_and_only_lists_unmet():
    profile = make_profile(
        transcript=[TranscriptRecord("A", "A과목", 3, "A+", "2025-1", CreditCategory.전공필수)],
        required_courses=[
            RequiredCourse("A", "A과목", CreditCategory.전공필수, 3),
            RequiredCourse("B", "B과목", CreditCategory.전공필수, 3),
            RequiredCourse("C", "C과목", CreditCategory.전공필수, 3),
        ],
    )
    missing = profile.missing_required_courses()
    assert [rc.course_code for rc in missing] == ["B", "C"]
