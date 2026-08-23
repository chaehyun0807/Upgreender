"""Prompt templates + JSON-schema definitions used to turn Upstage-parsed
document text into our structured dataclasses (transcript, graduation
requirements, syllabus)."""
from __future__ import annotations

from core.models import CalendarEvent, CreditCategory, CreditRequirement, RequiredCourse, Syllabus, TimeSlot, TranscriptRecord
from core.upstage_client import chat_json

CATEGORY_VALUES = [c.value for c in CreditCategory]
DAY_VALUES = ["월", "화", "수", "목", "금", "토", "일"]
ATTENDANCE_VALUES = ["낮음", "보통", "높음"]

TRANSCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "records": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "course_code": {"type": "string"},
                    "course_name": {"type": "string"},
                    "credits": {"type": "number"},
                    "grade": {"type": "string"},
                    "semester": {"type": "string"},
                    "category": {"type": "string", "enum": CATEGORY_VALUES},
                },
                "required": ["course_code", "course_name", "credits", "grade", "semester", "category"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["records"],
    "additionalProperties": False,
}

CREDIT_REQUIREMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": CATEGORY_VALUES},
                    "required_credits": {"type": "number"},
                },
                "required": ["category", "required_credits"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["requirements"],
    "additionalProperties": False,
}

SYLLABUS_SCHEMA = {
    "type": "object",
    "properties": {
        "course_code": {"type": "string"},
        "course_name": {"type": "string"},
        "department": {"type": "string"},
        "credits": {"type": "number"},
        "category": {"type": "string", "enum": CATEGORY_VALUES},
        "professor": {"type": "string"},
        "time_slots": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "string", "enum": DAY_VALUES},
                    "start": {"type": "integer"},
                    "end": {"type": "integer"},
                },
                "required": ["day", "start", "end"],
                "additionalProperties": False,
            },
        },
        "location": {"type": "string"},
        "team_project": {"type": "boolean"},
        "exam_types": {"type": "array", "items": {"type": "string"}},
        "attendance_intensity": {"type": "string", "enum": ATTENDANCE_VALUES},
        "tags": {"type": "array", "items": {"type": "string"}},
        "year_restriction": {"type": ["integer", "null"]},
        "prerequisites": {"type": "array", "items": {"type": "string"}},
        "allow_retake": {"type": "boolean"},
    },
    "required": [
        "course_code", "course_name", "department", "credits", "category", "professor",
        "time_slots", "location", "team_project", "exam_types", "attendance_intensity", "tags",
        "year_restriction", "prerequisites", "allow_retake",
    ],
    "additionalProperties": False,
}

REQUIRED_COURSE_SCHEMA = {
    "type": "object",
    "properties": {
        "required_courses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "course_code": {"type": "string"},
                    "course_name": {"type": "string"},
                    "category": {"type": "string", "enum": CATEGORY_VALUES},
                    "credits": {"type": "number"},
                    "equivalent_codes": {"type": "array", "items": {"type": "string"}},
                    "note": {"type": "string"},
                },
                "required": ["course_code", "course_name", "category", "credits", "equivalent_codes", "note"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["required_courses"],
    "additionalProperties": False,
}

_TRANSCRIPT_PROMPT = f"""당신은 대학교 성적표를 구조화된 데이터로 변환하는 도우미입니다.
주어진 성적표 텍스트에서 수강한 모든 과목을 추출하세요.
category는 반드시 다음 중 하나여야 합니다: {', '.join(CATEGORY_VALUES)}.
원문에 정확히 일치하는 분류명이 없으면 의미상 가장 가까운 값을 고르세요.
grade는 원문에 표기된 그대로(A+, B0, P, F 등) 넣으세요."""

_CREDIT_REQUIREMENT_PROMPT = f"""당신은 대학교 졸업이수학점표/졸업조건 문서를 구조화된 데이터로 변환하는 도우미입니다.
문서에서 교과영역별 요구 이수학점을 추출하세요.
category는 반드시 다음 중 하나여야 합니다: {', '.join(CATEGORY_VALUES)}.
'합계' 행은 제외하고 각 영역별 값만 추출하세요."""

_SYLLABUS_PROMPT = f"""당신은 대학교 강의계획서를 구조화된 데이터로 변환하는 도우미입니다.
아래 강의계획서 텍스트에 실제로 적힌 내용만 근거로 필드를 채우세요. 문서에 없는 내용을 추측해서 지어내지 마세요.
- course_code, course_name, professor, credits: 문서 상단의 기본 정보(예: "교과목번호"/"학수번호"/"과목코드",
  "교과목명"/"과목명", "담당교수"/"교수명", "학점" 같은 라벨) 옆에 적힌 값을 원문 표기 그대로 옮기세요.
  약어로 축약하거나 번역하거나 다른 표기로 바꾸지 마세요.
- department: 반드시 "개설학과", "학과", "소속학과"라는 라벨이 명시적으로 있고 그 옆에 학과 이름(예:
  "컴퓨터공학과")이 적혀 있을 때만 그 값을 사용하세요. 그런 라벨 자체가 문서에 없으면 절대로 과목코드,
  분반, 다른 숫자/코드값을 대신 넣지 말고 반드시 빈 문자열("")로 두세요. 문서에 없는 값을 추측해서
  채우는 것보다 빈 문자열이 항상 낫습니다.
- category는 다음 중 하나: {', '.join(CATEGORY_VALUES)}
- time_slots.day는 다음 중 하나: {', '.join(DAY_VALUES)}, start/end는 교시(정수). 요일과 교시가 명시된
  강의시간표가 문서에 없으면 빈 배열로 두세요.
- location: 강의실/건물 위치가 "공학관 302호", "본관 401"처럼 명시되어 있으면 그대로 옮기세요. 없으면
  빈 문자열로 두세요. 추측하지 마세요.
- team_project: 문서에 "팀 프로젝트", "조별과제", "그룹 프로젝트", "팀별 발표"처럼 여러 명이 한 조를 이루어
  함께 수행하고 그 결과로 평가받는 과제/활동이 명시적으로 적혀 있을 때만 true로 판단하세요.
  "토론", "실습", "실험", "발표"라는 단어가 있다고 해서 true로 판단하지 마세요 — 이런 단어들은 개인별
  활동일 수도 있으므로 그 자체만으로는 팀플의 근거가 되지 않습니다. 평가 항목(출석/과제/시험 비율표
  등)에 "팀", "조별", "그룹"이라는 말이 실제로 없으면 false로 두세요.
- exam_types: 문서에 적힌 시험/평가 방식을 모두 배열로 나열한다 (예: 중간고사와 기말고사가 둘 다 있으면
  ["중간고사", "기말고사"]). 명시된 항목만 각각 하나의 원소로 넣고, 하나로 뭉뚱그려 요약하지 마세요
  (예: "퀴즈"와 "과제"가 각각 있으면 ["퀴즈", "과제"]). 아무 언급이 없으면 ["기말고사"]로 둔다.
- attendance_intensity: 문서에 출석 관련 언급(출석 점수 비율, 결석 허용 횟수 등)이 있을 때만 그 강도를
  {', '.join(ATTENDANCE_VALUES)} 중 하나로 판단하고, 언급이 없으면 "보통"으로 둔다.
- tags: 문서에서 실제로 확인되는 특징만 짧은 한글 단어로 나열한다. 아래는 태그 "이름 형식"의 예시일 뿐이며,
  문서에 해당 내용이 없으면 절대 붙이지 않는다: "팀플", "비대면", "출석엄격", "시험없음" 등은 그런 내용이
  문서에 실제로 있을 때만 사용하는 이름표다. 확인되는 특징이 없으면 빈 배열로 둔다.
- year_restriction: 특정 학년 이상만 수강 가능하다고 명시되어 있으면 그 학년(정수), 없으면 null
- prerequisites: 선수과목으로 명시된 과목 코드 목록, 없으면 빈 배열
- allow_retake: 재수강 허용이라고 명시되어 있으면 true, 명시 없으면 false
근거가 부족한 항목은 항상 보수적인 기본값(false, "보통", ["기말고사"], 빈 배열, null)을 사용하세요."""


DOCUMENT_TYPE_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string", "enum": ["성적표", "이수학점표", "학사편람"]},
    },
    "required": ["document_type"],
    "additionalProperties": False,
}

_CLASSIFY_PROMPT = """당신은 대학교 행정 문서를 세 종류 중 하나로 분류하는 도우미입니다.
- 성적표: 학생 개인이 실제로 수강하고 취득한 과목별 성적(A+, B0, P 등)과 학기가 나열된 문서
- 이수학점표: 졸업을 위해 교과영역(전공필수/전공선택/교양 등)별로 몇 학점을 이수해야 하는지 요구 학점
  기준표. 개인의 성적/취득 학점이 아니라 "요구 학점" 기준만 나열되어 있다.
- 학사편람: 학과별 전공필수/필수교양 등 반드시 들어야 하는 특정 과목 목록과 대체과목 규정이 나열된
  교육과정 편람 문서
문서 내용을 읽고 셋 중 가장 알맞은 하나를 고르세요."""


def classify_document(markdown_text: str) -> str:
    data = chat_json(_CLASSIFY_PROMPT, markdown_text, DOCUMENT_TYPE_SCHEMA, "document_type")
    return data["document_type"]


def extract_transcript(markdown_text: str) -> list[TranscriptRecord]:
    data = chat_json(_TRANSCRIPT_PROMPT, markdown_text, TRANSCRIPT_SCHEMA, "transcript")
    return [
        TranscriptRecord(
            course_code=r["course_code"],
            course_name=r["course_name"],
            credits=float(r["credits"]),
            grade=r["grade"],
            semester=r["semester"],
            category=CreditCategory.from_str(r["category"]),
        )
        for r in data["records"]
    ]


def extract_credit_requirements(markdown_text: str) -> list[CreditRequirement]:
    data = chat_json(_CREDIT_REQUIREMENT_PROMPT, markdown_text, CREDIT_REQUIREMENT_SCHEMA, "credit_requirement")
    return [
        CreditRequirement(
            category=CreditCategory.from_str(r["category"]),
            required_credits=float(r["required_credits"]),
        )
        for r in data["requirements"]
    ]


_REQUIRED_COURSE_PROMPT = f"""당신은 대학교 학사편람(교육과정 편람)에서 필수과목 목록을 구조화된 데이터로
변환하는 도우미입니다. 문서에 실제로 나열된 과목만 추출하고, 없는 내용을 지어내지 마세요.
- "필수", "전공필수", "필수교양"처럼 반드시 이수해야 한다고 명시된 과목만 포함하세요. 선택과목/권장과목은
  제외하세요.
- category는 다음 중 하나: {', '.join(CATEGORY_VALUES)}
- credits: 문서에 적힌 학점 그대로
- equivalent_codes: 비고란에 "OOO 과목으로 대체 가능", "OOO와 동일 과목", "구 교육과정의 OOO" 등으로
  대체/동등 과목이 명시적으로 언급된 경우에만 그 과목 코드를 넣으세요. 문서에 그런 언급이 없으면 반드시
  빈 배열로 두세요. 절대 추측하지 마세요.
- note: 비고란에 적힌 원문을 그대로 옮기세요. 없으면 빈 문자열.
근거가 부족한 항목은 항상 보수적으로(빈 배열, 빈 문자열) 처리하세요."""


def extract_required_courses(markdown_text: str) -> list[RequiredCourse]:
    data = chat_json(_REQUIRED_COURSE_PROMPT, markdown_text, REQUIRED_COURSE_SCHEMA, "required_courses")
    return [
        RequiredCourse(
            course_code=r["course_code"],
            course_name=r["course_name"],
            category=CreditCategory.from_str(r["category"]),
            credits=float(r["credits"]),
            equivalent_codes=r["equivalent_codes"],
            note=r["note"],
        )
        for r in data["required_courses"]
    ]


def syllabus_from_agent_output(data: dict) -> Syllabus:
    """Studio 에이전트(강의계획서 Extract 브랜치)가 만든 JSON을 Syllabus로 변환한다.
    year_restriction: Studio의 Integer 필드 제약 때문에 '제한없음'이 0으로 온다 -> None으로 변환."""
    year_restriction = data.get("year_restriction")
    if not year_restriction:
        year_restriction = None
    return Syllabus(
        course_code=data["course_code"],
        course_name=data["course_name"],
        department=data.get("department", ""),
        credits=float(data["credits"]),
        category=CreditCategory.from_str(data["category"]),
        professor=data.get("professor", ""),
        time_slots=[TimeSlot(day=t["day"], start=t["start"], end=t["end"]) for t in data.get("time_slots", [])],
        location=data.get("location", ""),
        team_project=bool(data.get("team_project", False)),
        exam_types=data.get("exam_types") or ["기말고사"],
        attendance_intensity=data.get("attendance_intensity", "보통"),
        tags=data.get("tags", []),
        year_restriction=year_restriction,
        prerequisites=data.get("prerequisites", []),
        allow_retake=bool(data.get("allow_retake", False)),
    )


def extract_syllabus(markdown_text: str) -> Syllabus:
    d = chat_json(_SYLLABUS_PROMPT, markdown_text, SYLLABUS_SCHEMA, "syllabus")
    return Syllabus(
        course_code=d["course_code"],
        course_name=d["course_name"],
        department=d["department"],
        credits=float(d["credits"]),
        category=CreditCategory.from_str(d["category"]),
        professor=d["professor"],
        time_slots=[TimeSlot(day=t["day"], start=t["start"], end=t["end"]) for t in d["time_slots"]],
        location=d["location"],
        team_project=d["team_project"],
        exam_types=d["exam_types"],
        attendance_intensity=d["attendance_intensity"],
        tags=d["tags"],
        year_restriction=d["year_restriction"],
        prerequisites=d["prerequisites"],
        allow_retake=d["allow_retake"],
    )


CALENDAR_EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "date": {"type": ["string", "null"]},
                    "week_number": {"type": ["integer", "null"]},
                    "time": {"type": ["string", "null"]},
                    "location": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["title", "date", "week_number", "time", "location", "description"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["events"],
    "additionalProperties": False,
}

_CALENDAR_PROMPT_COMMON = """문서에 실제로 적힌 일정만 추출하세요. 없는 내용을 지어내지 마세요.
- title: 일정 제목. 가능하면 과목명/행사명 등 맥락을 포함해 구체적으로 작성하세요 (예: "운영체제 중간고사").
- date: 문서에 연/월/일이 모두 명시된 경우에만 "YYYY-MM-DD" 형식으로 채우세요. 연도가 빠져 있으면
  문서 상단에 적힌 작성일/공고일의 연도를 사용하세요. 그마저 알 수 없으면 null로 두세요.
- week_number: date를 채우지 못했고 "8주차"처럼 주차만 명시된 경우에만 그 정수를 넣으세요. 그 외에는 null.
- time: "HH:MM"(24시간) 형식. 시각이 없으면 null.
- location: 장소가 명시되어 있으면 그대로, 없으면 빈 문자열.
- description: 일정에 대한 간단한 부가 설명(신청 방법, 대상 등). 없으면 빈 문자열.
날짜/주차 정보가 전혀 없는 항목은 결과에 포함하지 마세요."""

_CALENDAR_PROMPTS = {
    "공지": f"""당신은 대학교 공지사항 문서에서 일정을 추출하는 도우미입니다.
신청 마감일, 발표일, 시행일처럼 날짜가 명시된 항목을 모두 찾으세요.
{_CALENDAR_PROMPT_COMMON}""",
    "공모전": f"""당신은 공모전/대회 안내 문서에서 일정을 추출하는 도우미입니다.
접수 마감일, 결과 발표일, 시상식 일정 등을 모두 찾으세요.
{_CALENDAR_PROMPT_COMMON}""",
    "행사": f"""당신은 학교 행사 안내 문서에서 일정을 추출하는 도우미입니다.
행사 일시(시작/종료), 장소를 찾으세요. 여러 날에 걸친 행사면 날짜별로 각각 항목을 만드세요.
{_CALENDAR_PROMPT_COMMON}""",
    "시험일정": f"""당신은 대학교 강의계획서에서 시험/과제 마감 일정을 추출하는 도우미입니다.
주별 수업계획표에서 "중간고사", "기말고사", "과제 제출"처럼 평가와 관련된 항목만 찾으세요. 일반 수업
내용(예: "1장 소개")은 제외하세요. 실제 달력 날짜가 적혀 있으면 date를, 주차만 적혀 있으면(예: "8주차")
week_number를 채우세요.
{_CALENDAR_PROMPT_COMMON}""",
}


def extract_calendar_events(markdown_text: str, source_type: str) -> list[CalendarEvent]:
    prompt = _CALENDAR_PROMPTS.get(source_type, _CALENDAR_PROMPTS["공지"])
    data = chat_json(prompt, markdown_text, CALENDAR_EVENT_SCHEMA, "calendar_events")
    return [
        CalendarEvent(
            title=e["title"],
            source_type=source_type,
            date=e["date"],
            week_number=e["week_number"],
            time=e["time"],
            location=e["location"],
            description=e["description"],
        )
        for e in data["events"]
    ]
