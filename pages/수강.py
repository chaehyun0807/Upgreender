import re

import pandas as pd
import streamlit as st

from core.config import has_upstage_key
from core.extraction import extract_syllabus
from core.models import CreditCategory, Syllabus, TimeSlot
from core.storage import add_syllabus, delete_syllabus, init_db, list_syllabi, seed_sample_syllabi, update_syllabus
from core.theme import inject_theme
from core.upstage_client import UpstageError, parse_document

st.set_page_config(page_title="수강", page_icon="🎓", layout="wide")
init_db()
inject_theme()

CATEGORY_VALUES = [c.value for c in CreditCategory]
DAY_VALUES = ["월", "화", "수", "목", "금", "토", "일"]
ATTENDANCE_VALUES = ["낮음", "보통", "높음"]

st.title("📊 강의계획서 비교 및 태그 필터링")

st.subheader("1. 강의계획서 등록")
tab_upload, tab_manual = st.tabs(["파일 업로드 (Upstage 자동 태깅)", "직접 입력"])

with tab_upload:
    if not has_upstage_key():
        st.info("UPSTAGE_API_KEY가 없으면 이 기능은 비활성화됩니다. '직접 입력' 탭이나 샘플 데이터를 사용하세요.")
    syllabus_files = st.file_uploader(
        "강의계획서 파일 (여러 개 선택 가능)",
        type=["pdf", "png", "jpg", "jpeg", "docx", "xlsx", "pptx"],
        accept_multiple_files=True,
        disabled=not has_upstage_key(),
    )
    if st.button("파싱 후 등록", disabled=not (has_upstage_key() and syllabus_files)):
        added = 0
        parsed_previews = []
        with st.spinner("Upstage로 강의계획서를 파싱하고 태깅하는 중..."):
            for f in syllabus_files:
                try:
                    markdown = parse_document(f.read(), f.name)
                    syllabus = extract_syllabus(markdown)
                    add_syllabus(syllabus)
                    added += 1
                    parsed_previews.append((f.name, markdown, syllabus))
                except UpstageError as e:
                    st.error(f"{f.name}: {e}")
        if added:
            st.success(f"{added}개 강의계획서를 등록했습니다.")
        for filename, markdown, syllabus in parsed_previews:
            with st.expander(f"🔍 {filename} — 파싱된 원문 및 추출 결과 확인"):
                st.caption("Upstage Document Parse가 실제로 뽑아낸 텍스트입니다. 추출 결과가 이상하면 여기서 원인을 확인하세요.")
                st.text_area("파싱된 원문", markdown, height=200, key=f"raw_{filename}")
                st.json(
                    {
                        "course_code": syllabus.course_code,
                        "course_name": syllabus.course_name,
                        "department": syllabus.department,
                        "professor": syllabus.professor,
                        "location": syllabus.location,
                        "credits": syllabus.credits,
                        "category": syllabus.category.value,
                        "team_project": syllabus.team_project,
                        "exam_types": syllabus.exam_types,
                        "attendance_intensity": syllabus.attendance_intensity,
                        "tags": syllabus.tags,
                    }
                )

with tab_manual:
    with st.form("manual_syllabus_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            course_code = st.text_input("과목코드")
            course_name = st.text_input("과목명")
            department = st.text_input("개설학과")
        with c2:
            credits = st.number_input("학점", min_value=0.0, step=0.5, value=3.0)
            category = st.selectbox("교과영역", CATEGORY_VALUES)
            professor = st.text_input("교수명")
        with c3:
            team_project = st.checkbox("팀 프로젝트 포함")
            exam_types_input = st.text_input("시험/평가 방식 (쉼표로 구분)", value="기말고사")
            attendance_intensity = st.selectbox("출석 강도", ATTENDANCE_VALUES, index=1)

        c4, c5 = st.columns(2)
        with c4:
            day = st.selectbox("요일", DAY_VALUES)
            start = st.number_input("시작 교시", min_value=1, max_value=14, value=1)
            end = st.number_input("종료 교시", min_value=1, max_value=14, value=2)
            location = st.text_input("장소 (예: 공학관 302호, 캠퍼스 지도 표시에 사용)")
        with c5:
            tags_input = st.text_input("태그 (쉼표로 구분)")
            year_restriction = st.number_input("수강 가능 최소 학년 (0=제한없음)", min_value=0, max_value=6, value=0)
            prereq_input = st.text_input("선수과목 코드 (쉼표로 구분)")

        allow_retake = st.checkbox("재수강 허용 과목")
        submitted = st.form_submit_button("강의계획서 추가")
        if submitted:
            if not course_code or not course_name:
                st.error("과목코드와 과목명은 필수입니다.")
            else:
                syllabus = Syllabus(
                    course_code=course_code,
                    course_name=course_name,
                    department=department,
                    credits=float(credits),
                    category=CreditCategory.from_str(category),
                    professor=professor,
                    time_slots=[TimeSlot(day=day, start=int(start), end=int(end))],
                    location=location,
                    team_project=team_project,
                    exam_types=[e.strip() for e in exam_types_input.split(",") if e.strip()] or ["기말고사"],
                    attendance_intensity=attendance_intensity,
                    tags=[t.strip() for t in tags_input.split(",") if t.strip()],
                    year_restriction=int(year_restriction) or None,
                    prerequisites=[p.strip() for p in prereq_input.split(",") if p.strip()],
                    allow_retake=allow_retake,
                )
                add_syllabus(syllabus)
                st.success(f"{course_name} 등록 완료")

if st.button("샘플 강의계획서 16개 불러오기 (데모용)"):
    n = seed_sample_syllabi()
    st.success(f"{n}개 추가했습니다." if n else "이미 모두 등록되어 있습니다.")

st.divider()
st.subheader("2. 비교표 및 태그 필터")

rows = list_syllabi()
if not rows:
    st.info("등록된 강의계획서가 없습니다. 위에서 등록하거나 샘플 데이터를 불러오세요.")
    st.stop()

df = pd.DataFrame(
    [
        {
            "id": sid,
            "과목코드": s.course_code,
            "과목명": s.course_name,
            "학과": s.department,
            "학점": s.credits,
            "교과영역": s.category.value,
            "교수": s.professor,
            "시간": ", ".join(f"{t.day}{t.start}-{t.end}" for t in s.time_slots),
            "장소": s.location or "-",
            "팀플": "예" if s.team_project else "아니오",
            "시험방식": ", ".join(s.exam_types),
            "출석강도": s.attendance_intensity,
            "태그": ", ".join(s.tags),
            "최소학년": f"{s.year_restriction}학년" if s.year_restriction else "제한없음",
        }
        for sid, s in rows
    ]
)

f1, f2, f3, f4 = st.columns(4)
with f1:
    sel_category = st.multiselect("교과영역", sorted(df["교과영역"].unique()))
with f2:
    sel_team = st.multiselect("팀플 여부", sorted(df["팀플"].unique()))
with f3:
    all_exam_types = sorted({e.strip() for exams in df["시험방식"] for e in exams.split(",") if e.strip()})
    sel_exam = st.multiselect("시험방식", all_exam_types)
with f4:
    sel_attendance = st.multiselect("출석강도", sorted(df["출석강도"].unique()))

all_tags = sorted({t.strip() for tags in df["태그"] for t in tags.split(",") if t.strip()})
sel_tags = st.multiselect("태그", all_tags)

filtered = df.copy()
if sel_category:
    filtered = filtered[filtered["교과영역"].isin(sel_category)]
if sel_team:
    filtered = filtered[filtered["팀플"].isin(sel_team)]
if sel_exam:
    filtered = filtered[
        filtered["시험방식"].apply(lambda t: any(e in [x.strip() for x in t.split(",")] for e in sel_exam))
    ]
if sel_attendance:
    filtered = filtered[filtered["출석강도"].isin(sel_attendance)]
if sel_tags:
    filtered = filtered[filtered["태그"].apply(lambda t: any(tag in [x.strip() for x in t.split(",")] for tag in sel_tags))]

st.dataframe(filtered.drop(columns=["id"]), width="stretch")

def _describe_syllabus_row(i: int) -> str:
    row = df.loc[df["id"] == i]
    if row.empty:
        return str(i)
    row = row.iloc[0]
    return f"{row['과목명']} ({row['과목코드']} · {row['교수']} · {row['시간']})"


def _format_time_slots(slots: list[TimeSlot]) -> str:
    return ", ".join(f"{t.day}{t.start}-{t.end}" for t in slots)


def _parse_time_slots(text: str) -> list[TimeSlot]:
    slots = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        m = re.match(r"^([월화수목금토일])\s*(\d+)\s*-\s*(\d+)$", token)
        if m:
            slots.append(TimeSlot(day=m.group(1), start=int(m.group(2)), end=int(m.group(3))))
    return slots


with st.expander("✏️ 강의계획서 수정"):
    if not len(filtered):
        st.caption("수정할 강의계획서가 없습니다.")
    else:
        edit_id = st.selectbox(
            "수정할 강의 (과목코드 · 교수 · 시간으로 구분)",
            options=filtered["id"].tolist(),
            format_func=_describe_syllabus_row,
            key="edit_select",
        )
        target = next(s for sid, s in rows if sid == edit_id)
        # 위젯 key에 edit_id를 넣어서, 수정 대상을 바꾸면 각 입력칸이 그 과목의 값으로 다시 초기화되게 한다.
        with st.form(f"edit_form_{edit_id}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                e_course_code = st.text_input("과목코드", value=target.course_code, key=f"e_code_{edit_id}")
                e_course_name = st.text_input("과목명", value=target.course_name, key=f"e_name_{edit_id}")
                e_department = st.text_input("개설학과", value=target.department, key=f"e_dept_{edit_id}")
            with c2:
                e_credits = st.number_input(
                    "학점", min_value=0.0, step=0.5, value=float(target.credits), key=f"e_credits_{edit_id}"
                )
                e_category = st.selectbox(
                    "교과영역", CATEGORY_VALUES, index=CATEGORY_VALUES.index(target.category.value),
                    key=f"e_cat_{edit_id}",
                )
                e_professor = st.text_input("교수명", value=target.professor, key=f"e_prof_{edit_id}")
            with c3:
                e_team_project = st.checkbox("팀 프로젝트 포함", value=target.team_project, key=f"e_team_{edit_id}")
                e_exam_types = st.text_input(
                    "시험/평가 방식 (쉼표로 구분)", value=", ".join(target.exam_types), key=f"e_exam_{edit_id}"
                )
                e_attendance = st.selectbox(
                    "출석 강도", ATTENDANCE_VALUES, index=ATTENDANCE_VALUES.index(target.attendance_intensity),
                    key=f"e_att_{edit_id}",
                )

            c4, c5 = st.columns(2)
            with c4:
                e_time_slots = st.text_input(
                    "강의시간 (요일+시작-종료, 쉼표로 구분. 예: 월1-2, 수1-2)",
                    value=_format_time_slots(target.time_slots),
                    key=f"e_time_{edit_id}",
                )
                e_location = st.text_input(
                    "장소 (예: 공학관 302호)", value=target.location, key=f"e_loc_{edit_id}"
                )
                e_year_restriction = st.number_input(
                    "수강 가능 최소 학년 (0=제한없음)", min_value=0, max_value=6,
                    value=target.year_restriction or 0, key=f"e_year_{edit_id}",
                )
            with c5:
                e_tags = st.text_input("태그 (쉼표로 구분)", value=", ".join(target.tags), key=f"e_tags_{edit_id}")
                e_prereq = st.text_input(
                    "선수과목 코드 (쉼표로 구분)", value=", ".join(target.prerequisites), key=f"e_prereq_{edit_id}"
                )

            e_allow_retake = st.checkbox("재수강 허용 과목", value=target.allow_retake, key=f"e_retake_{edit_id}")

            if st.form_submit_button("💾 수정 저장"):
                if not e_course_code or not e_course_name:
                    st.error("과목코드와 과목명은 필수입니다.")
                else:
                    updated = Syllabus(
                        course_code=e_course_code,
                        course_name=e_course_name,
                        department=e_department,
                        credits=float(e_credits),
                        category=CreditCategory.from_str(e_category),
                        professor=e_professor,
                        time_slots=_parse_time_slots(e_time_slots),
                        location=e_location,
                        team_project=e_team_project,
                        exam_types=[e.strip() for e in e_exam_types.split(",") if e.strip()] or ["기말고사"],
                        attendance_intensity=e_attendance,
                        tags=[t.strip() for t in e_tags.split(",") if t.strip()],
                        year_restriction=int(e_year_restriction) or None,
                        prerequisites=[p.strip() for p in e_prereq.split(",") if p.strip()],
                        allow_retake=e_allow_retake,
                    )
                    update_syllabus(int(edit_id), updated)
                    st.success(f"{e_course_name} 수정 완료")
                    st.rerun()

with st.expander("강의계획서 삭제"):
    delete_id = st.selectbox(
        "삭제할 강의 (과목코드 · 교수 · 시간으로 구분)",
        options=filtered["id"].tolist(),
        format_func=_describe_syllabus_row,
    ) if len(filtered) else None
    if delete_id is not None and st.button("삭제"):
        delete_syllabus(int(delete_id))
        st.rerun()
