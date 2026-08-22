import pandas as pd
import streamlit as st

from core.config import has_upstage_key
from core.extraction import classify_document, extract_credit_requirements, extract_required_courses, extract_transcript
from core.models import CreditCategory, CreditRequirement, RequiredCourse, StudentProfile, TranscriptRecord
from core.storage import init_db, list_syllabi, load_profile, load_sample_profile, save_profile, seed_sample_syllabi
from core.theme import inject_theme
from core.upstage_client import UpstageError, parse_document

st.set_page_config(page_title="성적표 업로드", page_icon="📄", layout="wide")
init_db()
inject_theme()

CATEGORY_VALUES = [c.value for c in CreditCategory]

# 아래 위젯들은 명시적 key를 가진다. 파싱/샘플 불러오기 등으로 값을 "프로그램에서" 바꿀 때는
# 이 key를 session_state에서 지운 뒤 st.rerun()해야 위젯이 새 값으로 다시 초기화된다.
# (Streamlit은 위젯이 한 번 렌더링되면 이후에는 value= 인자를 무시하고 자체 저장된 값을 우선한다.)
WIDGET_KEYS = [
    "name_input",
    "department_input",
    "year_input",
    "double_major_input",
    "transcript_editor",
    "requirement_editor",
    "required_course_editor",
]


def _transcript_records_to_df(records: list[TranscriptRecord]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "course_code": r.course_code,
                "course_name": r.course_name,
                "credits": r.credits,
                "grade": r.grade,
                "semester": r.semester,
                "category": r.category.value,
            }
            for r in records
        ]
    )


def _requirements_to_df(requirements: list[CreditRequirement]) -> pd.DataFrame:
    return pd.DataFrame([{"category": r.category.value, "required_credits": r.required_credits} for r in requirements])


def _required_courses_to_df(required_courses: list[RequiredCourse]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "course_code": rc.course_code,
                "course_name": rc.course_name,
                "category": rc.category.value,
                "credits": rc.credits,
                "equivalent_codes": ", ".join(rc.equivalent_codes),
                "note": rc.note,
            }
            for rc in required_courses
        ]
    )


def _reset_widgets_and_rerun() -> None:
    for key in WIDGET_KEYS:
        st.session_state.pop(key, None)
    st.rerun()


st.title("📄 성적표 · 이수학점 · 졸업조건 업로드")
st.write("파일(PDF/이미지/워드/엑셀 등)을 업로드해 Upstage로 자동 파싱하거나, 아래 표를 직접 입력/수정하세요.")

with st.expander("⚙️ 설정 및 데이터"):
    col1, col2 = st.columns(2)
    with col1:
        if has_upstage_key():
            st.success("Upstage API 키가 설정되어 있습니다. 문서 자동 파싱을 사용할 수 있습니다.")
        else:
            st.warning(
                "UPSTAGE_API_KEY가 설정되지 않았습니다. `.env.example`을 `.env`로 복사하고 키를 입력하세요. "
                "키가 없어도 수동 입력과 샘플 데이터로 앱을 체험할 수 있습니다."
            )
    with col2:
        st.metric("등록된 강의계획서 수", len(list_syllabi()))
        st.metric("학생 프로필", "등록됨" if load_profile() else "미등록")

    if st.button("샘플 강의계획서 16개 불러오기 (데모용)"):
        n = seed_sample_syllabi()
        st.success(f"{n}개의 샘플 강의계획서를 추가했습니다." if n else "이미 모든 샘플 강의계획서가 등록되어 있습니다.")

    st.markdown(
        """
**사용 순서**
1. **성적표 업로드** — 성적표 / 이수학점표 / 졸업조건 / 학사편람 파일을 업로드하거나 직접 입력합니다.
2. **강의계획서 비교** — 강의계획서를 등록하고 비교표에서 태그(팀플, 시험방식, 출석강도)로 필터링합니다.
3. **추천 시간표** — 필터를 설정하고 하드필터 + 조건 필터로 걸러낸 뒤 정렬된 추천 시간표를 확인합니다.
   마음에 드는 시간표는 '내 시간표'에 표시로 고정할 수 있습니다.
4. **내 시간표** — 추천 시간표에서 고른 시간표를 확인합니다.
5. **통합 캘린더** — 공지·공모전·행사·시험일정을 모아서 보고 구글 캘린더로 내보냅니다.
"""
    )

if "transcript_df" not in st.session_state:
    existing = load_profile()
    if existing:
        st.session_state.transcript_df = _transcript_records_to_df(existing.transcript)
        st.session_state.requirement_df = _requirements_to_df(existing.requirements)
        st.session_state.required_course_df = _required_courses_to_df(existing.required_courses)
        st.session_state.name = existing.name
        st.session_state.department = existing.department
        st.session_state.year = existing.year
        st.session_state.double_major = ", ".join(existing.double_major_departments)
    else:
        st.session_state.transcript_df = pd.DataFrame(
            columns=["course_code", "course_name", "credits", "grade", "semester", "category"]
        )
        st.session_state.requirement_df = pd.DataFrame(columns=["category", "required_credits"])
        st.session_state.required_course_df = pd.DataFrame(
            columns=["course_code", "course_name", "category", "credits", "equivalent_codes", "note"]
        )
        st.session_state.name = ""
        st.session_state.department = ""
        st.session_state.year = 1
        st.session_state.double_major = ""

st.subheader("0. 샘플 데이터로 체험하기")
if st.button("🧪 샘플 성적표 불러오기 (데모용)"):
    sample = load_sample_profile()
    if sample is None:
        st.error("샘플 데이터 파일(data/sample_profile.json)을 찾을 수 없습니다.")
    else:
        st.session_state.transcript_df = _transcript_records_to_df(sample.transcript)
        st.session_state.requirement_df = _requirements_to_df(sample.requirements)
        st.session_state.required_course_df = _required_courses_to_df(sample.required_courses)
        st.session_state.name = sample.name
        st.session_state.department = sample.department
        st.session_state.year = sample.year
        st.session_state.double_major = ", ".join(sample.double_major_departments)
        _reset_widgets_and_rerun()
st.caption(
    "컴퓨터공학과 3학년 예시 성적표(전공/교양 7과목 기이수), 졸업 이수학점 요건, 학사편람 필수과목 목록을 "
    "불러옵니다. 불러온 뒤 아래 표에서 확인/수정하고 '프로필 저장'을 누르세요."
)

st.subheader("1. 파일 업로드 (선택)")
if not has_upstage_key():
    st.info("UPSTAGE_API_KEY가 없어도 위 샘플 데이터나 아래 표 직접 입력으로 체험할 수 있습니다.")
st.caption("성적표 / 이수학점표 / 학사편람 파일을 한꺼번에 올리세요. 파일마다 종류를 자동으로 판별해 알맞은 표에 채워 넣습니다.")

mixed_files = st.file_uploader(
    "성적표 · 이수학점표 · 학사편람 파일",
    type=["pdf", "png", "jpg", "jpeg", "docx", "xlsx", "pptx"],
    accept_multiple_files=True,
)
if st.button("파싱하기", disabled=not (has_upstage_key() and mixed_files)):
    new_records: list[TranscriptRecord] = []
    new_reqs: list[CreditRequirement] = []
    new_required: list[RequiredCourse] = []
    detected: list[tuple[str, str]] = []
    with st.spinner("Upstage로 문서 종류를 판별하고 파싱하는 중..."):
        for f in mixed_files:
            try:
                markdown = parse_document(f.read(), f.name)
                doc_type = classify_document(markdown)
                detected.append((f.name, doc_type))
                if doc_type == "성적표":
                    new_records.extend(extract_transcript(markdown))
                elif doc_type == "이수학점표":
                    new_reqs.extend(extract_credit_requirements(markdown))
                else:
                    new_required.extend(extract_required_courses(markdown))
            except UpstageError as e:
                st.error(f"{f.name}: {e}")
    if detected:
        st.caption("인식 결과: " + ", ".join(f"{name} → {t}" for name, t in detected))
    if new_records:
        merged = pd.concat(
            [st.session_state.transcript_df, _transcript_records_to_df(new_records)], ignore_index=True
        ).drop_duplicates(subset=["course_code"], keep="last")
        st.session_state.transcript_df = merged
        st.success(f"성적표: {len(new_records)}개 과목을 인식했습니다.")
    if new_reqs:
        merged = pd.concat(
            [st.session_state.requirement_df, _requirements_to_df(new_reqs)], ignore_index=True
        ).drop_duplicates(subset=["category"], keep="last")
        st.session_state.requirement_df = merged
        st.success(f"이수학점표: {len(new_reqs)}개 교과영역을 인식했습니다.")
    if new_required:
        merged = pd.concat(
            [st.session_state.required_course_df, _required_courses_to_df(new_required)], ignore_index=True
        ).drop_duplicates(subset=["course_code"], keep="last")
        st.session_state.required_course_df = merged
        st.success(f"학사편람: {len(new_required)}개 필수과목을 인식했습니다.")
    if new_records or new_reqs or new_required:
        _reset_widgets_and_rerun()

st.subheader("2. 학생 기본 정보")
c0, c1, c2, c3 = st.columns(4)
with c0:
    st.session_state.name = st.text_input("이름 (선택, 홈 화면 인사말에 사용)", value=st.session_state.name, key="name_input")
with c1:
    st.session_state.department = st.text_input("학과", value=st.session_state.department, key="department_input")
with c2:
    st.session_state.year = st.number_input(
        "학년", min_value=1, max_value=6, value=st.session_state.year, step=1, key="year_input"
    )
with c3:
    st.session_state.double_major = st.text_input(
        "복수/부전공 학과 (쉼표로 구분, 없으면 비워두기)", value=st.session_state.double_major, key="double_major_input"
    )

st.subheader("3. 성적표 (직접 수정 가능)")
st.session_state.transcript_df = st.data_editor(
    st.session_state.transcript_df,
    num_rows="dynamic",
    width="stretch",
    column_config={
        "credits": st.column_config.NumberColumn("학점", min_value=0.0, step=0.5),
        "category": st.column_config.SelectboxColumn("교과영역", options=CATEGORY_VALUES),
    },
    key="transcript_editor",
)

st.subheader("4. 졸업 이수학점 요건 (교과영역별 합계, 직접 수정 가능)")
st.session_state.requirement_df = st.data_editor(
    st.session_state.requirement_df,
    num_rows="dynamic",
    width="stretch",
    column_config={
        "category": st.column_config.SelectboxColumn("교과영역", options=CATEGORY_VALUES),
        "required_credits": st.column_config.NumberColumn("요구 학점", min_value=0.0, step=1.0),
    },
    key="requirement_editor",
)
total_required = st.session_state.requirement_df["required_credits"].sum() if len(st.session_state.requirement_df) else 0
st.caption(f"합계: {total_required}학점")

current_profile = load_profile()
if current_profile is not None:
    st.caption("현재 저장된 프로필 기준 이수 현황 (표를 수정하고 다시 저장하면 갱신됩니다)")
    earned = current_profile.earned_credits_by_category()
    remaining = current_profile.remaining_credits_by_category()
    summary_df = pd.DataFrame(
        [
            {"교과영역": cat.value, "이수학점": earned.get(cat, 0.0), "부족학점": remaining.get(cat, 0.0)}
            for cat in CreditCategory
        ]
    )
    st.dataframe(summary_df, width="stretch")

st.subheader("5. 학사편람 필수과목 (과목 단위, 직접 수정 가능)")
st.caption(
    "졸업을 위해 반드시 들어야 하는 특정 과목 목록입니다. equivalent_codes(대체과목)는 학사편람에 "
    "'OOO로 대체 가능'처럼 명시된 경우에만 쉼표로 입력하세요 — 이수내역에 그 과목 코드가 있으면 "
    "충족으로 인정됩니다."
)
st.session_state.required_course_df = st.data_editor(
    st.session_state.required_course_df,
    num_rows="dynamic",
    width="stretch",
    column_config={
        "category": st.column_config.SelectboxColumn("교과영역", options=CATEGORY_VALUES),
        "credits": st.column_config.NumberColumn("학점", min_value=0.0, step=0.5),
        "equivalent_codes": st.column_config.TextColumn("대체과목 코드 (쉼표 구분)"),
        "note": st.column_config.TextColumn("비고"),
    },
    key="required_course_editor",
)

if current_profile is not None and current_profile.required_courses:
    st.caption("현재 저장된 프로필 기준 필수과목 이수 현황 (표를 수정하고 다시 저장하면 갱신됩니다)")
    st.caption("교과영역 채운/총/부족 학점은 학사편람 필수과목 기준입니다 (교양/전공 전체 이수학점 요건과는 별개).")

    progress = current_profile.required_course_progress()
    registered_codes = {s.course_code for _, s in list_syllabi()}
    rows = []
    for rc in current_profile.required_courses:
        satisfied_code = current_profile.satisfied_by_code(rc)
        if satisfied_code is None:
            status = "❌ 미이수"
        elif satisfied_code == rc.course_code:
            status = "✅ 이수"
        else:
            status = f"✅ 대체과목({satisfied_code})으로 이수"
        cat_progress = progress.get(rc.category, {"filled": 0.0, "total": 0.0, "missing": 0.0})
        rows.append(
            {
                "상태": status,
                "과목코드": rc.course_code,
                "과목명": rc.course_name,
                "교과영역": rc.category.value,
                "학점": rc.credits,
                "대체과목": ", ".join(rc.equivalent_codes) or "-",
                "비고": rc.note or "-",
                "현재 강의계획서 등록됨": "예" if rc.course_code in registered_codes else "-",
                "교과영역 채운학점": cat_progress["filled"],
                "교과영역 총학점": cat_progress["total"],
                "교과영역 부족학점": cat_progress["missing"],
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch")
    missing = current_profile.missing_required_courses()
    if missing:
        st.warning(f"미이수 필수과목 {len(missing)}개: " + ", ".join(f"{rc.course_name}({rc.course_code})" for rc in missing))
    else:
        st.success("등록된 필수과목을 모두 이수했습니다.")

st.divider()
if st.button("💾 학생 프로필 저장", type="primary"):
    if not st.session_state.department:
        st.error("학과를 입력하세요.")
    else:
        transcript = [
            TranscriptRecord(
                course_code=str(row.course_code),
                course_name=str(row.course_name),
                credits=float(row.credits),
                grade=str(row.grade),
                semester=str(row.semester),
                category=CreditCategory.from_str(row.category),
            )
            for row in st.session_state.transcript_df.itertuples()
            if pd.notna(row.course_code)
        ]
        requirements = [
            CreditRequirement(category=CreditCategory.from_str(row.category), required_credits=float(row.required_credits))
            for row in st.session_state.requirement_df.itertuples()
            if pd.notna(row.category)
        ]
        required_courses = [
            RequiredCourse(
                course_code=str(row.course_code),
                course_name=str(row.course_name),
                category=CreditCategory.from_str(row.category),
                credits=float(row.credits),
                equivalent_codes=[c.strip() for c in str(row.equivalent_codes or "").split(",") if c.strip()],
                note=str(row.note) if pd.notna(row.note) else "",
            )
            for row in st.session_state.required_course_df.itertuples()
            if pd.notna(row.course_code)
        ]
        double_major = [d.strip() for d in st.session_state.double_major.split(",") if d.strip()]
        profile = StudentProfile(
            department=st.session_state.department,
            year=int(st.session_state.year),
            name=st.session_state.name,
            transcript=transcript,
            requirements=requirements,
            required_courses=required_courses,
            double_major_departments=double_major,
        )
        save_profile(profile)
        st.success("프로필을 저장했습니다. '추천 시간표' 페이지로 이동하세요.")
