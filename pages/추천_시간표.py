import pandas as pd
import streamlit as st

from core.models import CreditCategory
from core.recommender import DEFAULT_FILTERS, recommend_timetables
from core.storage import init_db, list_syllabi, load_profile, save_selected_timetable
from core.theme import inject_theme
from core.timetable_view import render_timetable_html

st.set_page_config(page_title="추천 시간표", page_icon="🎯", layout="wide")
init_db()
inject_theme()

DAY_VALUES = ["월", "화", "수", "목", "금", "토", "일"]
ATTENDANCE_VALUES = ["낮음", "보통", "높음"]

st.title("🎯 추천 시간표")

profile = load_profile()
if profile is None:
    st.warning("먼저 '성적표 업로드' 페이지에서 학생 프로필을 저장하세요.")
    st.stop()

candidates = [s for _, s in list_syllabi()]
if not candidates:
    st.warning("등록된 강의계획서가 없습니다. '강의계획서 비교' 페이지에서 등록하거나 샘플 데이터를 불러오세요.")
    st.stop()

st.subheader("현재 이수 현황")
earned = profile.earned_credits_by_category()
remaining = profile.remaining_credits_by_category()
summary_df = pd.DataFrame(
    [
        {
            "교과영역": cat.value,
            "이수학점": earned.get(cat, 0.0),
            "요구학점": next((r.required_credits for r in profile.requirements if r.category == cat), 0.0),
            "부족학점": remaining.get(cat, 0.0),
        }
        for cat in CreditCategory
    ]
)
st.dataframe(summary_df, width="stretch")
st.caption(f"학과: {profile.department} · 학년: {profile.year} · 등록된 강의계획서 후보: {len(candidates)}개")

st.divider()
st.subheader("필터 설정")
st.caption("조건에 맞지 않는 과목은 후보에서 아예 제외됩니다. 아무것도 선택하지 않으면 전체 허용입니다.")

c1, c2 = st.columns(2)
with c1:
    max_credits = st.number_input("이번 학기 최대 신청 학점", min_value=9, max_value=24, value=18, step=1)
    top_n = st.number_input("추천 시간표 개수", min_value=1, max_value=10, value=5, step=1)
    exclude_team_project = st.checkbox("팀 프로젝트 과목 제외")
    only_remaining_requirements = st.checkbox("부족한 졸업요건 교과영역 과목만 보기")

with c2:
    allowed_attendance = st.multiselect("출석 비중", ATTENDANCE_VALUES)
    available_exam_types = sorted({et for c in candidates for et in c.exam_types})
    allowed_exam_types = st.multiselect("시험/평가 방식", available_exam_types)

filters = {
    "exclude_team_project": exclude_team_project,
    "allowed_attendance": allowed_attendance,
    "allowed_exam_types": allowed_exam_types,
    "only_remaining_requirements": only_remaining_requirements,
}

st.divider()
if st.button("🔍 추천 시간표 계산", type="primary"):
    with st.spinner("하드 필터 + 조건 필터 적용 → 시간 충돌 없는 조합 탐색 → 부족 학점 채움 순 정렬 중..."):
        timetables = recommend_timetables(profile, candidates, filters, max_credits, top_n)
    st.session_state.timetables = timetables

timetables = st.session_state.get("timetables")
if timetables is not None:
    if not timetables:
        st.error("조건을 만족하는 시간표를 찾지 못했습니다. 필터 조건이나 최대 학점을 조정해보세요.")
    else:
        st.success(f"{len(timetables)}개의 추천 시간표를 찾았습니다. (부족한 졸업요건을 많이 채우는 조합 순)")
        for i, tt in enumerate(timetables, start=1):
            with st.expander(f"#{i} 시간표 — 총 {tt.total_credits}학점", expanded=(i == 1)):
                course_df = pd.DataFrame(
                    [
                        {
                            "과목코드": c.course_code,
                            "과목명": c.course_name,
                            "교과영역": c.category.value,
                            "학점": c.credits,
                            "교수": c.professor,
                            "시간": ", ".join(f"{t.day}{t.start}-{t.end}" for t in c.time_slots),
                            "팀플": "예" if c.team_project else "아니오",
                            "시험방식": ", ".join(c.exam_types),
                            "출석강도": c.attendance_intensity,
                        }
                        for c in tt.courses
                    ]
                )
                st.dataframe(course_df, width="stretch")

                st.markdown(render_timetable_html(tt.courses), unsafe_allow_html=True)

                if st.button("⭐ 이 시간표를 홈 화면에 표시", key=f"select_timetable_{i}"):
                    save_selected_timetable(tt.courses)
                    st.success("홈 화면에 표시할 시간표로 선택했습니다. 홈으로 이동해서 확인하세요.")

                if tt.requirement_breakdown:
                    breakdown_df = pd.DataFrame(
                        [{"교과영역": k, "채우는 학점": v} for k, v in tt.requirement_breakdown.items()]
                    )
                    st.dataframe(breakdown_df, width="stretch", hide_index=True)
