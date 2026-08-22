import json

import core.storage as storage
from core.models import CreditCategory, CreditRequirement, RequiredCourse, StudentProfile, Syllabus, TimeSlot, TranscriptRecord
from core.storage import _profile_from_dict, _profile_to_dict, _syllabus_from_dict, _syllabus_to_dict


def test_profile_json_round_trip_with_required_courses():
    profile = StudentProfile(
        department="컴공",
        year=3,
        transcript=[TranscriptRecord("CSE201", "자료구조", 3, "A+", "2025-1", CreditCategory.전공필수)],
        requirements=[CreditRequirement(CreditCategory.전공필수, 9)],
        required_courses=[
            RequiredCourse(
                "CSE201-02", "자료구조", CreditCategory.전공필수, 3, equivalent_codes=["CSE201"], note="비고"
            )
        ],
        double_major_departments=["철학과"],
    )

    # 실제 DB 대신 (역)직렬화만 검증 — JSON을 왕복시켜도 값이 그대로 복원되는지 확인
    as_json = json.dumps(_profile_to_dict(profile), ensure_ascii=False)
    restored = _profile_from_dict(json.loads(as_json))

    assert restored.department == "컴공"
    assert restored.double_major_departments == ["철학과"]
    assert restored.required_courses[0].course_code == "CSE201-02"
    assert restored.required_courses[0].equivalent_codes == ["CSE201"]
    assert restored.required_courses[0].note == "비고"
    assert restored.satisfied_by_code(restored.required_courses[0]) == "CSE201"


def test_selected_timetable_json_round_trip():
    courses = [
        Syllabus(
            "CSE201", "자료구조", "컴공", 3, CreditCategory.전공필수, "김도현",
            time_slots=[TimeSlot("월", 1, 2), TimeSlot("수", 1, 2)],
        ),
        Syllabus("CSE305", "운영체제", "컴공", 3, CreditCategory.전공필수, "이서연", time_slots=[TimeSlot("화", 3, 4)]),
    ]
    as_json = json.dumps([_syllabus_to_dict(c) for c in courses], ensure_ascii=False)
    restored = [_syllabus_from_dict(d) for d in json.loads(as_json)]
    assert [c.course_code for c in restored] == ["CSE201", "CSE305"]
    assert restored[0].time_slots[0].day == "월"


def test_syllabus_round_trip_preserves_location():
    course = Syllabus(
        "CSE201", "자료구조", "컴공", 3, CreditCategory.전공필수, "김도현",
        time_slots=[TimeSlot("월", 1, 2)], location="공학관 301호",
    )
    restored = _syllabus_from_dict(json.loads(json.dumps(_syllabus_to_dict(course), ensure_ascii=False)))
    assert restored.location == "공학관 301호"


def test_load_selected_timetable_refreshes_from_catalog(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    storage.init_db()

    course = Syllabus("CSE201", "자료구조", "컴공", 3, CreditCategory.전공필수, "김도현", time_slots=[])
    syllabus_id = storage.add_syllabus(course)
    storage.save_selected_timetable([course])

    # 저장 시점엔 시간이 비어 있었지만, 이후 카탈로그에서 과목을 수정하면
    assert storage.load_selected_timetable()[0].time_slots == []

    updated = Syllabus(
        "CSE201", "자료구조", "컴공", 3, CreditCategory.전공필수, "김도현", time_slots=[TimeSlot("월", 1, 3)]
    )
    storage.update_syllabus(syllabus_id, updated)

    # '내 시간표'를 다시 불러오면 스냅샷이 아니라 최신 카탈로그 값을 반영해야 한다
    refreshed = storage.load_selected_timetable()
    assert refreshed[0].time_slots == [TimeSlot("월", 1, 3)]


def test_load_selected_timetable_keeps_snapshot_if_deleted_from_catalog(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    storage.init_db()

    course = Syllabus("CSE201", "자료구조", "컴공", 3, CreditCategory.전공필수, "김도현", time_slots=[TimeSlot("월", 1, 2)])
    syllabus_id = storage.add_syllabus(course)
    storage.save_selected_timetable([course])
    storage.delete_syllabus(syllabus_id)

    # 카탈로그에서 지워졌어도 '내 시간표'에 저장된 스냅샷은 그대로 남아있어야 한다
    refreshed = storage.load_selected_timetable()
    assert refreshed[0].course_code == "CSE201"
    assert refreshed[0].time_slots == [TimeSlot("월", 1, 2)]


def test_geocode_cache_round_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    storage.init_db()

    assert storage.get_cached_coords("공학관") is None
    storage.set_cached_coords("공학관", 36.0138, 129.3435, matched_query="공학관")
    assert storage.get_cached_coords("공학관") == (36.0138, 129.3435, "공학관")

    storage.set_cached_coords("공학관", 37.0, 128.0, matched_query="동아대학교")
    assert storage.get_cached_coords("공학관") == (37.0, 128.0, "동아대학교")
